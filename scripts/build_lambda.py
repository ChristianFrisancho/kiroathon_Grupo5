"""Empaqueta las Lambdas igual que `sam build` (objetivos del Makefile), sin necesitar `make`.

Uso:  python3 scripts/build_lambda.py   →   sam deploy --template-file .aws-sam/build/template.yaml ...

- Lee template.yaml por bloques de indentación (no por reemplazos exactos de texto) y encuentra cada recurso
  `AWS::Serverless::Function` con su Handler y su CodeUri.
- Construye en un directorio temporal, valida artefactos y template y solo entonces reemplaza el build final:
  si algo falla, el último build utilizable queda intacto.
- Excluye cachés, bases de datos (*.db), datos locales y archivos de entorno.
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / ".aws-sam" / "build"
EXCLUDE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "data", ".env", "*.env")
SECRET_PATTERNS = (re.compile(rb"AKIA[0-9A-Z]{16}"), re.compile(rb"aws_secret_access_key", re.I))

# Qué contiene cada función: handler → archivos de back/ y si incluye el frontend.
PACKAGES = {
    "app.handler": {"files": ["app.py"], "front": True},
    "worker.handler": {"files": ["worker.py"], "front": False},
}


def parse_functions(lines):
    """Devuelve [(logical_id, start, end, handler, codeuri_line_index, metadata_range)] de las funciones."""
    try:
        res_start = next(i for i, line in enumerate(lines) if line.rstrip() == "Resources:")
    except StopIteration:
        raise SystemExit("template.yaml no tiene sección Resources")
    blocks = []
    i = res_start + 1
    while i < len(lines):
        line = lines[i]
        if line and not line.startswith(" ") and line.strip():
            break  # siguiente sección de nivel superior
        match = re.match(r"^  ([A-Za-z0-9]+):\s*$", line)
        if match:
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].startswith("   ") or lines[j].lstrip().startswith("#")):
                if re.match(r"^  [A-Za-z0-9]+:\s*$", lines[j]):
                    break
                j += 1
            blocks.append((match.group(1), i, j))
            i = j
        else:
            i += 1
    functions = []
    for logical_id, start, end in blocks:
        body = lines[start:end]
        if not any(re.match(r"^    Type:\s*AWS::Serverless::Function\s*$", b) for b in body):
            continue
        handler = codeuri = None
        metadata = None
        for k in range(start, end):
            if re.match(r"^      Handler:\s*(\S+)", lines[k]):
                handler = re.match(r"^      Handler:\s*(\S+)", lines[k]).group(1)
            if re.match(r"^      CodeUri:\s*\S+", lines[k]):
                codeuri = k
            if re.match(r"^    Metadata:\s*$", lines[k]):
                m_end = k + 1
                while m_end < end and lines[m_end].startswith("      "):
                    m_end += 1
                metadata = (k, m_end)
        if handler is None or codeuri is None:
            raise SystemExit("La función %s no declara Handler y CodeUri" % logical_id)
        functions.append((logical_id, handler, codeuri, metadata))
    if not functions:
        raise SystemExit("template.yaml no declara funciones")
    return functions


def build_function(dest: Path, handler: str) -> None:
    spec = PACKAGES.get(handler)
    if spec is None:
        raise SystemExit("No sé empaquetar el handler %s" % handler)
    dest.mkdir(parents=True)
    for name in spec["files"]:
        shutil.copy2(ROOT / "back" / name, dest / name)
    shutil.copytree(ROOT / "back" / "aulalista", dest / "aulalista", ignore=EXCLUDE)
    if spec["front"]:
        shutil.copytree(ROOT / "front", dest / "front", ignore=EXCLUDE)


def validate_function(dest: Path, handler: str) -> int:
    module, func = handler.split(".", 1)
    entry = dest / ("%s.py" % module)
    if not entry.is_file():
        raise SystemExit("Falta %s en %s" % (entry.name, dest.name))
    if not re.search(r"^def %s\(" % re.escape(func), entry.read_text(encoding="utf-8"), re.M):
        raise SystemExit("%s no define %s()" % (entry.name, func))
    if not (dest / "aulalista" / "__init__.py").is_file():
        raise SystemExit("Falta el paquete aulalista/ en %s" % dest.name)
    if PACKAGES[handler]["front"] and not (dest / "front" / "index.html").is_file():
        raise SystemExit("Falta front/index.html en %s" % dest.name)
    files = [p for p in dest.rglob("*") if p.is_file()]
    for path in files:
        if path.suffix in (".db", ".pyc") or "__pycache__" in path.parts:
            raise SystemExit("Artefacto no permitido: %s" % path)
        data = path.read_bytes()
        if any(p.search(data) for p in SECRET_PATTERNS):
            raise SystemExit("Posible secreto en %s" % path)
    return len(files)


def main() -> None:
    lines = (ROOT / "template.yaml").read_text(encoding="utf-8").splitlines()
    functions = parse_functions(lines)
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="build-", dir=FINAL.parent))
    try:
        out = list(lines)
        removals = []
        summary = []
        for logical_id, handler, codeuri_idx, metadata in functions:
            build_function(staging / logical_id, handler)
            count = validate_function(staging / logical_id, handler)
            summary.append("%s (%s): %d archivos" % (logical_id, handler, count))
            out[codeuri_idx] = re.sub(r"CodeUri:\s*\S+", "CodeUri: %s" % logical_id, out[codeuri_idx])
            if metadata:
                removals.append(metadata)
        for start, end in sorted(removals, reverse=True):
            del out[start:end]
        template = "\n".join(out) + "\n"
        for logical_id, *_ in functions:
            if "CodeUri: %s" % logical_id not in template:
                raise SystemExit("El template generado no apunta a %s" % logical_id)
        if "BuildMethod: makefile" in template:
            raise SystemExit("El template generado conserva BuildMethod")
        (staging / "template.yaml").write_text(template, encoding="utf-8")
        # Reemplazo final: el build anterior se conserva hasta este punto.
        previous = FINAL.with_name("build.previous")
        if previous.exists():
            shutil.rmtree(previous)
        if FINAL.exists():
            os.replace(FINAL, previous)
        os.replace(staging, FINAL)
        if previous.exists():
            shutil.rmtree(previous)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print("Build listo en %s" % FINAL.relative_to(ROOT))
    for line in summary:
        print("  " + line)


if __name__ == "__main__":
    sys.exit(main())
