# Requisitos: AulaLista, copiloto del docente público

## Introducción

Un docente de colegio público necesita convertir el contenido de un curso en una clase que pueda realizar con su grupo, su tiempo y sus materiales. Después necesita conservar su trabajo y registrar lo que observa al aplicarlo. Principio: la IA prepara; el docente decide.

Este spec cubre la fase 1 (backend y frontend locales con persistencia real). La fase 2 conecta servicios AWS (Bedrock, DynamoDB, API Gateway/Lambda).

## Historia principal

**Como** docente de colegio público, **quiero** transformar un módulo en una sesión adaptada, revisarla, guardarla y recuperar mi trabajo con sus registros, **para** preparar mi próxima clase y aprender de su aplicación.

## Requisitos y criterios de aceptación

### R1. Mi aprendizaje
1. WHEN el docente abre Mi aprendizaje THEN el sistema SHALL mostrar título, fuente, versión y fragmentos (M1–M3) del módulo precargado y rotulado como simulado.
2. WHEN pulsa «Usar en mi clase» THEN Mi aula SHALL abrirse con ese módulo seleccionado sin repetir datos.

### R2. Mi aula
1. WHEN el docente confirma módulo, grado, duración (10–180 min), materiales e indicaciones y pulsa «Crear borrador» THEN el sistema SHALL devolver una sesión con propósito, actividades con minutos, materiales y evidencia esperada.
2. El código SHALL validar formato, que los minutos sumen la duración, que las referencias existan en el módulo y que los materiales sean los declarados.
3. IF la generación falla o devuelve una sesión inválida THEN el sistema SHALL mostrar un error comprensible, conservar las entradas y permitir reintentar, sin crear sesiones.
4. La salida SHALL declarar su origen; la plantilla local SHALL rotularse «No es Amazon Bedrock».

### R3. Revisión humana
1. El resultado nace como borrador; solo una acción expresa («Guardar versión revisada» o «Marcar como revisada») lo marca revisado.
2. Una edición posterior, una regeneración o una copia SHALL crear un borrador que no hereda la revisión.
3. Una nueva versión SHALL conservar el historial anterior.

### R4. Mi portafolio
1. Las sesiones y versiones SHALL persistir en el servidor y recuperarse tras recargar.
2. El docente SHALL poder continuar la edición, crear copias, regenerar e imprimir.
3. Cada sesión admite registros de aplicación (fecha declarada, actividad, observación, próximo ajuste) ligados a una versión, rotulados «Registro simulado» en la demo.
4. La evidencia esperada y la observación declarada SHALL mostrarse por separado.

### R5. Mi red, Aprendemos juntos (extensión acotada)
1. El autor SHALL compartir una copia separada solo con confirmación expresa y desde una versión revisada; los registros privados no se copian.
2. La valoración de uso (1–5, cuatro criterios, «No puedo valorarlo») SHALL requerir declarar que se usó la actividad.
3. La media SHALL ser el promedio de promedios de valoraciones completas, con un decimal; ausentes nunca valen 0; editar reemplaza; la autoevaluación del autor no cuenta; una versión nueva no hereda la media.
4. El ejemplo simulado [5,4,4,5], [4,4,5,4], [5,5,4,4] SHALL dar 4,4/5, 3 valoraciones completas, «Pocas valoraciones», «Datos simulados».
5. Adaptar una experiencia SHALL crear un borrador que conserva la procedencia.

### R6. Mis oportunidades, Mi tiempo, Mi bienestar
1. Mis oportunidades SHALL presentarse como función futura, sin pagos ni reservas.
2. Hoy SHALL ofrecer «Preparar clase», «Mi portafolio» y sesiones recientes, sin cifras de horas ahorradas.
3. Las preferencias de aviso SHALL estar apagadas por defecto y no publicar nada sin confirmación.

### R7. Contratos verificables
1. GET /health SHALL responder 200 con {"status":"ok","team":"T005"}.
2. POST /items y GET /items/{id} SHALL persistir y devolver value; GET /items SHALL listar el elemento.
3. POST /jobs SHALL responder 202 con jobId y GET /jobs/{jobId} SHALL devolver status done y la entrada invertida mediante un worker real con estado persistido.
4. GET / SHALL responder 200 text/html sin redirecciones.

### R8. Calidad
1. Todo texto dinámico SHALL insertarse como texto, nunca como HTML.
2. La interfaz SHALL usar la paleta naranja y negro (tema Halloween) con contraste AA y navegación por teclado.
3. Una sola orden SHALL ejecutar todas las pruebas.
