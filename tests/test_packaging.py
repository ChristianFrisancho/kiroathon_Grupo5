"""Empaquetado (scripts/build_lambda.py) e infraestructura (template.yaml)."""
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import support  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "template.yaml").read_text(encoding="utf-8")


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_lambda", ROOT / "scripts" / "build_lambda.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateTests(unittest.TestCase):
    def test_dos_funciones_con_handler_y_codeuri(self):
        functions = load_build_module().parse_functions(TEMPLATE.splitlines())
        self.assertEqual({f[0]: f[1] for f in functions},
                         {"AppFunction": "app.handler", "JobWorkerFunction": "worker.handler"})

    def test_permisos_especificos(self):
        self.assertNotIn("foundation-model/*", TEMPLATE)
        self.assertNotIn("inference-profile/*", TEMPLATE)
        self.assertIn("inference-profile/${ModelId}", TEMPLATE)
        self.assertIn("foundation-model/${FoundationModelId}", TEMPLATE)
        self.assertRegex(TEMPLATE, r"lambda:InvokeFunction\s*\n\s*Resource: !GetAtt JobWorkerFunction.Arn")
        worker = TEMPLATE[TEMPLATE.index("JobWorkerFunction:"):TEMPLATE.index("AppFunction:")]
        self.assertNotIn("bedrock", worker.lower())  # el worker no usa Bedrock
        self.assertIn("JOB_WORKER_FUNCTION: !Ref JobWorkerFunction", TEMPLATE)
        self.assertIn("Timeout: 29", TEMPLATE)
        self.assertIn("AttributeName: ttl", TEMPLATE)

    def test_el_template_no_tiene_dependencia_circular(self):
        worker = TEMPLATE[TEMPLATE.index("JobWorkerFunction:"):TEMPLATE.index("AppFunction:")]
        self.assertNotIn("AppFunction", worker)


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_lambda.py")], capture_output=True,
                                text=True, encoding="utf-8", timeout=120)
        cls.output = result.stdout + result.stderr
        cls.returncode = result.returncode
        cls.build = ROOT / ".aws-sam" / "build"

    def test_el_build_termina_y_genera_ambas_funciones(self):
        self.assertEqual(self.returncode, 0, self.output)
        template = (self.build / "template.yaml").read_text(encoding="utf-8")
        self.assertIn("CodeUri: AppFunction", template)
        self.assertIn("CodeUri: JobWorkerFunction", template)
        self.assertNotIn("BuildMethod", template)
        self.assertTrue((self.build / "AppFunction" / "front" / "index.html").is_file())
        self.assertFalse((self.build / "JobWorkerFunction" / "front").exists())
        for path in self.build.rglob("*"):
            self.assertNotIn(path.suffix, (".db", ".pyc"))
            self.assertNotIn("__pycache__", path.parts)

    def test_los_artefactos_se_importan_y_responden(self):
        code = (
            "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, %r);"
            "import app, worker;"
            "r = app.handler({'rawPath': '/', 'requestContext': {'http': {'method': 'GET'}}}, None);"
            "print(json.dumps([r['statusCode'], r['headers']['Content-Type'], worker.handler({}, None)['status']]))"
        ) % (str(self.build / "AppFunction"), str(self.build / "JobWorkerFunction"))
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                                timeout=60, cwd=str(ROOT / "tests"))
        self.assertEqual(result.returncode, 0, result.stderr)
        status, ctype, worker_status = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(status, 200)
        self.assertTrue(ctype.startswith("text/html"))
        self.assertEqual(worker_status, "ignored")

    def test_un_template_roto_no_destruye_el_ultimo_build(self):
        module = load_build_module()
        with self.assertRaises(SystemExit):
            module.parse_functions(["Resources:", "  Roto:", "    Type: AWS::Serverless::Function", "    Properties:",
                                    "      Runtime: python3.12"])
        self.assertTrue((self.build / "template.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
