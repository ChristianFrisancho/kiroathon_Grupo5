# AulaLista: convenciones del proyecto (equipo T005)

## Producto
Copiloto del docente de colegio público (track «Copiloto del docente público»). Historia única: módulo → contexto confirmado → borrador con Amazon Bedrock → revisión humana → guardado → portafolio → registro de aplicación ligado a una versión. Principio: la IA prepara; el docente decide.

## Stack y nombres
- `back/`: Python solo con biblioteca estándar; `boto3` únicamente dentro de funciones (lo trae el runtime de Lambda). Entradas Lambda: `back/app.py` → `handler` (API + front) y `back/worker.py` → `handler` (worker de /jobs). Lógica en `back/aulalista/`: `service.py` reglas, `api.py` rutas, `validators.py`, `scoring.py`, `bedrock.py`, `budget.py` plazo por petición, `jobs.py`, `repository.py` SQLite y `dynamo_repository.py` DynamoDB (cliente de bajo nivel, TransactWriteItems).
- `front/`: HTML, CSS y módulos ES sin compilar. Paleta Halloween: negro `#0b0a0d`, naranja `#ff7a1a`, hueso `#f7efe3`; contraste AA, teclado completo, una acción principal por vista. Todo texto dinámico entra como texto, nunca `innerHTML`.
- AWS (`template.yaml`): HTTP API + `AppFunction` (29 s) + `JobWorkerFunction` + DynamoDB `ItemsTable` (`pk`/`sk`/`doc`, TTL `ttl`) + Bedrock Converse (`MODEL_ID`). Permisos: InvokeModel solo sobre el perfil y el modelo base configurados; InvokeFunction solo sobre el worker.
- Contratos públicos que no se cambian: `GET /health`, `POST/GET /items`, `POST /jobs` + `GET /jobs/{jobId}`.

## Reglas de datos
- Añadir una versión es atómico y condicionado a la versión de partida (`parentVersionId`); un conflicto responde 409 `version_conflict`. Nunca se calculan números leyendo todas las versiones.
- La procedencia la decide el servidor: los borradores se emiten con `draftId` y se guardan; al guardar se deriva `generatedBy`, `editedByTeacher` y `sourceDraftId`. Se ignora el `generatedBy` del navegador.
- Las escrituras del frontend envían `operationKey`; el mismo contenido con la misma clave devuelve el resultado ya confirmado.
- GET de /jobs solo lee; el trabajo lo hace el worker.

## Cómo probar y desplegar
- Pruebas (una sola orden): `python3 -m unittest discover -s tests`. DynamoDB y Bedrock se simulan (`tests/fakes.py`). Las de navegador (`tests/test_browser.py`) se omiten si no hay Playwright + Chromium.
- Local: `python3 back/run.py` (SQLite + plantilla local).
- Despliegue: `python3 scripts/build_lambda.py` (valida y reemplaza `.aws-sam/build` al final) y `sam deploy --template-file .aws-sam/build/template.yaml --stack-name aulalista-t005 --region us-east-1 --s3-bucket <bucket propio> --capabilities CAPABILITY_IAM --parameter-overrides TeamId=T005`. Después verificar con `curl` cada contrato.

## Qué no hacer
- No presentar la plantilla local ni el respaldo como salida de Bedrock.
- No inventar resultados de aprendizaje, valoraciones, ahorros de horas ni integraciones con APRENDE PERÚ. Datos simulados rotulados; nunca datos personales reales.
- Valoraciones: ausentes nunca valen 0, editar reemplaza, la autoevaluación del autor no cuenta y una versión nueva no hereda la media.
- No publicar ni marcar como revisado nada sin acción expresa del docente. No reintentar escrituras automáticamente. No conectar sistemas externos ni poner secretos en el repositorio.
- No declarar desplegado algo que solo pasó en local.
