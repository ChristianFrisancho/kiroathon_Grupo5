#!/usr/bin/env python3
"""Prueba de humo explícita de la integración GenAI desplegada (Bedrock real a través de la API).

Usa solo el caso simulado, no guarda sesiones ni registros y no reintenta una generación fallida.
Exige generatedBy.engine=bedrock e isBedrock=true: un respaldo local cuenta como fallo.
No se ejecuta con la suite (el nombre no empieza por test_). Uso:
    python3 scripts/smoke_genai.py --base https://... --runs 1 --report docs/evidencias/genai-real.json
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())
ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def git_state():
    def run(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8",
                                           stderr=subprocess.DEVNULL, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            return None
    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "workingTreeDirty": bool(status) if status is not None else None}


def request_json(base, method, path, body=None, timeout=35):
    headers = {"Accept": "application/json"}
    raw = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(base + path, data=raw, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with OPENER.open(req, timeout=timeout) as response:
            status = response.status
            response_headers = dict(response.headers.items())
            content_type = response.headers.get("Content-Type", "")
            payload = response.read()
    except HTTPError as exc:
        detail = exc.read(1500).decode("utf-8", errors="replace")
        raise RuntimeError("%s %s devolvió HTTP %s: %s" % (method, path, exc.code, detail)) from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    check("application/json" in content_type.lower(), "La API no devolvió application/json.")
    return status, json.loads(payload.decode("utf-8")), elapsed_ms, response_headers


def verify_draft(draft, module, submitted):
    check(isinstance(draft, dict), "Borrador no es un objeto.")
    origin = draft.get("generatedBy")
    check(isinstance(origin, dict), "Falta generatedBy.")
    check(origin.get("engine") == "bedrock" and origin.get("isBedrock") is True,
          "No hubo salida Bedrock: origen recibido=%s" % origin)
    check(draft.get("reviewStatus") == "borrador", "La respuesta no debe estar revisada automáticamente.")
    returned_module = draft.get("module")
    check(isinstance(returned_module, dict) and returned_module.get("id") == module["id"], "El módulo no coincide.")
    context = draft.get("context")
    check(isinstance(context, dict), "Falta el contexto.")
    check(context.get("grade") == submitted["grade"], "El grado confirmado no coincide.")
    check(context.get("durationMinutes") == submitted["durationMinutes"], "La duración confirmada no coincide.")
    check(context.get("materials") == submitted["materials"], "Los materiales confirmados no coinciden.")
    content = draft.get("content")
    check(isinstance(content, dict), "Falta content.")
    for field in ("title", "purpose", "expectedEvidence"):
        check(isinstance(content.get(field), str) and bool(content[field].strip()), "Campo inválido: %s" % field)
    check(content.get("durationMinutes") == submitted["durationMinutes"], "La duración del contenido no coincide.")
    activities = content.get("activities")
    check(isinstance(activities, list) and 1 <= len(activities) <= 12, "Lista de actividades inválida.")
    known = {fragment["id"]: fragment["text"] for fragment in module["fragments"]}
    total, cited = 0, set()
    for index, activity in enumerate(activities, start=1):
        check(isinstance(activity, dict), "Actividad %d inválida." % index)
        for field in ("title", "description"):
            check(isinstance(activity.get(field), str) and bool(activity[field].strip()),
                  "Actividad %d: %s inválido." % (index, field))
        minutes = activity.get("minutes")
        check(isinstance(minutes, int) and not isinstance(minutes, bool) and minutes > 0,
              "Actividad %d: minutos inválidos." % index)
        total += minutes
        refs = activity.get("references")
        check(isinstance(refs, list), "Actividad %d: references inválido." % index)
        for ref in refs:
            check(isinstance(ref, str) and ref in known, "Referencia inexistente en actividad %d." % index)
            cited.add(ref)
    check(total == submitted["durationMinutes"], "Los minutos de las actividades no suman la duración.")
    check(bool(cited), "La sesión no cita el módulo.")
    declared = {m.strip().casefold() for m in submitted["materials"]}
    materials = content.get("materials")
    check(isinstance(materials, list), "Materiales inválidos.")
    for material in materials:
        check(isinstance(material, str) and material.strip().casefold() in declared,
              "La lista contiene un material no declarado.")
    sources = content.get("sources")
    check(isinstance(sources, list), "Faltan las fuentes resueltas.")
    source_ids = set()
    for source in sources:
        check(isinstance(source, dict), "Fuente inválida.")
        source_id = source.get("id")
        check(isinstance(source_id, str) and source_id in known, "Fuente inexistente.")
        check(source.get("text") == known[source_id], "El texto de una fuente no coincide con el módulo.")
        source_ids.add(source_id)
    check(cited <= source_ids, "No todas las referencias tienen fuente inspeccionable.")
    return {
        "origin": origin, "title": content["title"], "activityCount": len(activities), "totalMinutes": total,
        "references": sorted(cited), "materials": materials, "reviewNotes": draft.get("reviewNotes"),
        "humanReviewStillRequired": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--runs", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--report", default="docs/evidencias/genai-real.json")
    args = parser.parse_args()
    base = args.base.strip().rstrip("/")
    parsed = urlsplit(base)
    check(parsed.scheme == "https" and bool(parsed.netloc) and parsed.path in ("", "/") and not parsed.query
          and not parsed.fragment and parsed.username is None and parsed.password is None,
          "Usa únicamente la URL base HTTPS.")
    report = {
        "timestampUtc": datetime.now(timezone.utc).isoformat(), **git_state(), "baseUrl": base,
        "test": "deployed-bedrock-smoke", "results": [],
        "limitations": [
            "No evalúa calidad pedagógica ni impacto educativo.",
            "No acredita percentiles con una muestra pequeña.",
            "elapsedMs es el tiempo HTTP completo medido por el script; el tiempo de la llamada a Converse está en los logs (bedrock_converse_completed).",
            "La procedencia se contrasta con el código (bedrock.py) y con los logs de CloudWatch.",
        ],
    }
    try:
        module_id = "mod-escucha-activa"
        status, module, _, _ = request_json(base, "GET", "/api/modules/" + quote(module_id, safe=""))
        check(status == 200, "No se pudo recuperar el módulo.")
        check(isinstance(module, dict) and isinstance(module.get("fragments"), list) and bool(module["fragments"]),
              "El módulo no tiene fragmentos válidos.")
        for index in range(args.runs):
            submitted = {
                "moduleId": module_id, "grade": "Cuarto de primaria", "durationMinutes": 45,
                "materials": ["pizarra", "papel", "lápiz"],
                "notes": "Caso simulado de verificación. Explica las instrucciones en pasos breves.",
            }
            try:
                status, draft, elapsed_ms, headers = request_json(base, "POST", "/api/drafts/generate", submitted)
                check(status == 200, "Generación: se esperaba 200.")
                evidence = verify_draft(draft, module, submitted)
                request_ids = {k: v for k, v in headers.items()
                               if k.lower() in ("x-amzn-requestid", "x-amz-apigw-id", "x-request-id", "apigw-requestid")}
                report["results"].append({"run": index + 1, "passed": True, "httpStatus": status,
                                          "elapsedMsHttp": elapsed_ms, "requestIds": request_ids, "evidence": evidence})
            except Exception as exc:  # noqa: BLE001 - se informa y no se reintenta
                report["results"].append({"run": index + 1, "passed": False, "error": str(exc)})
                break
    except Exception as exc:  # noqa: BLE001
        report["setupError"] = str(exc)
    report["allPassed"] = (len(report["results"]) == args.runs and all(r["passed"] for r in report["results"])
                           and "setupError" not in report)
    successful = [r["elapsedMsHttp"] for r in report["results"] if r["passed"]]
    if successful:
        report["latencySummaryHttp"] = {"samples": len(successful), "minMs": min(successful),
                                        "maxMs": max(successful),
                                        "meanMs": round(sum(successful) / len(successful), 2)}
    target = Path(args.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    target.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if report["allPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
