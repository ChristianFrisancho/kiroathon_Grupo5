# AulaLista: convenciones del proyecto (equipo T005)

## Producto
Copiloto del docente de colegio público (track «Copiloto del docente público»). Historia única: módulo → contexto confirmado → borrador con Amazon Bedrock → revisión humana → guardado → portafolio → registro de aplicación. Principio: la IA prepara; el docente decide.

## Stack y nombres
- `back/`: Python solo con biblioteca estándar; `boto3` únicamente dentro de funciones (lo trae el runtime de Lambda). Entrada Lambda: `back/app.py` → `handler`. Lógica en `back/aulalista/` (`service.py` reglas, `api.py` rutas, `validators.py`, `scoring.py`, `bedrock.py`, `repository.py` SQLite local, `dynamo_repository.py` DynamoDB).
- `front/`: HTML, CSS y módulos ES sin compilar. Paleta Halloween: negro `#0b0a0d`, naranja `#ff7a1a`, hueso `#f7efe3`; contraste AA y teclado completo. Todo texto dinámico entra como texto, nunca `innerHTML`.
- AWS (`template.yaml`): API Gateway HTTP API + una Lambda Python 3.12 (API y front en el mismo dominio) + DynamoDB `ItemsTable` (`pk`/`sk`/`doc`) + Bedrock Converse (`MODEL_ID`, por defecto `us.amazon.nova-lite-v1:0`). Variables: `TEAM_ID`, `TABLE_NAME`, `MODEL_ID`.
- Contratos públicos que no se cambian: `GET /health`, `POST/GET /items`, `POST /jobs` + `GET /jobs/{jobId}`.

## Cómo probar y desplegar
- Pruebas (una sola orden, sin instalar nada): `python3 -m unittest discover -s tests`. Bedrock y DynamoDB se simulan en `tests/test_app.py`.
- Local: `python3 back/run.py` (SQLite + plantilla local).
- Despliegue: `python3 scripts/build_lambda.py` y `sam deploy --template-file .aws-sam/build/template.yaml --stack-name aulalista-t005 --region us-east-1 --s3-bucket <bucket propio> --capabilities CAPABILITY_IAM --parameter-overrides TeamId=T005`. Después verificar con `curl` cada contrato.

## Qué no hacer
- No presentar la plantilla local ni el respaldo como salida de Bedrock; cada borrador declara su `generatedBy`.
- No inventar resultados de aprendizaje, valoraciones, ahorros de horas ni integraciones con APRENDE PERÚ. Datos simulados rotulados; nunca datos personales reales.
- Valoraciones: ausentes nunca valen 0, editar reemplaza, la autoevaluación del autor no cuenta y una versión nueva no hereda la media.
- No publicar ni marcar como revisado nada sin acción expresa del docente. No conectar sistemas externos ni secretos en el repositorio.
