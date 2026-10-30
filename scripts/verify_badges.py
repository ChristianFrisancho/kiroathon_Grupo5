#!/usr/bin/env python3
"""Comprueba contra la URL desplegada los contratos de las insignias API viva, Persistencia y Asíncrono.

Crea solo datos sintéticos de verificación: un item y un job por ejecución (valores aleatorios, sin datos
personales). Sondea GET /jobs/{id} cada 1,5 s durante 12 s como máximo, como el verificador del portal.
Verificar el contrato aquí no equivale a que el portal desbloquee la insignia.
Uso:
    python3 scripts/verify_badges.py --base https://... --team T005 --report docs/evidencias/insignias.json
"""
import argparse
import json
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


def git_state():
    def run(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8",
                                           stderr=subprocess.DEVNULL, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            return None
    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "workingTreeDirty": bool(status) if status is not None else None}


def call(base, method, path, body=None, timeout=15):
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    try:
        with OPENER.open(Request(base + path, data=raw, headers=headers, method=method), timeout=timeout) as resp:
            status, ctype, payload = resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except HTTPError as exc:
        status, ctype, payload = exc.code, exc.headers.get("Content-Type", ""), exc.read()
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    try:
        data = json.loads(payload.decode("utf-8"))
    except ValueError:
        data = None
    return {"method": method, "path": path, "status": status, "contentType": ctype, "elapsedMs": elapsed, "body": data}


def check_health(base, team):
    r = call(base, "GET", "/health")
    ok = r["status"] == 200 and "application/json" in r["contentType"] and r["body"] == {"status": "ok", "team": team}
    return {"badge": "API viva", "passed": ok, "calls": [r]}


def check_items(base):
    nonce = "verificacion-%d-%s" % (int(time.time()), secrets.token_hex(4))
    created = call(base, "POST", "/items", {"value": nonce})
    calls = [created]
    item_id = (created["body"] or {}).get("id") if isinstance(created["body"], dict) else None
    ok = created["status"] in (200, 201) and isinstance(item_id, str) and bool(item_id)
    if ok:
        one = call(base, "GET", "/items/" + item_id)
        listing = call(base, "GET", "/items")
        calls += [one, listing]
        rows = listing["body"]["items"] if isinstance(listing["body"], dict) else listing["body"]
        ok = (one["status"] == 200 and isinstance(one["body"], dict) and one["body"].get("value") == nonce
              and listing["status"] == 200 and isinstance(rows, list)
              and any(isinstance(i, dict) and i.get("id") == item_id and i.get("value") == nonce for i in rows)
              and all("application/json" in c["contentType"] for c in calls))
    return {"badge": "Persistencia", "passed": ok, "nonce": nonce, "calls": calls}


def check_jobs(base):
    nonce = "abc-%s" % secrets.token_hex(4)
    started = time.monotonic()
    created = call(base, "POST", "/jobs", {"input": nonce}, timeout=12)
    calls = [created]
    job_id = created["body"].get("jobId") if isinstance(created["body"], dict) else None
    result = {"badge": "Asíncrono o agente", "passed": False, "nonce": nonce, "expectedOutput": nonce[::-1]}
    if created["status"] not in (200, 201, 202) or not job_id:
        return {**result, "calls": calls}
    while time.monotonic() - started < 12:
        time.sleep(1.5)
        polled = call(base, "GET", "/jobs/" + job_id, timeout=12)
        polled["secondsSincePost"] = round(time.monotonic() - started, 2)
        calls.append(polled)
        body = polled["body"] if isinstance(polled["body"], dict) else {}
        if body.get("status") == "done":
            result["passed"] = body.get("output") == nonce[::-1]
            result["doneAfterSeconds"] = polled["secondsSincePost"]
            break
    return {**result, "calls": calls}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--report", default="docs/evidencias/insignias.json")
    args = parser.parse_args()
    base = args.base.strip().rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise SystemExit("Usa únicamente la URL base HTTPS.")
    checks = [check_health(base, args.team), check_items(base), check_jobs(base)]
    report = {"timestampUtc": datetime.now(timezone.utc).isoformat(), **git_state(), "baseUrl": base,
              "team": args.team, "syntheticDataCreated": "1 item y 1 job", "checks": checks,
              "allPassed": all(c["passed"] for c in checks),
              "note": "Contrato verificado por nosotros; la insignia la otorga el portal con «Verificar ahora»."}
    target = Path(args.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print("%-20s %s" % (c["badge"], "OK" if c["passed"] else "FALLA"))
    print("Informe: %s" % target)
    return 0 if report["allPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
