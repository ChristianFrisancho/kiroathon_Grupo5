# Verificación de AulaLista (equipo T005)

- **URL base**, confirmada con el Output `ApiUrl` del stack de CloudFormation `aulalista-t005` (us-east-1): `https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com`
- **Equipo:** T005.
- **Comprobación:** 30-oct-2026, 18:33–18:34 UTC, commit `c68e513`, desplegado en el stack `aulalista-t005` con ese commit (working tree limpio al ejecutar).
- **Resultados reales:** [`docs/evidencias/insignias.json`](evidencias/insignias.json) y [`docs/evidencias/genai-real.json`](evidencias/genai-real.json). Cada archivo trae su fecha, su commit y las respuestas recibidas.

**Tres niveles distintos:**
- **Prueba local:** suite aislada, con DynamoDB y Bedrock simulados.
- **Prueba desplegada:** scripts contra la URL pública.
- **Insignia otorgada:** solo la decide el portal con «Verificar ahora». Lo de abajo es un *contrato verificado por nosotros*, no una insignia desbloqueada.

## Comandos (Bash del Kiro web)

```bash
BASE="https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com"

python3 scripts/verify_badges.py \
  --base "$BASE" \
  --team T005 \
  --report docs/evidencias/insignias.json

python3 scripts/smoke_genai.py \
  --base "$BASE" \
  --runs 1 \
  --report docs/evidencias/genai-real.json
```

- `verify_badges.py` crea solo datos sintéticos de verificación: **un item y un job por ejecución**, con valores aleatorios y sin datos personales. Sondea `GET /jobs/{id}` cada 1,5 s durante 12 s como máximo.
- `smoke_genai.py` usa solo el caso simulado (cuarto de primaria, 45 min, pizarra, papel y lápiz). No guarda sesiones ni registros y no reintenta. Si recibe «Respaldo local» en lugar de Bedrock, falla.

### Comprobaciones manuales equivalentes

```bash
BASE="https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com"
curl --silent --show-error --fail-with-body --max-time 15 --include "$BASE/health"
```

Respuesta esperada (ejemplo, no resultado real):

```http
HTTP 200
Content-Type: application/json
{"status":"ok","team":"T005"}
```

Persistencia:

```bash
NONCE="verificacion-$(date +%s)-$RANDOM"
CREATED="$(curl --silent --show-error --fail-with-body --max-time 15 \
  --header 'Content-Type: application/json' --data "{\"value\":\"$NONCE\"}" "$BASE/items")"
printf '%s\n' "$CREATED"
ITEM_ID="$(printf '%s' "$CREATED" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
curl --silent --show-error --fail-with-body --max-time 15 "$BASE/items/$ITEM_ID"
curl --silent --show-error --fail-with-body --max-time 15 "$BASE/items"
```

Respuestas esperadas: el POST devuelve 200/201 con un `id` no vacío; el GET individual trae un `value` exactamente igual a `NONCE`; el GET del listado incluye el elemento recién creado (los 100 más recientes, del más nuevo al más antiguo).

Jobs:

```bash
JOB_CREATED="$(curl --silent --show-error --fail-with-body --max-time 12 \
  --header 'Content-Type: application/json' --data "{\"input\":\"$NONCE\"}" "$BASE/jobs")"
printf '%s\n' "$JOB_CREATED"
JOB_ID="$(printf '%s' "$JOB_CREATED" | python3 -c 'import json,sys; print(json.load(sys.stdin)["jobId"])')"
curl --silent --show-error --fail-with-body --max-time 12 "$BASE/jobs/$JOB_ID"
```

Respuesta esperada: el POST devuelve 202 con `jobId`. Una consulta inmediata puede devolver `"status": "queued"`: eso no es un fallo ni una insignia conseguida. El sondeo completo, con el plazo de 12 s, lo hace `verify_badges.py`. Al terminar se espera `{"jobId": "...", "status": "done", "output": "<NONCE al revés>"}`.

## Resultados

| Comprobación | Entorno | Comando | Resultado real | Evidencia |
|---|---|---|---|---|
| API viva | AWS desplegado | `verify_badges.py` | 200, `application/json`, `{"status":"ok","team":"T005"}` | `insignias.json` → checks[0] |
| Persistencia | AWS desplegado | `verify_badges.py` | POST 201 con id; GET por id con el mismo nonce; listado lo incluye | `insignias.json` → checks[1] |
| Jobs ≤ 12 s | AWS desplegado | `verify_badges.py` | POST 202; `done` con salida invertida en el primer sondeo, a 1,72 s | `insignias.json` → checks[2]; logs del worker (abajo) |
| Bedrock real | AWS desplegado | `smoke_genai.py --runs 3` | 3/3 con `engine=bedrock`, `isBedrock=true`, 45 min, referencias M1–M3 y fuentes iguales al módulo. HTTP: 2,43 / 2,78 / 3,76 s (media 2,99 s) | `genai-real.json`; logs de Converse (abajo) |
| JSON malformado y sobres inválidos | Aislado (FakeBedrock) | `python3 -m unittest discover -s tests` | 502 `generation_failed`, sin sesiones creadas ni atribución a Bedrock | `tests/test_integrity.py::AiOutputTests`, `tests/test_app.py::BedrockFlowTests` |
| Flujo docente | Navegador local (Chromium/Playwright) | `python3 -m unittest discover -s tests` | 16 pruebas OK; recorrido de 10 acciones | `tests/test_browser.py`, `docs/capturas/` |
| Frontend desplegado (solo lectura) | AWS desplegado, Chromium | script de lectura | GET / 200 `text/html` sin redirección; CSS/JS 200 con MIME correcto; consola sin errores; sin peticiones externas; sin scroll horizontal a 320 y 1440 px | `docs/capturas/desplegado-hoy-320.png`, `desplegado-hoy-1440.png` |

Los tiempos de Bedrock son de la generación de una clase. No tienen relación con los 12 s de la insignia Jobs. Tres muestras no permiten hablar de percentiles ni de una garantía de rendimiento.

## Corroboración en CloudWatch (consulta del 30-oct, 18:3x UTC)

En `AppFunction` aparecen 4 eventos `bedrock_converse_completed` (modelo `us.amazon.nova-lite-v1:0`, `stopReason=end_turn`, intento 1). Su `elapsedMs`, medido por el SDK en la llamada a Converse, fue de 2230, 2725, 3712 y 2380 ms, cada uno con su `bedrockRequestId`. Las tres últimas coinciden en hora con las tres muestras de `smoke_genai.py`; la primera, de las 18:33:42, es anterior a la ejecución de `verify_badges`. El tiempo del SDK y el tiempo HTTP del script son mediciones distintas.

En `JobWorkerFunction` aparecen invocaciones `REPORT` (una de 2719 ms con arranque en frío y otra de 77 ms). Confirman que el trabajo lo procesó el worker, no un GET.

Los logs no registran prompt, notas, respuesta pedagógica ni credenciales.

## Qué falta en el portal

- Pegar la URL base (sin barra final) en **Perfil del equipo** y pulsar **«Verificar ahora»** en API viva, Persistencia y Asíncrono.
- Maestría Kiro y GenAI con propósito se otorgan al evaluar el código o el frontend.
