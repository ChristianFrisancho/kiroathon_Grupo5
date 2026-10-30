# Diseño: AulaLista

## Arquitectura mínima en AWS (template.yaml)

```
Navegador ──HTTPS──▶ API Gateway HTTP API (rutas / y /{proxy+}, sin autenticación, con límite de tasa)
                         │
                         ▼
               Lambda AppFunction (Python 3.12, arm64, 29 s)
               back/app.py → handler
                 ├─ /health, /items, /jobs, /api/...  → aulalista.api.handle_request
                 └─ resto (GET)                        → archivos de front/ (mismo dominio)
                         │                         │
                         ▼                         ▼
          DynamoDB ItemsTable (pk, sk, doc)   Amazon Bedrock Converse (MODEL_ID)
```

Variables de la Lambda: `TEAM_ID` (parámetro `TeamId`, por defecto T005), `TABLE_NAME`, `MODEL_ID` (perfil `us.amazon.nova-lite-v1:0`, probado en la cuenta). Permisos mínimos: `DynamoDBCrudPolicy` sobre la tabla y `bedrock:InvokeModel` sobre modelos y perfiles de inferencia. Output `ApiUrl` sin barra final.

## Estructura del repositorio

- `back/`: Python solo con biblioteca estándar; boto3 se importa dentro de funciones (lo trae el runtime).
- `front/`: HTML, CSS y módulos ES sin compilar.
- `tests/`: una sola orden; `tests/test_app.py` simula DynamoDB (FakeTable) y Bedrock (FakeBedrock).
- `scripts/build_lambda.py` / `Makefile`: empaquetan `back/app.py`, `back/aulalista/` y `front/`.

## Módulos del backend

| Archivo | Responsabilidad |
|---|---|
| `app.py` | Adaptador Lambda (payload 2.0): API o archivos estáticos. Un servicio por contenedor. |
| `api.py` | Enrutador independiente del servidor; errores siempre en JSON sin trazas. |
| `service.py` | Reglas: borradores, versiones, revisión, copias, registros, compartir, valoraciones, adaptación, items y jobs. |
| `bedrock.py` | Converse con prompts de sistema diseñados (rol, reglas, límite de 400 caracteres por actividad, JSON), reintentos ante throttling, respaldo rotulado si no responde, 502 en otros errores. |
| `validators.py` | Validación determinista de contexto y sesión; las fuentes las resuelve el servidor. |
| `scoring.py` | Media de valoraciones completas (Fraction, ROUND_HALF_UP a un decimal). |
| `dynamo_repository.py` | Tabla única: `pk` = tipo (SESSION, VERSION, RECORD, EXPERIENCE, RATING, COMMENT, PREFERENCES, ITEM, JOB), `sk` = id, `doc` = JSON. Cada listado hace Query de una partición y pagina con LastEvaluatedKey. Valoración con clave `versión#revisor` (unicidad). |
| `repository.py` | Mismo contrato sobre SQLite para el servidor local. |

## Flujo GenAI central

1. El docente confirma el contexto en «Preparar»; el servidor lo valida (si es inválido, no llama al modelo).
2. `BedrockGenerator.generate` envía el contexto y los fragmentos M1–M3 dentro de `<modulo>` e `<indicaciones>` (datos, nunca instrucciones).
3. La respuesta JSON se normaliza de forma determinista (referencias conocidas, materiales declarados, minutos reescalados a la duración) y luego `validate_lesson_content` decide.
4. El borrador vuelve con `generatedBy`; el docente edita y decide guardar como borrador o como versión revisada.
5. «Adaptar en Mi aula» envía además la experiencia y su mejora propuesta; «Resumir acuerdos» envía solo los registros guardados.

## Trabajos asíncronos

`POST /jobs` guarda `queued` con `createdAt` en DynamoDB y responde 202. En Lambda (`job_mode=lazy`) la primera lectura posterior a 1 s calcula la salida (entrada invertida), persiste `done` y la devuelve: el verificador sondea cada 1,5 s, así que el resultado está listo en la primera consulta. En local, un ThreadPoolExecutor procesa el trabajo en segundo plano.

## Decisiones

1. Borrador no persistido hasta que el docente guarda.
2. Revisión explícita (`markReviewed: true` estricto); copiar o regenerar crea borradores.
3. Demo sin login: usuario `u-demo`; `X-User-Id` sirve solo para pruebas, no es autenticación.
4. Tabla única con Query por tipo: suficiente para la demo; con volumen real se añadirían índices por dueño y sesión.
5. Seguridad: CSP `default-src 'self'`, sin HTML dinámico, validación en el servidor y archivos confinados a `front/`.
