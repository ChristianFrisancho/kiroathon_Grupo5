# AulaLista: ayuda al docente de colegio público a pasar del módulo del curso a una clase y a su portafolio

**Equipo T005, Los 4 del grupo 5 · Track: Copiloto del docente público.** *Del módulo del curso a la sesión de clase y al portafolio de evidencias.*

Un docente de colegio público necesita convertir el contenido de un curso en una clase para su grupo, su tiempo y sus materiales, conservar su trabajo y registrar lo que observa al aplicarla. Principio: **la IA prepara; el docente decide.**

**Demo desplegada:** https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com

## Estado

| Elemento | Implementado y probado en local | Desplegado y verificado en la URL pública |
|---|---|---|
| Recorrido módulo → borrador → revisión → portafolio → registro | Sí (16 pruebas en Chromium) | Versión anterior (fase 2) |
| Amazon Bedrock (Converse, `us.amazon.nova-lite-v1:0`) | Sí, con cliente simulado | Sí, generación real verificada con la fase 2 |
| Guardados atómicos, 409 ante conflicto, procedencia verificada por el servidor, claves de operación | Sí | **No desplegado** |
| Worker Lambda de `/jobs` (GET solo lee) | Sí, worker probado sin AWS | **No desplegado**: la URL usa todavía resolución al leer |
| Contratos `/health`, `/items`, `/jobs` | Sí | Sí (fase 2), con curl |
| Voz con Transcribe | No implementada (opcional) | — |

No se entrevistó a docentes ni se midió ahorro de tiempo o mejora educativa. Todos los datos son simulados y no hay integración con APRENDE PERÚ.

## Qué hace

- **Hoy / Mi tiempo:** «Preparar clase», «Mi portafolio», sesiones recientes y retomar un borrador.
- **Mi aprendizaje:** módulo «Escucha activa y diálogo respetuoso» (simulado) con fragmentos M1–M3 y «Usar en mi clase».
- **Mi aula:** grado, duración, materiales e indicaciones → «Crear borrador». **Amazon Bedrock** adapta el módulo y el código valida que los minutos sumen, que las referencias existan y que solo se usen los materiales declarados. Luego el docente edita y elige entre guardar un borrador o una versión revisada.
- **Mi portafolio:** sesiones, versiones, copia, regeneración, impresión y registros de aplicación (rotulados «Registro simulado»).
- **Mi red · Aprendemos juntos:** experiencia simulada con valoración de uso 1–5 (**4,4/5 · 3 valoraciones completas · Pocas valoraciones · Datos simulados**), comentarios de diseño y «Resumir acuerdos» con Bedrock. «Adaptar en Mi aula» lleva la mejora propuesta a Bedrock y conserva la procedencia.
- **Mis oportunidades:** función futura, sin pagos. **Mi bienestar:** preferencias apagadas por defecto.

## GenAI con propósito (`back/aulalista/bedrock.py`)

- **Prompts de sistema:** rol (docente de colegio público), reglas, límites de longitud como objetivos (400 caracteres por actividad, 120 palabras por resumen), tono y salida JSON. El módulo y las indicaciones van entre etiquetas como datos, nunca como instrucciones.
- **Entrada:** se valida antes de llamar al modelo; si es inválida, el modelo no se invoca.
- **Tiempos:** el plazo sale de la Lambda (`get_remaining_time_in_millis`) menos una reserva. El SDK no reintenta; ThrottlingException se reintenta solo si queda margen; sin margen, o si el modelo no responde, se entrega un **respaldo local rotulado**. Permisos, validación o una salida truncada responden **502**.
- **Salida:**
  - Se quitan las referencias inventadas, con aviso. Si ninguna actividad cita el módulo, es error.
  - Se avisa de recursos mencionados que no se declararon, para revisión humana.
  - Los minutos se reescalan con un mínimo de 1.
  - La pertinencia pedagógica la revisa el docente.
- **Procedencia:** el servidor emite el borrador con `draftId` y al guardar deriva `generatedBy` y `editedByTeacher`. El navegador no puede atribuir un texto a Bedrock, y guardar no vuelve a llamar al modelo.

## Integridad de datos

- Añadir una versión es atómico y condicionado a la versión de partida (SQLite: transacción con `UPDATE … WHERE current_version_id`; DynamoDB: TransactWriteItems con la condición `#doc = :expected` y un marcador por número de versión). Dos guardados desde la misma versión dan uno confirmado y un 409.
- Un fallo de escritura no deja versiones huérfanas. Actualizar fechas o conteos no restaura una versión vigente antigua.
- Las escrituras del frontend llevan `operationKey`: tras perder una confirmación, el mismo reintento devuelve el resultado ya guardado.

## Arquitectura (template.yaml)

API Gateway HTTP API → `AppFunction` (Python 3.12, 29 s; sirve la API y el front en el mismo dominio) → DynamoDB `ItemsTable` + Amazon Bedrock. `AppFunction` invoca de forma asíncrona `JobWorkerFunction` (`back/worker.py`), que solo accede a la tabla. Permisos: InvokeModel solo sobre el perfil `ModelId` y el modelo `FoundationModelId`; InvokeFunction solo sobre el worker. Output: `ApiUrl`.

## Ejecutar y probar

```bash
python3 back/run.py                      # local: http://127.0.0.1:8000 (SQLite + plantilla local)
python3 -m unittest discover -s tests    # todas las pruebas; DynamoDB y Bedrock simulados (tests/fakes.py)
```

- `tests/test_integrity.py`: reproducciones de la auditoría (concurrencia, escrituras parciales, procedencia, idempotencia, tiempos, consultas, salida de IA, migración).
- `tests/test_browser.py`: recorrido real en Chromium. Requiere `python3 -m pip install --user playwright && python3 -m playwright install chromium`; si no está, esas pruebas se omiten.
- Las pruebas son clases `unittest`, que pytest también descubre; en este entorno pytest no está instalado.

## Desplegar

```bash
python3 scripts/build_lambda.py          # equivale a `sam build` (Makefile): valida y reemplaza .aws-sam/build al final
sam deploy --template-file .aws-sam/build/template.yaml --stack-name aulalista-t005 --region us-east-1 \
  --s3-bucket <bucket propio> --s3-prefix aulalista --capabilities CAPABILITY_IAM \
  --parameter-overrides TeamId=T005 --no-confirm-changeset --no-fail-on-empty-changeset
```

Se usa `--s3-bucket` en lugar de `--resolve-s3` porque el rol de la cuenta del evento no puede crear el bucket que gestiona SAM.

## Kiro

Spec en `.kiro/specs/aulalista-copiloto-docente/` (requirements, design y tasks), steering en `.kiro/steering/project.md` y hooks con `when` y `then` en `.kiro/hooks/`.
