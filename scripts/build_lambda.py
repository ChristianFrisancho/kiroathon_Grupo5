"""Empaqueta la Lambda igual que `sam build` (objetivo build-AppFunction del Makefile), sin necesitar `make`.

Uso: python3 scripts/build_lambda.py   →   después: sam deploy ... (usa .aws-sam/build/template.yaml)
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".aws-sam" / "build"
ARTIFACTS = BUILD / "AppFunction"


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    ARTIFACTS.mkdir(parents=True)
    shutil.copy2(ROOT / "back" / "app.py", ARTIFACTS / "app.py")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "data")
    shutil.copytree(ROOT / "back" / "aulalista", ARTIFACTS / "aulalista", ignore=ignore)
    shutil.copytree(ROOT / "front", ARTIFACTS / "front", ignore=ignore)
    template = (ROOT / "template.yaml").read_text(encoding="utf-8")
    template = template.replace("    Metadata:\n      BuildMethod: makefile\n", "")
    template, count = re.subn(r"CodeUri: \.\n", "CodeUri: AppFunction\n", template)
    if count != 1:
        raise SystemExit("No se encontró CodeUri en template.yaml")
    (BUILD / "template.yaml").write_text(template, encoding="utf-8")
    files = sum(1 for p in ARTIFACTS.rglob("*") if p.is_file())
    print("Lambda empaquetada en %s (%d archivos)" % (ARTIFACTS.relative_to(ROOT), files))


if __name__ == "__main__":
    main()
