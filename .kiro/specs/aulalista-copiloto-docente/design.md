# Diseño: AulaLista

Estado: la fase 3 (integridad, procedencia, tiempos, worker y frontend) está implementada y probada en local. La URL pública sirve todavía la fase 2.

## Arquitectura mínima en AWS (template.yaml)

```
Navegador ──HTTPS──▶ API Gateway HTTP API (rutas / y /{proxy+}, sin autenticación, límite de tasa; corte a 30 s)
                         │
                         ▼
               Lambda AppFunction (Python 3.12, arm64, 29 s) ── back/app.py → handler
                 ├─ /health, /items, /jobs, /api/...  → aulalista.api.handle_request (plazo por petición)
                 └─ resto (GET)                        → archivos de front/ (mismo dominio)
                 │            │                    │
                 │            ▼                    ▼
                 │   DynamoDB ItemsTable      Amazon Bedrock Converse (MODEL_ID)
                 │   (pk, sk, doc, ttl)
                 └─ lambda:InvokeFunction (Event) ──▶ Lambda JobWorkerFunction (back/worker.py, 15 s)
                                                        └─ solo DynamoDB ItemsTable
```

Permisos: `DynamoDBCrudPolicy` sobre la tabla en ambas funciones. `bedrock:InvokeModel` solo sobre `inference-profile/${ModelId}` y `foundation-model/${FoundationModelId}` (en las regiones del perfil «us.»). `lambda:InvokeFunction` solo sobre el worker. El worker no tiene permisos de Bedrock.

## Estructura del repositorio

- `back/`: Python solo con biblioteca estándar; boto3 se importa dentro de funciones (lo trae el runtime).
- `front/`: HTML, CSS y módulos ES sin compilar.
- `tests/`: una sola orden. `tests/fakes.py` simula DynamoDB (condiciones y transacciones atómicas), Bedrock y un reloj.
- `scripts/build_lambda.py` / `Makefile`: empaquetan `AppFunction` (app.py, aulalista/, front/) y `JobWorkerFunction` (worker.py, aulalista/).

## Modelo de datos en DynamoDB

| Dato | pk | sk |
|---|---|---|
| Sesión con resumen (versión vigente, conteos) | SESSION#id | META |
| Versión / marcador de número único | SESSION#id | VERSION#versionId / VNUM#000002 |
| Registro de aplicación | SESSION#id | RECORD#createdAt#id |
| Sesiones de un docente (copia del resumen) | USER#owner | SESSION#id |
| Borrador emitido por el servidor | DRAFT#id | META (ttl) |
| Clave de operación | OP#owner | clave (ttl) |
| Experiencias / ya compartida / adaptaciones | EXPERIENCE · SHARED#autor · ADAPTED#experienceId | id · versionId · sessionId |
| Valoraciones / comentarios | RATINGS#exp / COMMENTS#exp | revisor / createdAt#id |
| Ítems / índice temporal / trabajos | ITEM / ITEMS_BY_TIME / JOB | id / createdAt#id / jobId |

- **Crear sesión:** una transacción con VERSION, VNUM, META y USER (todas con `attribute_not_exists`).
- **Añadir versión:** se lee META con lectura consistente y se verifica `currentVersionId == parentVersionId`. Después, una transacción crea VERSION y VNUM y reemplaza META con la condición `#doc = :expected` (el valor exacto leído) junto con la copia en USER. Si otra escritura cambió META, la condición falla y la API responde 409.
- **Fechas y conteos** (registro, revisión): lectura → cambio → escritura condicionada al valor leído, con reintentos. Nunca restaura una versión vigente antigua.
- **Migración:** `migrate_legacy()` copia el esquema anterior (pk = tipo) al actual sin borrar nada, una sola vez (marcador `MIGRATION/layout-v2`). Las versiones huérfanas antiguas no se presentan como sesiones.
- **SQLite:** las mismas garantías con transacciones, `UPDATE … WHERE current_version_id = ?` y `UNIQUE(session_id, number)`.

## Flujo GenAI central

1. El docente confirma el contexto en «Preparar»; el servidor lo valida y, si es inválido, no llama al modelo.
2. `BedrockGenerator.generate` envía el contexto y los fragmentos M1–M3 dentro de `<modulo>` e `<indicaciones>` (datos, nunca instrucciones).
3. **Normalización conservadora:**
   - Se quitan las referencias inventadas, con aviso.
   - Si ninguna actividad cita el módulo, la respuesta es error 502.
   - Se descartan las actividades sin contenido útil.
   - Se avisa de recursos mencionados que no se declararon.
   - Los minutos se reescalan con un mínimo de 1.
   - Después decide `validate_lesson_content`. Los avisos van en `reviewNotes`.
4. **Borrador emitido por el servidor:** se guarda con `draftId`, dueño, contenido, huella SHA-256, `generatedBy` y caducidad de 24 h.
5. **Al guardar** no se llama al modelo. El servidor deriva `generatedBy` del borrador y marca `editedByTeacher` si la huella cambió. Un borrador ajeno, caducado o inexistente se guarda como contenido del docente, con `provenanceNote`.
6. **Tiempos:** el SDK no reintenta. Cada intento necesita 15 s de margen (12 s de lectura + 3 s de conexión) dentro del plazo de la Lambda menos 2,5 s de reserva. Throttling con margen se reintenta; sin margen, o si el modelo no responde, se usa el respaldo local rotulado. Permisos y validación dan 502.

## Trabajos asíncronos

`POST /jobs` guarda `queued` y despacha el worker con `InvocationType=Event`, luego responde 202. El worker (`jobs.process_job`, idempotente) guarda `running` y `done` con la entrada invertida. `GET /jobs/{id}` solo lee. Si el despacho falla, el trabajo queda `failed` y la API responde 503. En local, un hilo del servidor (proceso de larga vida) hace de worker.

## Decisiones

1. El borrador del docente no se persiste como sesión hasta que guarda; el borrador del modelo sí queda en el servidor para verificar su procedencia.
2. Revisión explícita (`markReviewed: true` estricto); copiar o regenerar crea borradores.
3. Demo sin login: usuario `u-demo`; `X-User-Id` sirve solo para pruebas, no es autenticación.
4. Las escrituras del frontend llevan `operationKey`: la misma clave y el mismo contenido devuelven el resultado ya confirmado; la misma clave con otro contenido da 422.
5. Seguridad: CSP `default-src 'self'`, sin HTML dinámico, validación en el servidor y archivos confinados a `front/`.
