# Plataforma para KIRON — Copiloto del docente público

**Equipo:** T005, Los 4 del grupo 5. **Producto:** AulaLista, nombre provisional.
**Versión:** 1.0 · 30 de octubre de 2026 · reglas y guías verificadas en navegador a las 11:52–11:54, hora de Lima.
**Destino:** documento autocontenido para compartir con KIRON y con la persona que desarrollará en Kiro. No se ha enviado automáticamente.

Este archivo explica el producto y cómo priorizar su construcción frente a la rúbrica. No acredita implementación, pruebas, despliegue ni aceptación pedagógica. Diferenciar siempre propuesto, implementado, probado, desplegado, enviado y evaluado. La meta es cubrir los criterios con evidencia real; ningún diseño garantiza el máximo puntaje ni ganar.

## 1. Idea y problema

Un docente de colegio público necesita convertir el contenido de un curso en una clase que pueda realizar con su grupo, su tiempo y sus materiales. Después necesita conservar su trabajo y registrar lo que observa al aplicarlo. Nuestra hipótesis es que acompañar ese recorrido reduce esfuerzo y permite aprender de experiencias propias y ajenas.

La plataforma conecta preparación, revisión, portafolio y aprendizaje compartido. En su evolución permitirá compartir recursos, colaborar y ofrecer voluntariamente experiencia profesional mediante materiales, mentorías o talleres.

**Principio:** la IA prepara; el docente decide. **Visión:** lo que una persona aprende enseñando puede ayudar a otra a preparar su siguiente clase.

No se entrevistó a docentes durante este trabajo ni se midió ahorro o mejora educativa. La investigación pública orienta el problema; la utilidad de esta solución sigue por validar. No afirmar que todos los docentes trabajan el mismo número de horas ni que todo el trabajo administrativo es no remunerado.

## 2. Encaje exacto en el concurso

Track confirmado: **Copiloto del docente público**. Usuario principal: docente de colegio público. Enunciado visible: **«Del módulo del curso a la sesión de clase y al portafolio de evidencias»**.

Las reglas piden construcción de punta a punta en Kiro, datos simulados o públicos y ninguna conexión a sistemas externos. La guía de spec precisa usar la propia cuenta AWS y servicios declarados en `template.yaml`.

APRENDE PERÚ fue mencionado en el evento; su plataforma, módulo y relación exacta no se han identificado. No afirmar una integración. Antes de implementar, leer el módulo, CANVAS.md y RETOS.md reales cuando estén disponibles; un contenido obligatorio sustituye al ejemplo de este documento.

La visión completa tiene siete módulos; la entrega inicial demuestra una sola historia coherente. La rúbrica no contiene un criterio de cantidad de módulos. La recomendación estratégica es completar y probar el recorrido antes de ampliar funciones.

## 3. Los siete módulos conectados

### 3.1 Mi aprendizaje

**Función:** convertir un contenido de formación en punto de partida de una clase.

Muestra título, fuente, versión y fragmentos del módulo. El docente consulta el contenido y pulsa **Usar en mi clase**. La selección llega a Mi aula sin repetir datos. Para la demo basta un módulo precargado e identificado. Las consultas explicativas y rutas de formación son evolución.

La fuente permanece visible desde la sesión. Generar una clase no significa haber completado o aprobado un curso. La IA puede posteriormente explicar conceptos con referencias; el docente decide qué aplicar.

### 3.2 Mi aula

**Función:** preparar una sesión adaptada a condiciones concretas.

Entradas: módulo, grado, duración en minutos, materiales e indicaciones opcionales. Acción **Crear borrador**. Bedrock devuelve propósito, actividades con tiempos, materiales y evidencia esperada, con referencias inspeccionables. El docente edita, descarta, guarda borrador o guarda una versión revisada.

El código valida formato, minutos e IDs. La revisión pedagógica es humana. Mostrar espera y errores sin borrar las entradas. La voz puede añadirse como entrada optativa: transcribir, corregir y confirmar antes de generar.

### 3.3 Mi portafolio

**Función:** conservar sesiones, versiones y registros de aplicación aportados por el docente.

Lista las sesiones y permite recuperar tras recargar, continuar edición y crear copias. Cada sesión admite un registro textual opcional: fecha declarada, actividad realizada, observación y próximo ajuste. Se liga a la versión usada. En demo se marca **Registro simulado**.

Separar evidencia esperada de observación declarada. Generar, revisar o guardar no significa haber impartido la clase ni demostrar aprendizaje. La IA no inventa resultados. Guardar y recuperar usan persistencia real, no solo memoria del navegador.

### 3.4 Mi red — Aprendemos juntos

**Función:** aprender de actividades y experiencias compartidas por colegas.

Banco de experiencias con propósito, grado, materiales, descripción, observación y propuesta de mejora. El autor elige qué compartir mediante una copia separada del portafolio; no publica sus registros privados automáticamente.

Otros pueden dejar comentarios de diseño, registrar experiencia de uso, valorar una versión y adaptarla en Mi aula. La adaptación conserva procedencia. La IA ayuda a buscar, resumir acuerdos/desacuerdos y proponer cambios sustentados en experiencias autorizadas.

Para la IAThon, una extensión acotada puede mostrar una experiencia y valoraciones simuladas, con cálculo y adaptación funcionales. No presentar una comunidad real inexistente.

### 3.5 Mis oportunidades

**Función futura:** ofrecer recursos originales, mentorías o talleres de forma voluntaria.

Una oferta describe destinatarios, contenido, modalidad, duración, disponibilidad y precio elegido por el docente. La IA ayuda a redactar y encontrar solicitudes compatibles; el autor decide publicar y aceptar. Clases complementarias para familias pueden ser una etapa posterior.

Derechos de uso, reservas, pagos, cancelaciones y atención requieren desarrollo propio. Publicar no equivale a ingresar dinero. No convertir automáticamente materiales ajenos en vendibles. No implementar transacciones para la primera demo.

### 3.6 Mi tiempo

**Función:** preparar y retomar el trabajo sin reconstruirlo.

Portada mínima con **Preparar clase**, **Mi portafolio** y sesiones recientes. Evolución: agenda interna, fechas, pendientes y avisos elegidos por el docente. Ordenar fechas y guardar estados no necesita IA; sugerir reutilización puede incorporarla.

No mostrar ahorros de horas sin medición. El docente controla prioridades y recordatorios. No integrar calendarios externos en esta IAThon.

### 3.7 Mi bienestar

**Función transversal:** respetar los límites de la persona que enseña.

Pocos pasos, errores comprensibles, posibilidad de detenerse y retomar, recuperación del trabajo y notificaciones elegidas. Futuro: horarios y disponibilidad para colaborar o impartir talleres, con preferencias separadas del perfil público.

No requiere IA en el núcleo. La voz sirve para interactuar; no se utiliza para inferir emociones, salud o calidad profesional. Beneficios sobre bienestar siguen por validar.

## 4. Única historia que debe funcionar hoy

**Como docente de colegio público, quiero transformar un módulo en una sesión adaptada, revisarla, guardarla y recuperar mi trabajo con sus registros, para preparar mi próxima clase y aprender de su aplicación.**

Cuatro vistas posibles, incluso en una sola página:

| Vista | Contenido | Comprobación |
|---|---|---|
| Hoy | Preparar clase / Mi portafolio | Se comprende qué hacer sin explicación |
| Preparar | Módulo y contexto editable | Lo que entra al modelo coincide con lo confirmado |
| Revisar | Resultado, referencias, edición y guardado | La persona corrige y decide la versión |
| Portafolio | Sesiones, recuperación y registro de aplicación | Lo guardado persiste después de recargar |

**Caso simulado:** módulo «Escucha activa y diálogo respetuoso»; cuarto de primaria; 45 minutos; pizarra, papel y lápiz. No es currículo oficial ni un curso identificado de APRENDE PERÚ.

Fragmentos de entrada:

- **M1:** Escuchar a otra persona requiere darle tiempo para terminar y atender a lo que expresa. En una actividad por parejas se pueden alternar los papeles de quien habla y quien escucha.
- **M2:** Parafrasear consiste en expresar con palabras propias lo que se entendió y preguntar a la otra persona si esa interpretación es correcta. La persona que habló puede aclarar o corregir.
- **M3:** Las preguntas de aclaración buscan comprender mejor el mensaje. Se puede cerrar una actividad pidiendo explicar una idea escuchada y describir cómo se comprobó su comprensión.

La generación necesita conexión. Un material imprimible podrá usarse después en el aula. Una salida precargada de ejemplo debe estar rotulada; no presentarla como generación real.

## 5. IA y control humano

| Componente | Responsabilidad | Prioridad |
|---|---|---|
| Kiro | Construcción real con spec, steering, hooks y pruebas | Obligatorio por el evento |
| Bedrock | Adaptar el módulo a una sesión editable | Núcleo |
| Software convencional | Validar estructura, minutos, IDs; guardar, versionar y calcular medias | Núcleo |
| Docente | Confirmar contexto, revisar, corregir y decidir guardar/compartir | Núcleo |
| Transcribe | Voz → texto corregible | Opcional tras completar el núcleo |
| Polly / OCR / búsqueda semántica | Lectura en voz, ingreso de documentos y búsqueda ampliada | Evolución |

Human in the loop es el diseño de decisiones, no otro modelo: el resultado nace como borrador; una acción expresa revisa una versión; una edición posterior crea otro borrador. La aplicación declarada y la publicación son estados separados. Guardar un borrador está permitido.

Mostrar fuente y restricciones consideradas. Tratar módulo/transcripción como datos, nunca como instrucciones capaces de aprobar o publicar. Ante fallos conservar edición, mostrar error y permitir reintento controlado. La demo pública usa únicamente datos simulados; privacidad productiva requiere identidad y autorización propias.

## 6. Aprendizaje colectivo y puntuación del producto

**Ciclo:** preparar → aplicar → registrar → compartir una copia → recibir sugerencias → adaptar → volver a probar.

La ficha de experiencia conserva contexto, observación y mejora propuesta. La IA consulta experiencias autorizadas y muestra procedencia; no se presume reentrenamiento del modelo con cada interacción.

**Valoración de uso 1–5**, asociada a recurso y versión:

1. Claridad de instrucciones.
2. Viabilidad con tiempo y materiales declarados.
3. Coherencia de la actividad con el propósito.
4. Apoyo para observar comprensión del grupo.

Quien declara haber usado la actividad añade contexto y comentario de mejora. Quien solo la leyó deja comentario de diseño separado. Permitir «No puedo valorarlo»; ausentes nunca se convierten en cero. La autoevaluación del autor no entra en la media comunitaria.

Media general: promedio de los cuatro criterios por valoración completa, luego promedio entre valoraciones completas; mostrar un decimal, número de completas y parciales, contexto y fecha. Sin completas: «Sin valoración general». Con 1–4 completas: «Pocas valoraciones», umbral propuesto de interfaz, no garantía estadística. Una valoración activa por usuario/versión; editar reemplaza, no duplica. Versiones nuevas no heredan la media anterior.

Ejemplo simulado: [5,4,4,5], [4,4,5,4] y [5,5,4,4] → **4,4/5 · 3 valoraciones completas · Pocas valoraciones · Datos simulados**. No equivale a 88 % de eficacia ni califica profesionalmente al docente.

Reconocimientos propuestos: experiencia compartida, mejora documentada y recurso adaptado por otra persona, vinculados a acciones comprobables. No premiar publicar en masa ni votar positivo. Para una comunidad real hacen falta identidad, control de duplicados, reporte y revisión humana de disputas.

**Esta puntuación es una función del producto. No añade una categoría ni modifica los puntos oficiales de la IAThon.**

## 7. Arquitectura y datos mínimos

Inspeccionar el kit real. El prompt oficial parte de API Gateway HTTP, Lambda Python 3.12, DynamoDB y Bedrock en `template.yaml`, con cambios en `src/app.py` y `src/web/`. Reutilizarlo antes de añadir infraestructura. Medir generación; si el timeout exige trabajo asíncrono, implementar worker real y estado persistido. Responder 202 por sí solo no ejecuta trabajo de fondo.

Entidades propuestas:

- **Module:** id, version, title, sourceLabel, fragments[{id,text}], isSimulated.
- **LessonVersion:** sessionId, versionId, moduleId/version, context, content, reviewStatus, timestamps.
- **ApplicationRecord:** id, sessionId/versionId, fecha declarada, actividad, observación, próximo ajuste e isSimulated.
- **Experience/Review**, solo extensión: copia compartible, contexto, versión, tipo de revisión, cuatro valores o null, comentarios e isSimulated.

Operaciones: leer módulo, generar, guardar, listar/recuperar, revisar versión y añadir registro. Acordar nombres de rutas con el código existente; no romper los contratos de insignias. El backend confirma guardado, valida versiones y calcula medias. Una nueva versión no borra el historial.

## 8. Rúbrica oficial y evidencia que debemos producir

Fuente primaria: https://dse8jbss45rea.cloudfront.net/reglas . Reglas y guías leídas 11:52–11:54 Lima. Los máximos son posibilidades de evaluación, no puntos asegurados.

| Categoría | Máximo | Qué debe quedar demostrable |
|---|---:|---|
| Código | 350 | Historia del track implementada, proceso Kiro real, GenAI central, pruebas e infraestructura |
| Pitch | 250 | Problema/persona claros, demo concreta, siguiente paso y discurso coherente con lo construido |
| Frontend | 150 | URL accesible, recorrido completo, usabilidad y resultado coherente |
| Documento | 100 | Problema, solución, uso de Kiro, AWS y demo/impacto explicados con evidencia |
| Bonus | 150 | Insignias y retos verificados, con tope compartido |
| **Total** | **1000** | Cuatro entregas y bonus; ampliar funciones no sustituye entregar |

### Código — 350

Estático: **100**, por specs, steering, hooks, README, infraestructura como código y pruebas. No se observó reparto público de esos 100 por archivo; no inventarlo.

Evaluación con agente: problema **50**, solución **50**, implementación **60**, proceso Kiro **50** y GenAI con propósito **40**.

Acciones: primera línea de README nombra el problema y al docente de colegio público; spec propia con una historia y aceptación; Bedrock participa realmente en el flujo; persistencia y errores se prueban; README, UI y código describen la misma versión.

ZIP máximo **200 MB**. La guía pide `.kiro/` completa, `template.yaml`, `src/`, `tests/` y `README.md`. El portal enumera carpetas ignoradas al evaluar, como `node_modules`, `.venv`, `.git`, `dist`, `build` y `cdk.out`; esto no autoriza incluir secretos en ellas. Ejecutar las pruebas relevantes; la guía del kit indica `python -m pytest -q tests`. Comprobar contenido del ZIP y ausencia de secretos/datos personales. No fabricar specs, hooks o historial para aparentar uso de Kiro.

### Pitch — 250

Discurso **200**: problema25, persona15, demo30, siguiente paso15, estructura15, mensaje30, concreción20, cierre20 y coherencia30.

Entrega oral **50**: ritmo15, muletillas10, pausas10, duración10 y dicción5. Audio en español de **2–3 minutos**, tope **3:00**; se evalúa la transcripción de los primeros tres minutos. Ensayar y escuchar la grabación; una duración escrita no acredita duración real.

Guion recomendado: escena hipotética concreta → problema → recorrido que funciona → dónde interviene IA y docente → evidencia disponible → próximo paso → cierre. Comunidad/ingresos se nombran como evolución, sin dedicarles la mayor parte del pitch. No prometer ahorro medido, eficacia, uso real o afiliación institucional inexistentes.

### Frontend — 150

Carga40, flujo principal50, usabilidad30 y coherencia30. HTTPS público; GET debe devolver **200 text/html**, sin redirecciones y URL sin barra final. La guía permite login únicamente con usuario de demo y credenciales en la nota; proponemos demo sin login con datos simulados.

El agente navega dentro del mismo dominio con **hasta 16 acciones**. Nota: **1–3 pasos**, máximo **240 caracteres**; GenAI en campo separado, máximo **240**. Sin correos ni secuencias de 7 dígitos o más según guía del registro.

Precargar el caso, hacer visibles generar/editar/guardar/abrir, mostrar espera y errores. Contar acciones reales. No hacer obligatoria voz, impresión, comunidad ni un tour para demostrar el núcleo.

Textos propuestos para usar **solo si están implementados**:

**Nota del flujo:**
1) Genera la sesión con el caso precargado. 2) Edita y guarda. 3) Abre Mi portafolio, recupera la sesión y añade un registro simulado de aplicación.

**Funcionalidad GenAI:**
Bedrock adapta el módulo al grado, tiempo y materiales. Pulsa Crear borrador; revisa las actividades y sus referencias. Puedes editar y guardar la versión revisada.

Comprobar etiquetas reales y ajustar estos textos antes de registrar.

### Documento — 100

Problema25, solución25, Kiro15, AWS15 y demo/impacto20. **PDF o PPTX, máximo25 MB.** Este MD sirve como contexto de trabajo; no sustituye ese entregable aceptado por el portal.

Contenido propuesto: problema/persona y fuente; historia y alcance; capturas reales del flujo; arquitectura desplegada; cómo se usaron specs/steering/hooks; prueba de recuperación y error controlado; impacto buscado y siguiente validación. Separar observación real, simulación e hipótesis. Reutilizar material del producto, sin afirmar resultados que no se hayan comprobado.

### Bonus — hasta150

| Insignia | Puntos | Contrato visible |
|---|---:|---|
| API viva | 20 | GET /health → 200 con {"status":"ok","team":"T005"} |
| Persistencia | 25 | POST /items {"value":nonce} →200/201 {id}; GET /items/{id} conserva value; GET /items incluye el nonce |
| Asíncrono o agente | 35 | POST /jobs {"input":nonce} →202 {jobId}, admite200/201; GET /jobs/{jobId} antes de12s → {"status":"done","output":nonce invertido} |
| Maestría Kiro | 30 | requirements.md, design.md y tasks.md propios en .kiro/specs/<feature>/; ≥300 caracteres cada uno; steering≥200; hook con when y then |
| GenAI con propósito | 40 | Bedrock o AgentCore central, prompts y errores; verificación por agente, con corroboración de código si se declara en frontend |

API, persistencia y asíncrono se verifican contra la URL base; son públicos según contrato. El plazo12s es para el nonce de la insignia, no para generar una clase. Kiro y GenAI se otorgan mediante evaluación; no asumirlas por crear archivos o mostrar una interfaz.

Usar hooks compatibles con versión y ejemplo reales del kit y con el contrato visible. Si discrepan, resolverlo con organización; no sustituir el esquema a ciegas.

Las cinco insignias suman150. Retos sorpresa comparten el mismo límite: incremento posible = mínimo(puntos del reto, espacio restante hasta150), sujeto a cumplimiento. Consultar solo retos activos y su plazo; la lista de /reglas es catálogo. No sacrificar una entrega completa por bonus ya topado.

## 9. Elegibilidad, horario e iteración

Finalistas: diez mayores totales entre equipos con **código y pitch evaluados y puntaje mayor que cero**, sin cupo por track. Jurado humano decide el podio. Código+pitch suman600 posibles, pero frontend/documento/bonus completan los400 restantes.

El track se fija cuando se evalúa el primer código; después solo los organizadores pueden cambiarlo. El track confirmado de este equipo es Copiloto del docente público.

Horario publicado de Lima: apertura10:20; recordatorio segunda toma12:45; último envío recomendado13:00; **code freeze13:15**; finalistas13:20; cierre del portal13:21. No interpretar13:21 como plazo adicional para enviar código.

A las11:53 se verificó T005 en **CONSTRUCCIÓN EN CURSO**, con entradas de archivos, registro de frontend y grabación habilitados; 0/1000 y sin historial. No había retos activos. La apertura operativa ocurrió después de la hora anunciada, pero no se observó extensión del freeze. Esto es un snapshot, no estado permanente.

Reenvío del mismo tipo cada5min; verificaciones de insignias/retos cada1min. Cuenta la última entrega evaluada; evaluación provisional conserva mejor puntaje. La plataforma indica tiempos orientativos de evaluación: código1–3min, pitch2–5min, documento/frontend1–4min. No son garantías. Un fallo de plataforma se reintenta hasta3 veces; fallo de entrega requiere corrección.

**Plan de ejecución propuesto desde la lectura actual:**

1. Revisar inmediatamente kit, accesos y avance existente. Acordar una única historia y formato entre UI/API.
2. Completar núcleo funcional y preparar pitch/documento en paralelo; primera evaluación en cuanto haya una versión utilizable. No esperar comunidad, voz ni estética final.
3. Cubrir las cuatro entregas y preparar contratos de insignias; evaluar feedback real por categoría.
4. Después de la primera ronda, elegir la corrección con mayor efecto observable. Extensión de experiencias/puntuación solo si hay margen y no rompe el núcleo.
5. Usar13:00 como objetivo interno de último candidato, dejando margen antes de13:15. Si el horario oficial cambia, actualizar este plan.

Responsabilidades: desarrollo backend/GenAI/persistencia e infraestructura; desarrollo frontend/recorrido y proceso Kiro coordinado; marketing guion y ensayo; responsable de producto/fuentes documento y coherencia. Ajustar personas disponibles sin duplicar trabajo.

## 10. Pruebas de aceptación y decisiones de recorte

- Una persona ajena al código puede generar, abrir una referencia, editar, guardar, recargar y recuperar.
- Lo generado usa el módulo/contexto correctos; tiempos suman y referencias existen. La pertinencia pedagógica requiere revisión aparte.
- Salida incompleta, timeout y fallo de guardado muestran error; edición no se pierde ni se simula éxito.
- Revisión se liga a versión; regeneración no hereda aprobación. Registro simulado no equivale a clase aplicada.
- Frontend accesible por GET y recorrido dentro de16 acciones; nota≤240 y GenAI≤240.
- Código, frontend, documento y pitch coinciden en capacidades efectivas. La visión futura está identificada.
- Cada contrato de insignia se prueba y su otorgamiento se comprueba en portal mediante decisión del equipo.
- Si hay puntuación: ausentes≠0, edición no duplica voto, versión nueva no hereda media y ejemplo simulado da4,4.

**Recortar primero:** pagos/reservas, red completa, chat, traducciones no validadas, OCR, TTS, varios agentes, multigrado y nuevas integraciones. La demostración acotada de aprendizaje colectivo y la voz son ampliaciones propuestas, no condiciones para enviar el núcleo.

## 11. Encargo autocontenido para KIRON / desarrollador

Usa este documento como contexto de producto y mapa de la rúbrica, no como evidencia de funcionalidades terminadas. Identifica qué existe realmente. Empieza con el prompt oficial de spec del portal y los archivos del kit disponibles; declara lo ausente sin inventarlo.

Desarrolla en Kiro la historia del docente: módulo/versionado → contexto confirmado → adaptación real con Bedrock → edición y revisión humana → persistencia y recuperación → registro textual opcional de aplicación. Usa datos simulados y servicios AWS declarados. No alteres el track ni contratos del kit. No generes hechos de aprendizaje, credenciales o proceso Kiro ficticios.

Prioriza flujo, errores, coherencia, cuatro entregas y contratos verificables. Después evalúa la extensión mínima experiencia/valoración/adaptación y voz opcional. No implementes toda la visión comercial como alcance obligatorio de hoy.

Entrega: tareas pequeñas con aceptación; reporte de implementado/probado/desplegado; pruebas realmente ejecutadas; URLs comprobadas; lista de pendientes. Prepara ZIP, notas del frontend, guion y contenido de documento coherentes con esa versión. La decisión de enviar y verificar en el portal corresponde al equipo; este archivo no autoriza envíos automáticos.

## Fuentes y notas de evidencia

- [Reglas, rúbrica y guías oficiales](https://dse8jbss45rea.cloudfront.net/reglas): leídas11:52–11:54 Lima, 30-oct-2026. Fuente prioritaria; revisar cambios posteriores.
- [Portal propio](https://dse8jbss45rea.cloudfront.net/team): track, apertura operativa y estado de T005 observados; sin códigos de acceso en este documento.
- [ENDO2021, Minedu](https://www.minedu.gob.pe/politicas/docencia/pdf/endo/2021/endo2021-0-nacional.pdf): 63,7% declaró más de3 horas semanales fuera del horario para preparación y administración agrupadas; encuesta de2021 en pandemia, no diagnóstico actual de toda la profesión ni tiempo atribuible solo a papeleo.
- [UNESCO, competencias docentes en IA](https://www.unesco.org/en/articles/ai-competency-framework-teachers): referencia de agencia y aprendizaje profesional; no certifica este diseño.
- [NIOT, feedback profesional](https://evidenceportal.niot.org.uk/toolkit/feedback-for-professional-learning/): referencia para ciclos de reflexión/acción; no demuestra eficacia de nuestra plataforma.

La investigación, la rúbrica y las funciones propuestas cumplen papeles distintos. No presentar recomendaciones del equipo como reglas del concurso ni los máximos de la rúbrica como puntajes obtenidos.
