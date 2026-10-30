# Requisitos: Docente Presente, copiloto del docente público

## Introducción

Track «Copiloto del docente público», enunciado: «Del módulo del curso a la sesión de clase y al portafolio de evidencias». Un docente de colegio público necesita convertir el contenido de un curso en una clase que pueda realizar con su grupo, su tiempo y sus materiales; después, conservar su trabajo y registrar lo que observa al aplicarla. Principio: la IA prepara; el docente decide.

Fuente: `PLATAFORMA-PARA-KIRON.md` (secciones 3 a 10). En el repositorio no hay `CANVAS.md` ni `RETOS.md`; si aparecen, su contenido obligatorio sustituye al ejemplo. Todos los datos son simulados.

## Historia principal

**Como** docente de colegio público, **quiero** transformar un módulo en una sesión adaptada, revisarla, guardarla y recuperar mi trabajo con sus registros, **para** preparar mi próxima clase y aprender de su aplicación.

## Requisitos y criterios de aceptación

### R1. Mi aprendizaje
1. WHEN el docente abre Mi aprendizaje THEN el sistema SHALL mostrar título, fuente, versión y fragmentos (M1–M3) del módulo precargado y rotulado como simulado.
2. WHEN pulsa «Usar en mi clase» THEN Mi aula SHALL abrirse con ese módulo seleccionado sin repetir datos.

### R2. Mi aula con Amazon Bedrock
1. WHEN el docente confirma módulo, grado, duración (10–180 min), materiales e indicaciones y pulsa «Crear borrador» THEN Amazon Bedrock (API Converse) SHALL devolver una sesión con propósito, actividades con minutos, materiales y evidencia esperada, con referencias a M1–M3.
2. El prompt SHALL incluir el contexto confirmado, el rol del docente de colegio público, el límite de longitud y el tono, y SHALL tratar módulo e indicaciones como datos, nunca como instrucciones.
3. El código SHALL validar que los minutos sumen la duración, que las referencias existan y que los materiales sean los declarados. Una entrada inválida (falta el grado, duración fuera de rango, indicaciones de más de 500 caracteres) SHALL rechazarse sin llamar al modelo.
4. IF Bedrock responde ThrottlingException AND queda presupuesto para otro intento dentro del plazo de la Lambda THEN el sistema SHALL reintentar con espera. IF no queda presupuesto o el modelo no responde THEN SHALL entregar antes del límite un borrador de respaldo rotulado «Respaldo local». IF ocurre un error de permisos, validación o una salida ilegible o truncada THEN SHALL responder 502 con un mensaje comprensible, conservando las entradas.
5. El servidor SHALL emitir cada borrador con `draftId` y guardar su origen. Al guardar, `generatedBy` SHALL derivarse de ese registro; un `generatedBy` enviado por el navegador SHALL ignorarse. La sesión SHALL indicar `editedByTeacher` si el contenido difiere del borrador. Guardar no SHALL volver a llamar al modelo.
6. IF ninguna actividad del modelo cita un fragmento real THEN el borrador SHALL rechazarse. Las referencias inventadas SHALL quitarse con aviso, y los recursos mencionados y no declarados SHALL avisarse para revisión humana.

### R3. Revisión humana
1. El resultado nace como borrador; solo una acción expresa («Guardar versión revisada» o «Marcar como revisada») lo marca revisado.
2. Una edición posterior, una regeneración o una copia SHALL crear un borrador que no hereda la revisión, y SHALL conservar el historial.
3. WHEN dos guardados parten de la misma versión THEN solo uno SHALL confirmarse y el otro SHALL recibir 409 `version_conflict`. Nunca SHALL existir dos versiones con el mismo número. El frontend SHALL conservar la edición y ofrecer abrir la versión nueva o guardarla como sesión nueva.

### R4. Mi portafolio
1. Las sesiones y versiones SHALL persistir en DynamoDB y recuperarse tras recargar o en otro contenedor de Lambda.
2. El docente SHALL poder continuar la edición, crear copias, regenerar e imprimir.
3. Cada sesión admite registros de aplicación (fecha declarada, actividad, observación, próximo ajuste) ligados a la versión elegida en «Versión utilizada» y rotulados «Registro simulado».
4. Un fallo de escritura SHALL dejar los datos como estaban: sin versiones huérfanas ni versión vigente restaurada.
5. Repetir una escritura con la misma `operationKey` y el mismo contenido SHALL devolver el resultado ya confirmado, sin duplicar. La misma clave con otro contenido SHALL dar 422.
6. El texto de formularios no enviados (registro, compartir) SHALL conservarse al cambiar de versión o recargar.

### R5. Mi red, Aprendemos juntos
1. Compartir SHALL exigir confirmación expresa y una versión revisada; los registros privados no se copian.
2. La valoración 1–5 (cuatro criterios, «No puedo valorarlo») SHALL exigir declarar el uso; la media es el promedio de promedios de valoraciones completas, con un decimal; ausentes ≠ 0; editar reemplaza; la autoevaluación del autor no cuenta.
3. El ejemplo [5,4,4,5], [4,4,5,4], [5,5,4,4] SHALL mostrarse como 4,4/5 · 3 valoraciones completas · Pocas valoraciones · Datos simulados.
4. «Resumir acuerdos» SHALL usar Bedrock solo con los registros guardados (máx. 120 palabras), con respaldo local rotulado.
5. Adaptar una experiencia SHALL enviar la mejora propuesta a Bedrock y crear un borrador con procedencia, que empieza sin valoraciones.

### R6. Mis oportunidades, Mi tiempo, Mi bienestar
1. Mis oportunidades SHALL presentarse como función futura, sin pagos.
2. Hoy SHALL ofrecer «Preparar clase», «Mi portafolio» y sesiones recientes, sin cifras de horas ahorradas.
3. Las preferencias de aviso SHALL estar apagadas por defecto.

### R7. Contratos de insignias (rutas públicas, sin autenticación)
1. GET /health SHALL responder 200 con {"status":"ok","team":"T005"}, tomando `team` de `TEAM_ID` (parámetro `TeamId`).
2. POST /items {"value"} SHALL responder 201 {id, value} y guardar en `ItemsTable`; GET /items/{id} SHALL devolverlo (404 si no existe); GET /items SHALL listar hasta 100 ítems, los más recientes primero, paginando la tabla completa.
3. POST /jobs {"input"} SHALL responder 202 {jobId}, guardar el trabajo en `ItemsTable` y despachar un worker independiente. GET /jobs/{jobId} SHALL solo leer y devolver status «done» con la entrada invertida antes de 12 s. Un fallo de despacho SHALL dejar el trabajo en `failed` y responder 503.
4. GET {ApiUrl} SHALL responder 200 text/html sin redirecciones.

### R8. Calidad
1. Todo texto dinámico SHALL insertarse como texto. Paleta naranja y negro con contraste AA.
2. Una sola orden SHALL ejecutar todas las pruebas, con DynamoDB y Bedrock simulados.

### R9. Infraestructura
1. `template.yaml` SHALL declarar todos los servicios usados (HTTP API, Lambda, DynamoDB, permiso `bedrock:InvokeModel`) y exponer el Output `ApiUrl`.
