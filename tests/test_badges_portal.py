"""Contratos de las insignias tal como los llamaría el verificador del portal (Lambda con DynamoDB falsa)."""
import json
import unittest

import support  # noqa: F401

import app
from aulalista.bedrock import BedrockGenerator
from aulalista.dynamo_repository import DynamoRepository
from aulalista.service import Service
from fakes import FakeBedrock, FakeDynamoClient

ORIGIN = "https://dse8jbss45rea.cloudfront.net"


def event(method, path, body=None):
    return {"rawPath": path, "rawQueryString": "", "requestContext": {"http": {"method": method}},
            "headers": {"origin": ORIGIN, "content-type": "application/json", "user-agent": "verificador"},
            "body": json.dumps(body) if body is not None else None, "isBase64Encoded": False}


class PortalBadgeTests(unittest.TestCase):
    def setUp(self):
        app._service = Service(DynamoRepository(FakeDynamoClient(), "t"), BedrockGenerator(client=FakeBedrock("{}")),
                               app.lambda_settings(), dispatcher=lambda job_id: None)

    def tearDown(self):
        app._service = None

    def call(self, method, path, body=None):
        r = app.handler(event(method, path, body), None)
        data = json.loads(r["body"]) if r["body"] and r["headers"]["Content-Type"].startswith("application/json") else None
        return r["statusCode"], data, r["headers"]

    def test_api_viva(self):
        status, body, headers = self.call("GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok", "team": "T005"}))
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")

    def test_url_base_con_barra_final(self):
        self.assertEqual(self.call("GET", "//health")[0:2], (200, {"status": "ok", "team": "T005"}))
        self.assertEqual(self.call("GET", "/health/")[0], 200)
        self.assertEqual(self.call("GET", "//items")[0], 200)

    def test_preflight_cors(self):
        for path in ("/health", "/items", "/items/abc", "/jobs"):
            status, _, headers = self.call("OPTIONS", path)
            self.assertEqual(status, 204, path)
            self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
            self.assertIn("POST", headers["Access-Control-Allow-Methods"])
            self.assertIn("Content-Type", headers["Access-Control-Allow-Headers"])

    def test_persistencia(self):
        status, created, headers = self.call("POST", "/items", {"value": "nonce-portal-123"})
        self.assertIn(status, (200, 201))
        self.assertTrue(created["id"])
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(self.call("GET", "/items/" + created["id"])[1]["value"], "nonce-portal-123")
        listing = self.call("GET", "/items")[1]
        self.assertIn("nonce-portal-123", [i["value"] for i in listing])

    def test_nonce_no_texto_tambien_se_conserva(self):
        for value in (12345, {"n": 1}, "ñandú-ünicode"):
            created = self.call("POST", "/items", {"value": value})[1]
            self.assertEqual(self.call("GET", "/items/" + created["id"])[1]["value"], value)

    def test_asincrono_responde_202_con_jobid(self):
        status, job, headers = self.call("POST", "/jobs", {"input": "abc1"})
        self.assertEqual(status, 202)
        self.assertTrue(job["jobId"])
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")


if __name__ == "__main__":
    unittest.main()
