# AulaLista: ayuda al docente de colegio público a pasar del módulo del curso a una clase y a su portafolio

**Equipo T005, Los 4 del grupo 5 · Track: Copiloto del docente público.** *Del módulo del curso a la sesión de clase y al portafolio de evidencias.*

Un docente de colegio público necesita convertir el contenido de un curso en una clase para su grupo, su tiempo y sus materiales, conservar su trabajo y registrar lo que observa al aplicarla. Principio: **la IA prepara; el docente decide.**

**Demo desplegada:** https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com

## Estado

| Elemento | Estado |
|---|---|
| Backend (`back/`) y frontend (`front/`) | Implementados, probados y desplegados |
| Amazon Bedrock (Converse, `us.amazon.nova-lite-v1:0`) | En el flujo central; verificado contra la URL desplegada |
| DynamoDB `ItemsTable` | Persistencia de sesiones, versiones, registros, valoraciones, items y jobs |
| Contratos `/health`, `/items`, `/jobs` | Verificados con curl contra la URL desplegada |
| Voz con Transcribe | No implementada (opcional) |

No se entrevistó a docentes ni se midió ahorro de tiempo o mejora educativa. Todos los datos son simulados y no hay integración con APRENDE PERÚ.

## Qué hace

- **Hoy / Mi tiempo:** «Preparar clase», «Mi portafolio», sesiones recientes y retomar un borrador.
- **Mi aprendizaje:** módulo «Escucha activa y diálogo respetuoso» (simulado) con fragmentos M1–M3 y «Usar en mi clase».
- **Mi aula:** grado, duración, materiales e indicaciones → «Crear borrador». **Amazon Bedrock** adapta el módulo y el código valida que los minutos sumen, que las referencias existan y que solo se usen los materiales declarados. Luego el docente edita y elige entre guardar un borrador o una versión revisada.
- **Mi portafolio:** sesiones, versiones, copia, regeneración, impresión y registros de aplicación (rotulados «Registro simulado»).
- **Mi red · Aprendemos juntos:** experiencia simulada con valoración de uso 1–5 (**4,4/5 · 3 valoraciones completas · Pocas valoraciones · Datos simulados**), comentarios de diseño y «Resumir acuerdos» con Bedrock. «Adaptar en Mi aula» lleva la mejora propuesta a Bedrock y conserva la procedencia.
- **Mis oportunidades:** función futura, sin pagos. **Mi bienestar:** preferencias apagadas por defecto.

## GenAI con propósito (`back/aulalista/bedrock.py`)

- Prompts de sistema con el rol (docente de colegio público), las reglas, el límite de longitud (400 caracteres por actividad, 120 palabras por resumen), el tono y la salida JSON. El módulo y las indicaciones van entre etiquetas como datos, nunca como instrucciones.
- La entrada se valida antes de llamar al modelo: si falta el grado, la duración está fuera de 10–180 o las indicaciones pasan de 500 caracteres, responde un error sin llamar al modelo.
- Una ThrottlingException se reintenta con espera.
- Si el modelo no responde, se entrega un borrador de **respaldo local rotulado**, y el flujo sigue.
- Otros errores responden **502** con un mensaje comprensible.
- La salida pasa por una validación determinista y por la revisión del docente antes de guardarse.

## Arquitectura (template.yaml)

API Gateway HTTP API → una Lambda Python 3.12 (`back/app.py`, sirve la API y el front en el mismo dominio) → DynamoDB `ItemsTable` + Amazon Bedrock. Parámetros: `TeamId` (→ `TEAM_ID`) y `ModelId` (→ `MODEL_ID`). Output: `ApiUrl`.

## Ejecutar y probar

```bash
python3 back/run.py                      # local: http://127.0.0.1:8000 (SQLite + plantilla local)
python3 -m unittest discover -s tests    # todas las pruebas; DynamoDB y Bedrock simulados
```

Las pruebas son clases `unittest`, que pytest también descubre (`python -m pytest -q tests`); en este entorno pytest no está instalado.

## Desplegar

```bash
python3 scripts/build_lambda.py          # equivale a `sam build` (Makefile) sin necesitar make
sam deploy --template-file .aws-sam/build/template.yaml --stack-name aulalista-t005 --region us-east-1 \
  --s3-bucket <bucket propio> --s3-prefix aulalista --capabilities CAPABILITY_IAM \
  --parameter-overrides TeamId=T005 --no-confirm-changeset --no-fail-on-empty-changeset
```

Se usa `--s3-bucket` en lugar de `--resolve-s3` porque el rol de la cuenta del evento no puede crear el bucket que gestiona SAM.

## Kiro

Spec en `.kiro/specs/aulalista-copiloto-docente/` (requirements, design y tasks), steering en `.kiro/steering/project.md` y hooks con `when` y `then` en `.kiro/hooks/`.
