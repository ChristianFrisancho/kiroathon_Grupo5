# PROMPT MAESTRO DEFINITIVO — AULALISTA
## Copiloto pedagógico, comunidad profesional e inteligencia colectiva con Amazon Web Services

### MISIÓN PARA KIRO

Actúa como un equipo senior formado por un arquitecto AWS, un ingeniero full-stack, un especialista en inteligencia artificial generativa, un ingeniero de sistemas RAG, un especialista en bases de datos, un diseñador UX/UI y un experto en tecnología educativa.

Tu misión es **DISEÑAR, IMPLEMENTAR, EJECUTAR Y VALIDAR** AulaLista, una plataforma inteligente para docentes que conecta aprendizaje, planificación, experiencias educativas, colaboración profesional y mejora continua.

Estamos participando en una IAThon y disponemos de aproximadamente cuatro horas para construir un MVP demostrable.

No quiero únicamente diagramas, documentación, pantallas estáticas ni una propuesta conceptual. Quiero una aplicación funcional, con servicios AWS reales, persistencia, generación con Amazon Bedrock, interacción conversacional, comunidad docente y mecanismos para aprovechar experiencias compartidas.

**Restricción tecnológica:** toda la infraestructura cloud debe utilizar Amazon Web Services. Se permiten frameworks y bibliotecas open source para desarrollar la aplicación, pero no sustituir AWS por proveedores externos de nube, autenticación, base de datos o IA.

Kiro será nuestro agente de desarrollo. Amazon Bedrock será el motor de inteligencia artificial utilizado dentro del producto.

Prioriza funcionalidades completas y comprobables por encima de funcionalidades visualmente impresionantes que no estén conectadas.

---

# 1. VISIÓN DE AULALISTA

AulaLista es una plataforma inteligente que ayuda a docentes de diferentes contextos a preparar clases, aprovechar recursos pedagógicos, compartir experiencias y mejorar sus estrategias mediante inteligencia artificial y colaboración.

Nuestra visión es:

**"Lo que un docente aprende enseñando puede ayudar al siguiente a preparar mejor su clase".**

El producto parte de seis problemas.

**Primero:** muchos docentes no saben cómo comenzar a utilizar una herramienta de inteligencia artificial ni qué preguntarle.

**Segundo:** transformar capacitaciones, documentos y conocimientos en actividades prácticas requiere tiempo.

**Tercero:** las condiciones educativas son diversas. No todas las aulas cuentan con los mismos recursos, materiales, tecnologías o tiempo disponible.

**Cuarto:** muchas experiencias pedagógicas valiosas permanecen aisladas y no llegan a otros docentes.

**Quinto:** compartir una actividad no explica necesariamente cómo funcionó, qué dificultades aparecieron ni cómo podría mejorarse.

**Sexto:** el trabajo de planificación y reflexión suele fragmentarse y no siempre queda disponible para futuras clases.

AulaLista responde a estos problemas mediante un copiloto conversacional, una biblioteca de recursos, un portafolio persistente y una comunidad inteligente.

La plataforma debe funcionar para educación inicial, primaria, secundaria, educación técnica, formación profesional y otros contextos educativos.

Perú será el escenario inicial de demostración, pero la arquitectura debe ser generalizable a otros países.

No asumir condiciones materiales por ubicación geográfica. Los recursos y limitaciones deben declararse, recuperarse del perfil o confirmarse por el docente.

---

# 2. EL CICLO PRINCIPAL DEL PRODUCTO

Toda la plataforma debe articularse alrededor de este ciclo:

**COMENZAR → PREPARAR → APLICAR → REGISTRAR → COMPARTIR → RECIBIR SUGERENCIAS → ADAPTAR → VOLVER A PROBAR**

Desglose:

1. El docente entra a AulaLista.
2. El copiloto le ayuda a identificar qué necesita mediante preguntas rompehielo.
3. Selecciona recursos pedagógicos o experiencias de otros docentes.
4. Amazon Bedrock propone actividades adaptadas a su contexto.
5. El docente revisa, modifica y guarda.
6. Aplica la clase fuera de la plataforma.
7. Cuando regresa, registra voluntariamente lo observado.
8. Puede compartir una versión autorizada de la experiencia.
9. Otros docentes consultan, comentan y valoran la actividad.
10. La IA ayuda a identificar sugerencias fundamentadas.
11. Un docente puede crear una nueva versión aplicando esas sugerencias.
12. La versión conserva su procedencia y tiene su propio historial de valoraciones.
13. El proceso puede repetirse.

**Esta secuencia es la identidad central de AulaLista.**

La plataforma no debe limitarse a almacenar publicaciones. Debe conectar experiencias, condiciones de aplicación, reflexiones, sugerencias y versiones.

No todo el ciclo requiere IA. Las operaciones de guardado, permisos, puntuaciones y versionado deben implementarse mediante lógica determinista.

---

# 3. ESTRUCTURA DE LA PLATAFORMA

Mantener siete módulos principales:

1. **Mi aprendizaje:** llevo lo que aprendo a mi aula.
2. **Mi aula:** preparo clases adaptadas a mi realidad.
3. **Mi portafolio:** conservo, reviso y documento mi trabajo.
4. **Mi red:** comparto, descubro y colaboro con otros docentes.
5. **Mis oportunidades:** exploro posibilidades profesionales voluntarias.
6. **Mi tiempo:** organizo y recupero mi trabajo.
7. **Mi bienestar:** controlo mis límites, privacidad y disponibilidad.

Dentro de Mi red incorporar una nueva sección esencial:

## APRENDEMOS JUNTOS

Será un banco inteligente de experiencias docentes, valoraciones y mejoras documentadas.

Este submódulo debe estar conectado directamente con:

- Mi aprendizaje.
- Mi aula.
- Mi portafolio.
- Mi red.
- El Laboratorio de ideas con IA.

No crear aplicaciones separadas para estas funciones.

Utilizar entidades compartidas, identificadores estables y una arquitectura común.

---

# 4. PANTALLA INICIAL — COPILOTO CON PREGUNTAS ROMPEHIELO

Esta funcionalidad es prioritaria.

El usuario no debe encontrarse con un cuadro vacío y tener que inventar un prompt.

## Primera experiencia

Mostrar:

**"¡Hola, profe! ¿Qué te gustaría hacer hoy?"**

Debajo:

"Si no sabes por dónde comenzar, puedo ayudarte a encontrar una idea para tu próxima clase."

Mostrar entre tres y cinco sugerencias accionables.

Ejemplos:

- "Tengo un tema, pero no sé cómo enseñarlo."
- "Quiero una dinámica divertida."
- "Tengo poco tiempo para preparar mi clase."
- "Necesito adaptar una actividad porque me faltan materiales."
- "Quiero conocer ideas de otros docentes."
- "Quiero mejorar una clase que ya preparé."
- "Quiero compartir cómo me fue en una actividad."
- "No sé por dónde empezar. Hazme algunas preguntas."

Cada opción debe ejecutar una acción real.

## Conversación guiada

Ejemplo:

DOCENTE:

"No sé por dónde empezar."

AULALISTA:

"Podemos preparar una clase nueva, mejorar una actividad que ya tienes o buscar ideas de otros profesores. ¿Cuál prefieres?"

DOCENTE:

"Quiero preparar una clase."

AULALISTA:

"¿Qué tema necesitas enseñar?"

DOCENTE:

"Fracciones."

AULALISTA:

"¿Para qué grado o grupo?"

DOCENTE:

"Quinto de primaria."

AULALISTA:

"¿Cuánto tiempo tienes?"

DOCENTE:

"45 minutos."

AULALISTA:

"¿Con qué materiales cuentas?"

DOCENTE:

"Pizarra, papel y lápices."

AULALISTA:

"Perfecto. Puedo buscar actividades sobre fracciones que funcionen con esos materiales. También puedo incorporar ideas compartidas por otros docentes."

Mostrar opciones:

- Crear clase.
- Ver ideas relacionadas.
- Combinar ideas.

## Motor inteligente de preguntas

Implementar un componente `ConversationStarter`.

Debe considerar:

- Perfil del docente.
- Historial de conversación.
- Contexto del aula.
- Recursos recientes.
- Borradores pendientes.
- Sesiones guardadas.
- Actividades consultadas.
- Experiencias compartidas.

Si existen datos suficientes, sugerir acciones contextuales.

Ejemplo:

"¿Quieres continuar la clase de comprensión lectora que dejaste pendiente?"

No inventar recursos, tareas o sesiones.

## Interpretación contextual

Si el usuario dice:

"Necesito una actividad divertida para enseñar multiplicación a 32 alumnos, tengo media hora y no hay internet."

Extraer:

- Intención: generar actividad.
- Tema: multiplicación.
- Participantes: 32.
- Duración: 30 minutos.
- Internet: no disponible.
- Preferencia: dinámica.

No volver a preguntar por datos ya proporcionados.

Hacer una pregunta breve cuando falte información indispensable.

Permitir respuestas libres, botones sugeridos y dictado por voz.

El sistema debe mantener un estado conversacional persistente.

---

# 5. INTERACCIÓN POR VOZ — AMAZON TRANSCRIBE

Los docentes deben poder interactuar naturalmente sin escribir instrucciones extensas.

Utilizar Amazon Transcribe para reconocimiento de voz.

## Casos de uso

Permitir dictar:

- Solicitudes de planificación.
- Respuestas a preguntas rompehielo.
- Cambios sobre una sesión.
- Búsquedas de actividades.
- Reflexiones posteriores a una clase.
- Comentarios.
- Sugerencias.
- Experiencias para compartir.

Ejemplo:

"Hoy utilicé la dinámica de tarjetas para enseñar fracciones. Los estudiantes participaron bastante, pero perdimos tiempo explicando las reglas. La próxima vez las dividiría en tres pasos."

La plataforma debe convertir la transcripción en un borrador estructurado de experiencia:

**Qué hice:** dinámica de tarjetas.

**Qué observé:** participación del grupo y dificultades al explicar las reglas.

**Qué cambiaría:** dividir las instrucciones en tres pasos.

La IA debe conservar el sentido del relato, sin inventar resultados.

El docente revisa antes de guardar o compartir.

## Implementación AWS

- Captura mediante MediaRecorder.
- Almacenamiento temporal privado en S3.
- Procesamiento mediante Amazon Transcribe.
- Recuperación de transcripción.
- Presentación editable en frontend.
- Confirmación humana.

Comprobar los formatos de audio y códigos de idioma admitidos por el servicio en la región seleccionada.

Para el MVP es suficiente la transcripción por lotes.

No afirmar que se implementó streaming si solamente se dispone de transcripción después de grabar.

Mostrar:

- Escuchando.
- Procesando audio.
- Transcripción lista.
- Error de transcripción.
- Reintentar.

Mantener entrada por texto como alternativa.

No ejecutar publicaciones automáticamente a partir de una transcripción.

---

# 6. MI APRENDIZAJE — BIBLIOTECA PEDAGÓGICA

Permitir consultar recursos educativos y módulos de capacitación.

Cada recurso debe conservar:

- Identificador.
- Título.
- Contenido.
- Procedencia.
- Autor.
- Versión.
- Nivel.
- Tema.
- Fragmentos identificables.
- Materiales.
- Permisos de uso.

Crear un catálogo inicial con un módulo detallado de escucha activa y recursos adicionales sobre:

- Comprensión lectora.
- Matemática.
- Ciencia.
- Comunicación.
- Habilidades socioemocionales.
- Aprendizaje colaborativo.
- Educación ambiental.
- Pensamiento crítico.
- Actividades prácticas.

Cada recurso debe incluir información suficiente para utilizarse en una clase.

Implementar el botón:

**"Usar en mi clase".**

Debe trasladar el recurso seleccionado a Mi aula conservando su identificador y versión.

## Recorrido privado de aprendizaje profesional

Incorporar un historial privado denominado:

**"Mi recorrido de aprendizaje".**

Estructura:

1. Qué quiero mejorar.
2. Qué experiencia o recurso consulté.
3. Qué cambié en mi práctica.
4. Qué observé.
5. Qué probaré después.

Ejemplo:

**Objetivo:** mejorar instrucciones de actividades grupales.

**Experiencia consultada:** dinámica compartida por otro docente.

**Cambio realizado:** dividir las instrucciones en tres pasos.

**Observación:** el docente describe qué ocurrió.

**Siguiente acción:** volver a probar con otro grupo.

No completar automáticamente observaciones que todavía no existen.

El sistema podrá sugerir el siguiente paso, pero el docente decide registrarlo.

Este historial es privado por defecto.

---

# 7. MI AULA — GENERACIÓN PEDAGÓGICA CON BEDROCK

Esta es la principal herramienta de creación.

El docente puede generar:

- Sesiones de aprendizaje.
- Actividades.
- Juegos.
- Dinámicas.
- Evaluaciones formativas.
- Ejercicios.
- Proyectos.
- Materiales de apoyo.
- Adaptaciones de clases.
- Combinaciones de estrategias.

## Contexto de aula

Recoger de manera progresiva:

- Nivel.
- Grado.
- Tema.
- Propósito.
- Duración.
- Número de estudiantes.
- Materiales.
- Conectividad.
- Tecnología disponible.
- Idioma.
- Condiciones particulares.
- Preferencias metodológicas.

No exigir todos los datos para iniciar.

Reutilizar contextos existentes.

## Generación

Amazon Bedrock utilizará:

1. Solicitud del docente.
2. Contexto.
3. Recursos pedagógicos relevantes.
4. Experiencias comunitarias autorizadas.
5. Restricciones declaradas.
6. Ideas seleccionadas.

Generar una sesión estructurada con:

- Título.
- Objetivo.
- Nivel y grado.
- Duración.
- Materiales.
- Actividades.
- Instrucciones.
- Tiempos.
- Organización.
- Evidencia esperada.
- Evaluación formativa.
- Referencias.
- Explicación de las adaptaciones.

## Factibilidad

Implementar validaciones programáticas:

- Suma correcta de minutos.
- Restricciones de materiales.
- Conectividad.
- Recursos citados existentes.
- Actividades adecuadas al nivel.
- Referencias a versiones correctas.
- Permisos para incorporar ideas comunitarias.

No depender exclusivamente de una respuesta generada por IA.

## Edición

Permitir modificar manualmente.

Permitir cambios conversacionales como:

"Haz la segunda actividad más participativa."

"Reduce el tiempo a 30 minutos."

"Quiero una versión sin materiales impresos."

"Combínala con una dinámica de la comunidad."

El resultado de una modificación debe quedar como nuevo borrador o revisión, sin destruir silenciosamente la versión anterior.

---

# 8. MI PORTAFOLIO — HISTORIAL Y VERSIONES

Crear un repositorio personal persistente.

Permitir:

- Guardar una sesión.
- Recuperarla.
- Editarla.
- Duplicarla.
- Crear versiones.
- Comparar versiones.
- Adaptarla.
- Imprimirla.
- Exportarla.
- Registrar su aplicación.
- Compartir una copia autorizada.

## Estados

Distinguir:

- Borrador generado por IA.
- Revisado por docente.
- Sesión con registro de aplicación.

No considerar que una planificación fue aplicada solamente porque se guardó.

## Registro de aplicación

Permitir registrar voluntariamente:

- Fecha declarada.
- Actividad utilizada.
- Condiciones reales.
- Materiales utilizados.
- Qué ocurrió.
- Qué funcionó según el docente.
- Qué resultó difícil.
- Qué quedó incierto.
- Qué cambiaría.

La IA puede ayudar a estructurar una reflexión dictada, pero debe preservar el relato original.

No inferir aprendizajes de estudiantes sin evidencias.

Los datos simulados deben estar identificados como ejemplos.

## Versionado

Cada versión debe tener:

- ID propio.
- Número de versión.
- Autor.
- Fecha.
- Contenido.
- Motivo del cambio.
- Identificador de la versión anterior.
- Recursos utilizados.
- Estado de revisión.

Una versión publicada debe permanecer identificable incluso si el autor crea una adaptación posterior.

---

# 9. MI RED — COMUNIDAD SOCIAL DOCENTE

Crear una comunidad donde los docentes puedan compartir:

- Recursos.
- Planificaciones.
- Dinámicas.
- Experiencias aplicadas.
- Solicitudes de colaboración.
- Recomendaciones.
- Adaptaciones.

## Feed

Cada tarjeta debe mostrar:

- Autor.
- Título.
- Nivel.
- Tema.
- Duración.
- Materiales.
- Contexto.
- Tipo de publicación.
- Resumen.
- Fecha.
- Permisos.
- Acciones.

Acciones:

- Abrir.
- Guardar.
- Comentar.
- Adaptar con IA.
- Combinar con otra idea.
- Consultar experiencias.
- Consultar valoraciones.

El MVP debe priorizar abrir, guardar, adaptar y combinar.

## Permisos

Cada publicación tendrá una política clara:

- Privada.
- Pública de solo lectura.
- Reutilizable con atribución.
- Adaptable y combinable con atribución.

La copia compartida debe excluir observaciones privadas no seleccionadas por el autor.

## Solicitudes

Permitir publicaciones como:

"Busco una actividad de escucha activa para primaria que necesite solamente papel."

La IA puede recomendar recursos relacionados y ayudar a redactar la solicitud.

El usuario debe aprobarla antes de publicar.

---

# 10. NUEVO SUBMÓDULO: APRENDEMOS JUNTOS

## Objetivo

Convertir las experiencias docentes en conocimiento consultable, contextualizado, versionado y reutilizable.

Este submódulo NO debe limitarse a una lista de comentarios o estrellas.

Debe permitir comprender:

- Qué se intentó enseñar.
- En qué condiciones.
- Qué hizo el docente.
- Qué observó.
- Qué dificultades encontró.
- Qué cambiaría.
- Qué sugerencias recibió.
- Qué versión preparó después.

La plataforma debe reconocer que una experiencia que no salió como se esperaba también puede aportar conocimiento.

## 10.1 Banco de experiencias

Cada experiencia compartida tendrá una ficha estructurada.

### A. Propósito

¿Qué quería trabajar?

Ejemplo:

"Mejorar la escucha activa mediante actividades por parejas."

### B. Contexto

- Nivel.
- Grado.
- Número de estudiantes, si se comparte.
- Duración.
- Materiales.
- Conectividad.
- Condiciones relevantes.

### C. Aplicación

¿Qué hizo?

Registrar pasos y adaptaciones.

### D. Observaciones

¿Qué ocurrió según el docente?

Separar:

- Qué funcionó.
- Qué resultó difícil.
- Qué quedó incierto.

### E. Mejora propuesta

¿Qué cambiaría para la próxima aplicación?

Registrar una acción concreta.

### F. Procedencia

Mostrar:

- Autor.
- Versión.
- Actividad original.
- Recursos utilizados.
- Permisos.
- Relación con versiones anteriores.

## 10.2 Ejemplo de experiencia

Un docente comparte:

**Actividad:** trabajo en parejas para desarrollar escucha activa.

**Contexto:** cuarto de primaria, 45 minutos, papel y pizarra.

**Observación:**

"Las instrucciones iniciales fueron demasiado largas. Tuve que repetirlas varias veces."

**Dificultad:**

"Algunos grupos comenzaron antes de comprender la dinámica."

**Qué cambiaría:**

"Dividir las instrucciones en tres pasos y mostrar un ejemplo antes de comenzar."

Otro docente puede responder:

"Yo probaría mostrar primero una demostración breve con dos voluntarios."

La plataforma debe permitir seleccionar esta sugerencia y crear una nueva versión con Bedrock.

La experiencia anterior no se elimina.

La nueva versión conserva su relación con la original.

Posteriormente, si alguien aplica la nueva versión, podrá registrar lo observado.

## 10.3 Pantalla de experiencia

Mostrar:

- Resumen.
- Contexto.
- Materiales.
- Pasos.
- Observaciones.
- Mejoras propuestas.
- Valoración de uso.
- Comentarios.
- Sugerencias.
- Historial de versiones.
- Fuentes.
- Botón "Adaptar con IA".
- Botón "Proponer una mejora".
- Botón "Guardar en mi portafolio".

No mostrar datos personales de estudiantes.

---

# 11. VALORACIÓN DE USO — SISTEMA DE PUNTUACIÓN

Implementar un sistema de valoraciones por versión concreta.

La valoración debe describir la experiencia declarada de uso, no probar automáticamente resultados educativos.

## 11.1 Quién puede valorar

La interfaz debe pedir al usuario que confirme:

**"He utilizado esta actividad y quiero compartir mi valoración".**

El sistema puede exigir un registro de aplicación asociado.

Esto representa una declaración del docente, no una verificación independiente.

Los usuarios que únicamente leyeron la actividad pueden comentar, guardarla o sugerir ideas, pero sus comentarios no deben contarse como valoraciones de uso.

No calcular puntuaciones a partir de likes o visualizaciones.

## 11.2 Cuatro criterios

Utilizar una escala de 1 a 5 para cada criterio:

### Claridad

**¿Se entendían las instrucciones?**

### Viabilidad

**¿Pude realizarla con el tiempo y materiales indicados?**

### Coherencia

**¿La actividad permitió trabajar el propósito planteado?**

### Observación del aprendizaje

**¿Me ayudó a observar qué estaba comprendiendo el grupo?**

Cada criterio debe permitir:

- 1.
- 2.
- 3.
- 4.
- 5.
- No puedo valorarlo.

No forzar al docente a inventar una puntuación cuando no puede juzgar el criterio.

## 11.3 Reflexión asociada

Cada valoración debe permitir registrar:

**¿Qué mantendrías?**

**¿Qué cambiarías?**

Guardar estos comentarios con el contexto de uso.

Las valoraciones deben conservar:

- Autor.
- Versión exacta.
- Contexto declarado.
- Fecha.
- Criterios.
- Comentarios.
- Fecha de actualización.

## 11.4 Cálculo de puntuación

Para una valoración completa, los cuatro criterios deben contener valores numéricos válidos.

Calcular:

`score = (claridad + viabilidad + coherencia + observacion) / 4`

La puntuación global de la versión será la media aritmética de las valoraciones completas de usuarios distintos.

Utilizar todos los criterios con el mismo peso en el MVP.

No inventar ponderaciones supuestamente científicas.

Si algún criterio contiene "No puedo valorarlo", conservar la respuesta como valoración parcial, pero no incluirla en la media global de valoraciones completas.

Mostrar las valoraciones parciales por separado cuando sea útil.

## 11.5 Presentación

Ejemplo ficticio:

**4,4/5**

**3 valoraciones completas**

**Pocas valoraciones**

Contexto:

"Cuarto de primaria · Papel y pizarra"

Resumen:

"Sugerencia recurrente: simplificar las instrucciones iniciales."

Una sugerencia solo puede etiquetarse como recurrente si hay al menos dos aportes independientes que la respalden.

No inventar recurrencias a partir de una sola opinión.

### Reglas visuales

- Sin datos: mostrar "Sin valoraciones".
- Mostrar siempre el número de valoraciones completas.
- Si hay menos de 5, mostrar "Pocas valoraciones".
- Nunca mostrar un promedio sin informar cuántas observaciones lo sustentan.
- La popularidad no debe interpretarse automáticamente como eficacia pedagógica.
- Permitir consultar los comentarios y sus contextos.
- No combinar valoraciones de versiones diferentes.
- No mezclar opiniones de lectores con valoraciones de uso.

## 11.6 Edición y duplicados

Cada usuario podrá tener una valoración activa por versión.

Puede corregirla.

La modificación debe actualizar la valoración existente, no crear otro voto.

Implementar unicidad utilizando:

`versionId + reviewerId`

Validar esta regla en el backend.

No confiar únicamente en el frontend.

Si se mantiene un agregado de puntuaciones, actualizarlo de forma consistente para evitar duplicaciones.

Para el MVP, si el volumen es pequeño, es aceptable calcular el agregado de forma determinista al consultar las valoraciones de una versión.

## 11.7 Nuevas versiones

Una nueva versión comienza sin valoraciones propias.

No heredar automáticamente la puntuación de una versión anterior.

Mostrar:

**Versión 1: 4,2/5 — 5 valoraciones completas.**

**Versión 2: Sin valoraciones.**

La interfaz puede vincular ambas versiones para compararlas, indicando sus contextos.

No afirmar que la segunda es mejor hasta contar con observaciones pertinentes.

---

# 12. COMENTARIOS, SUGERENCIAS Y MEJORAS

Permitir dos clases de participación.

## Comentario general

Disponible para quienes consultan una publicación.

Puede contener preguntas, opiniones o sugerencias.

No implica que hayan utilizado la actividad.

## Sugerencia de mejora

Debe describir un cambio concreto.

Ejemplo:

"Reducir las instrucciones a tres pasos."

Guardar:

- Autor.
- Recurso.
- Versión.
- Descripción.
- Motivo.
- Fecha.
- Estado.

Estados posibles:

- Propuesta.
- Incorporada a una nueva versión.
- Descartada por el responsable de la adaptación.

Una sugerencia no debe modificar automáticamente la actividad original.

El docente puede seleccionar sugerencias y pedir a Bedrock:

"Aplica estas recomendaciones a mi sesión."

El resultado debe mostrarse como nuevo borrador.

## Comparación de versiones

Implementar una comparación sencilla:

**Versión anterior:**

"Instrucciones orales de diez minutos."

**Nueva propuesta:**

"Explicación en tres pasos con demostración inicial."

**Motivo del cambio:**

"Reducir la dificultad observada al comprender instrucciones."

Mostrar qué se mantuvo y qué cambió.

La IA debe generar la explicación basándose en los cambios reales.

---

# 13. LABORATORIO DE IDEAS — COMBINAR EXPERIENCIAS CON IA

Permitir seleccionar varias fuentes:

- Recursos pedagógicos.
- Planificaciones autorizadas.
- Experiencias de docentes.
- Sugerencias.
- Versiones anteriores.

Amazon Bedrock debe generar una propuesta coherente combinando los elementos seleccionados.

## Ejemplo

Un docente encuentra:

**Idea A:** juego de fracciones con papel.

**Idea B:** actividad grupal colaborativa.

**Idea C:** experiencia aplicada donde otro docente recomienda simplificar instrucciones.

El usuario solicita:

"Combina estas ideas para una clase de quinto de primaria de 45 minutos, sin proyector, con 35 estudiantes."

El sistema debe:

1. Recuperar fuentes autorizadas.
2. Identificar objetivos.
3. Analizar actividades.
4. Reconocer restricciones.
5. Incorporar sugerencias relevantes.
6. Adaptar tiempos.
7. Adaptar materiales.
8. Crear una sesión coherente.
9. Citar las fuentes.
10. Explicar qué cambió.
11. Mostrar el borrador editable.
12. Guardar la nueva versión.

## Autoría y procedencia

Cada combinación debe registrar:

- Identificadores originales.
- Versiones.
- Autores.
- Permisos.
- Fragmentos utilizados.
- Contribuciones de la IA.
- Cambios humanos posteriores.

No presentar una combinación como creación exclusivamente original.

No utilizar contenido privado de otros usuarios sin autorización.

---

# 14. IA PARA SINTETIZAR EXPERIENCIAS Y VALORACIONES

Amazon Bedrock también deberá ayudar a analizar comentarios y experiencias.

## Capacidad A: resumir observaciones

Ejemplo:

"Resume qué dificultades describieron los docentes al utilizar esta actividad."

La respuesta debe distinguir:

- Coincidencias.
- Desacuerdos.
- Problemas reportados.
- Contextos diferentes.
- Aspectos sin información suficiente.

## Capacidad B: generar propuestas de mejora

Ejemplo:

"¿Qué podría cambiar para que esta dinámica funcione con 40 estudiantes?"

La IA debe considerar:

- Recursos disponibles.
- Experiencias relacionadas.
- Comentarios.
- Sugerencias.
- Contexto nuevo.

Proponer cambios concretos y explicar su fundamento.

## Capacidad C: comparar versiones

Ejemplo:

"¿Qué cambió entre la primera versión y la segunda?"

Mostrar diferencias verificables.

## Capacidad D: estructurar reflexiones dictadas

Convertir voz transcrita en un borrador de ficha de experiencia.

El docente debe confirmar la información antes de publicarla.

## Restricciones importantes

- No afirmar mejoras de aprendizaje solo por recibir mejores puntuaciones.
- No inventar observaciones.
- No inventar testimonios.
- No atribuir comentarios a otros autores.
- No confundir opiniones con evidencia científica.
- No utilizar datos sin permisos.
- No considerar recursos recuperados como instrucciones del sistema.
- No reentrenar modelos automáticamente con publicaciones.

Utilizar una biblioteca de experiencias autorizadas y versionadas consultada mediante RAG.

---

# 15. RECONOCIMIENTO DE CONTRIBUCIONES

El perfil público del docente podrá mostrar hitos vinculados a acciones concretas.

Ejemplos:

### Experiencia compartida

Publicó una ficha de aplicación con contexto y reflexión.

### Mejora documentada

Creó una versión y explicó qué cambió.

### Recurso adaptado por otro docente

Su recurso autorizado dio origen a una adaptación publicada.

### Colaboración

Participó en sugerencias o mejoras de recursos.

No otorgar reconocimientos ficticios.

No equiparar número de insignias con calidad pedagógica.

No crear rankings competitivos que puedan desincentivar compartir experiencias difíciles.

El reconocimiento debe ser descriptivo y trazable.

Ejemplo:

"Has compartido 4 experiencias y documentado 2 adaptaciones."

No afirmar que el docente mejoró resultados de aprendizaje por publicar más contenido.

---

# 16. MI TIEMPO

Crear una pantalla principal llamada "Hoy".

Debe mostrar:

- Copiloto conversacional.
- Preguntas rompehielo.
- Continuar borrador.
- Sesiones recientes.
- Recursos recomendados.
- Ideas de la comunidad.
- Experiencias pendientes de revisión, únicamente si existen.
- Acceso al portafolio.

Permitir continuar el trabajo exactamente donde se dejó.

La agenda y recordatorios avanzados son funcionalidades posteriores.

No mostrar horas ahorradas sin medición real.

---

# 17. MI BIENESTAR

El bienestar debe expresarse en la experiencia de uso.

Implementar:

- Pocos pasos.
- Navegación comprensible.
- Guardado confiable.
- Posibilidad de interrumpir y continuar.
- Control de privacidad.
- Publicación voluntaria.
- Confirmación antes de acciones importantes.
- Ausencia de notificaciones intrusivas.

Evolución futura:

- Horarios preferidos.
- Silenciar avisos.
- Disponibilidad profesional.
- Recursos públicos de apoyo.

No recopilar información personal sensible innecesaria.

No implementar diagnósticos de salud mental.

---

# 18. MIS OPORTUNIDADES

Preparar una sección para la evolución profesional del docente.

Categorías:

- Recursos educativos originales.
- Mentorías.
- Talleres.
- Acompañamiento pedagógico.

Cada oferta futura podría incluir:

- Autor.
- Descripción.
- Destinatarios.
- Modalidad.
- Duración.
- Disponibilidad.
- Precio.
- Condiciones.

La IA podrá ayudar a redactar ofertas y encontrar coincidencias.

No implementar pagos ni prometer ingresos en el MVP.

La publicación de una oferta no implica una transacción.

---

# 19. ARQUITECTURA TÉCNICA AWS

## Frontend

- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- AWS Amplify Hosting.

## Infraestructura y backend

- AWS Amplify Gen 2.
- Amazon Cognito.
- AWS AppSync.
- Amazon DynamoDB.
- AWS Lambda.
- Amazon S3.

## Inteligencia artificial

- Amazon Bedrock.
- AWS SDK for JavaScript v3.
- Converse API, con un modelo compatible y autorizado.

## Audio

- Amazon Transcribe.

## Monitoreo

- Amazon CloudWatch.

## Evolución RAG

- Amazon Bedrock Knowledge Bases.
- Amazon S3.
- Almacenamiento vectorial compatible, si está disponible.

## Principio de simplicidad

Para el MVP, implementar búsqueda textual y filtrado por metadatos.

No desplegar infraestructura vectorial compleja si impide terminar el producto.

Definir una interfaz desacoplada de recuperación para cambiar posteriormente el motor de búsqueda.

## Seguridad

- Autenticación mediante Cognito.
- Autorización por recurso.
- Buckets S3 privados.
- Acceso temporal mediante URLs prefirmadas cuando corresponda.
- Cifrado según configuración del servicio.
- IAM con permisos mínimos.
- Validación de entradas mediante Zod.
- Límites de tamaño de archivos.
- Control de llamadas a Bedrock.
- Logs de errores sin datos sensibles.
- Protección contra prompt injection desde documentos y publicaciones.

Utilizar Amazon Bedrock Guardrails cuando esté disponible y configurado.

No reemplazar controles de autorización por filtros de lenguaje.

Verificar los servicios autorizados en la cuenta AWS antes de desplegar.

Si el entorno es AWS Academy Learner Lab, revisar las restricciones IAM y de servicios antes de elegir la implementación definitiva.

---

# 20. MODELO DE DATOS AWS

Definir modelos compatibles con Amplify Data y DynamoDB.

## TeacherProfile

- id
- ownerId
- displayName
- bio
- specialties
- educationalLevels
- country
- region
- avatarKey
- createdAt

## ClassroomContext

- id
- ownerId
- level
- grade
- studentCount
- durationPreferences
- materials
- internetAvailable
- projectorAvailable
- additionalConditions

## LearningResource

- id
- title
- authorId
- source
- version
- topic
- contentKey
- metadata
- visibility
- reusePermission

## ResourceFragment

- id
- resourceId
- resourceVersion
- sectionLabel
- content

## ConversationSession

- id
- ownerId
- intent
- state
- contextData
- selectedResources
- selectedPosts
- updatedAt

## LessonPlan

- id
- ownerId
- title
- classroomContextId
- currentVersionId
- status
- createdAt
- updatedAt

## LessonVersion

- id
- lessonId
- versionNumber
- parentVersionId
- content
- sourceReferences
- changes
- reviewStatus
- createdAt

## ApplicationRecord

- id
- lessonVersionId
- authorId
- declaredDate
- context
- activityPerformed
- observations
- difficulties
- uncertainties
- nextImprovement
- isDemo
- createdAt

## CommunityPost

- id
- authorId
- sourceVersionId
- postType
- title
- content
- context
- visibility
- reusePermission
- moderationStatus
- createdAt

## ExperienceRating

- id
- resourceVersionId
- reviewerId
- applicationRecordId
- clarity
- feasibility
- coherence
- learningObservation
- whatToKeep
- whatToChange
- completed
- createdAt
- updatedAt

Definir unicidad lógica por `resourceVersionId + reviewerId`.

## ImprovementSuggestion

- id
- resourceVersionId
- authorId
- content
- explanation
- status
- createdAt

## CommunityComment

- id
- postId
- authorId
- content
- commentType
- createdAt

## RemixRecord

- id
- ownerId
- sourceVersionIds
- sourceResourceIds
- resultingVersionId
- changeExplanation
- attribution
- createdAt

## LearningJourneyEntry

- id
- ownerId
- improvementGoal
- consultedExperienceIds
- changesApplied
- observations
- nextAction
- createdAt

## ContributionEvent

- id
- teacherId
- eventType
- resourceId
- versionId
- createdAt

## Opportunity

- id
- ownerId
- title
- category
- description
- duration
- modality
- price
- status

## TeacherPreferences

- id
- ownerId
- onboardingCompleted
- notificationPreferences
- privacyPreferences

### Reglas de modelado

1. Las versiones publicadas deben ser identificables e inmutables.
2. Una nueva edición crea otra versión.
3. Las valoraciones pertenecen a una versión específica.
4. No mezclar valoraciones de distintas versiones.
5. Evitar duplicados por usuario.
6. Conservar procedencia de remixes.
7. No permitir que otro usuario edite recursos privados.
8. Mantener separado contenido privado y público.
9. No permitir publicaciones automáticas.
10. Implementar patrones de acceso e índices adecuados para evitar escaneos completos de DynamoDB.

---

# 21. RAG — CONOCIMIENTO COLECTIVO AUTORIZADO

Implementar una capa de recuperación que pueda consultar:

- Módulos de aprendizaje.
- Recursos educativos.
- Publicaciones públicas.
- Experiencias autorizadas.
- Sugerencias.
- Versiones.
- Recursos propios del docente.

## Flujo

1. Interpretar solicitud.
2. Identificar contexto.
3. Determinar permisos.
4. Buscar recursos.
5. Buscar experiencias relevantes.
6. Ordenar por compatibilidad.
7. Recuperar fragmentos.
8. Enviar contexto a Bedrock.
9. Generar propuesta.
10. Validar referencias.
11. Mostrar fuentes.

Las valoraciones pueden utilizarse como señal secundaria de recomendación.

No clasificar una actividad como pedagógicamente superior solamente por su promedio.

Priorizar:

- Relevancia del tema.
- Compatibilidad del nivel.
- Materiales.
- Tiempo.
- Restricciones.
- Objetivos.

Cuando una recomendación esté apoyada en experiencias, mostrar el contexto correspondiente.

No afirmar que un recurso ha sido ampliamente probado si solamente cuenta con unas pocas valoraciones.

---

# 22. INTERFAZ UX/UI

Diseñar una aplicación profesional, accesible y visualmente consistente.

No crear un dashboard administrativo genérico.

## Navegación

- Hoy.
- Mi aprendizaje.
- Mi aula.
- Mi portafolio.
- Mi red.
- Mis oportunidades.
- Mi bienestar.

Dentro de Mi red destacar:

**Aprendemos juntos.**

Desde Mi aula permitir acceder al Laboratorio de ideas.

## Pantalla Hoy

El protagonista visual debe ser el copiloto.

Elementos:

- Saludo.
- Preguntas rompehielo.
- Entrada por texto.
- Botón de micrófono.
- Sesiones recientes.
- Ideas relevantes.

## Mi red

Feed con tarjetas.

Cada tarjeta mostrará:

- Autor.
- Tipo de publicación.
- Nivel y tema.
- Materiales.
- Duración.
- Descripción.
- Valoración, si existe.
- Número de valoraciones.
- Botón adaptar.
- Botón combinar.

## Aprendemos juntos

Crear una página de detalle con pestañas o secciones:

- Actividad.
- Contexto.
- Experiencias.
- Valoraciones.
- Sugerencias.
- Versiones.

Mostrar claramente las experiencias aplicadas y las planificaciones no aplicadas.

## Editor

Crear tarjetas editables por actividad.

Mostrar:

- Tiempo.
- Instrucciones.
- Materiales.
- Evidencia esperada.
- Referencias.
- Cambios sugeridos.

## Diseño

- Responsive.
- Tipografía legible.
- Estados de carga.
- Mensajes de error.
- Acciones de confirmación.
- Navegación sencilla.
- Accesibilidad de teclado.
- Contraste suficiente.
- Vista de impresión.

No crear controles que aparenten funcionar sin tener una acción implementada.

---

# 23. DATOS DE DEMOSTRACIÓN

Preparar datos ficticios claramente identificados.

Crear:

- 3 perfiles docentes de prueba.
- 1 módulo detallado de escucha activa.
- 8 recursos pedagógicos adicionales.
- 6 publicaciones de comunidad.
- 3 experiencias de aplicación simuladas.
- 3 valoraciones de uso simuladas para una misma versión.
- 2 sugerencias sobre esa experiencia.
- 2 versiones relacionadas de una actividad.
- 2 clases en portafolio.
- 1 recorrido privado de aprendizaje.
- 1 combinación de ideas que pueda generarse con Bedrock.

## Ejemplo central

**Actividad:** escucha activa por parejas.

**Versión 1:**

Instrucciones extensas.

**Experiencia simulada:**

El docente declara dificultades para explicar las reglas.

**Valoraciones:**

Tres valoraciones completas, con comentarios contextualizados.

**Sugerencia:**

Dividir instrucciones en tres pasos.

**Versión 2:**

Adaptación con instrucciones simplificadas y demostración inicial.

**Estado de la versión 2:**

Sin valoraciones.

De esta manera se demostrará cómo una experiencia contribuye a una nueva versión, sin afirmar que la nueva versión ya funciona mejor.

No calcular o mostrar cifras que no correspondan a los registros cargados.

---

# 24. DEMOSTRACIÓN OBLIGATORIA

## DEMO 1 — EL DOCENTE NO SABE QUÉ PEDIR

1. Abre AulaLista.
2. Ve preguntas rompehielo.
3. Selecciona "No sé por dónde empezar".
4. El copiloto pregunta qué desea preparar.
5. Expresa su necesidad.
6. Se confirma el contexto.
7. Bedrock genera una sesión.
8. Edita.
9. Guarda.

## DEMO 2 — EL DOCENTE INTERACTÚA POR VOZ

1. Presiona el micrófono.
2. Describe lo que necesita.
3. Amazon Transcribe procesa el audio.
4. Corrige la transcripción.
5. Bedrock adapta recursos.
6. Genera una actividad.
7. La guarda.

## DEMO 3 — DESCUBRIMIENTO SOCIAL

1. Abre Mi red.
2. Encuentra una dinámica.
3. Consulta materiales y contexto.
4. Revisa experiencias aplicadas.
5. Consulta valoraciones.
6. Lee una sugerencia.
7. Selecciona "Adaptar con IA".

## DEMO 4 — APRENDEMOS JUNTOS

1. Abrir una experiencia simulada.
2. Mostrar propósito, materiales y contexto.
3. Mostrar observaciones.
4. Mostrar media y número de valoraciones.
5. Abrir comentarios.
6. Identificar una sugerencia concreta.
7. Pedir a Bedrock que incorpore la mejora.
8. Generar una nueva versión.
9. Comparar ambas.
10. Guardar.
11. Mostrar que la nueva versión comienza sin valoraciones.

**Este recorrido es obligatorio porque demuestra el nuevo valor de aprendizaje colectivo.**

## DEMO 5 — COMBINAR IDEAS

1. Seleccionar una dinámica de un docente.
2. Seleccionar otra actividad.
3. Abrir Laboratorio de ideas.
4. Describir restricciones.
5. Bedrock combina estrategias.
6. Mostrar atribución.
7. Revisar.
8. Guardar.

## DEMO 6 — CERRAR EL CICLO

1. Recuperar una clase del portafolio.
2. Añadir un registro de aplicación simulado.
3. Escribir o dictar una reflexión.
4. Revisar la ficha.
5. Compartir una versión autorizada.
6. Mostrarla en Mi red.
7. Verificar que otros usuarios puedan consultarla según permisos.

---

# 25. PRIORIZACIÓN PARA CUATRO HORAS

El alcance es amplio, por lo que debes construir una demostración vertical, no siete módulos incompletos.

## P0 — NÚCLEO OBLIGATORIO

- Frontend ejecutable.
- Infraestructura AWS mínima.
- Datos persistentes.
- Preguntas rompehielo.
- Conversación guiada.
- Un recurso pedagógico con referencias.
- Generación Bedrock.
- Edición y guardado.
- Recuperación desde portafolio.
- Feed social mínimo.
- Ficha de experiencia.
- Valoración de uso por versión.
- Cálculo de puntuación.
- Sugerencia de mejora.
- Adaptación con Bedrock.
- Guardado de nueva versión.
- Atribución de fuentes.

## P1 — PRIORIDAD ALTA

- Amazon Transcribe.
- Publicación desde portafolio.
- Laboratorio de combinación de dos recursos.
- Registro dictado de experiencias.
- Comparación visual de versiones.
- Impresión.
- Recorrido privado de aprendizaje.

## P2 — EVOLUCIÓN

- Comentarios avanzados.
- Seguimiento de usuarios.
- Notificaciones.
- Reconocimientos visuales.
- Agenda.
- Búsqueda semántica avanzada.
- Analítica y recomendaciones personalizadas.

## P3 — FUTURO

- Marketplace.
- Mentorías.
- Talleres.
- Reservas.
- Pagos.
- Integraciones educativas externas.

### Regla de prioridad

Si el tiempo se reduce, no elimines el ciclo:

**Generar → guardar → registrar experiencia → valorar → sugerir → adaptar → versionar.**

Ese ciclo debe funcionar con al menos un recurso y una experiencia de demostración.

La voz es importante y debe implementarse cuando los servicios AWS estén habilitados, pero no debe destruirse un flujo funcional por intentar resolver una incompatibilidad de audio a última hora.

---

# 26. PRUEBAS OBLIGATORIAS

Implementar pruebas sobre:

## Copiloto

- Extrae contexto correctamente.
- No repite preguntas innecesarias.
- Mantiene estado conversacional.
- Los rompehielos ejecutan acciones.

## Generación

- Bedrock devuelve contenido válido.
- La suma de minutos es correcta.
- Los materiales son compatibles.
- Las referencias existen.

## Portafolio

- Guarda.
- Recupera.
- Versiona.
- No sobrescribe revisiones anteriores.

## Comunidad

- Respeta permisos.
- Distingue recursos de experiencias.
- Conserva autoría.
- No publica contenido privado.

## Valoraciones

- No existen puntuaciones inventadas.
- "No puedo valorarlo" no se convierte en cero.
- Las valoraciones parciales no alteran el promedio de completas.
- Un usuario no puede duplicar su voto para una versión.
- Corregir una valoración no incrementa el conteo.
- Cada versión tiene sus propios datos.
- El promedio corresponde a las puntuaciones almacenadas.
- El número de valoraciones está visible.
- Se muestra "Sin valoraciones" cuando corresponda.

## Mejoras

- La sugerencia se asocia a una versión.
- La IA no reemplaza automáticamente el original.
- La adaptación crea una nueva versión.
- Se conserva procedencia.
- La nueva versión no hereda puntuaciones.

## Seguridad

- Un usuario no puede editar datos privados de otro.
- Los endpoints validan permisos.
- Los recursos recuperados no ejecutan instrucciones maliciosas.
- No se exponen credenciales AWS.

Ejecutar las pruebas y el build.

No afirmar que una integración funciona sin haberla comprobado.

---

# 27. ENTREGABLES FINALES

Generar en el repositorio:

1. Aplicación web funcional.
2. Código frontend.
3. Configuración AWS.
4. Autenticación.
5. Base de datos.
6. Funciones Lambda.
7. Integración Amazon Bedrock.
8. Motor conversacional.
9. Preguntas rompehielo.
10. Recursos educativos.
11. Portafolio.
12. Feed docente.
13. Banco de experiencias.
14. Valoraciones por versión.
15. Sugerencias.
16. Adaptación mediante IA.
17. Versionado.
18. Reconocimiento de voz cuando esté disponible.
19. Datos de demostración.
20. `.env.example`.
21. README.
22. Instrucciones exactas de despliegue.
23. Resultado de pruebas.
24. Guion de demo para los jueces.

No incluir secretos ni credenciales en el repositorio.

Documentar claramente qué está implementado, qué necesita configuración AWS y qué corresponde a evolución futura.

---

# 28. INSTRUCCIONES FINALES PARA KIRO

**Comienza inspeccionando el repositorio y construye inmediatamente el núcleo funcional.**

No te detengas después de generar un plan o una lista de tareas.

Utiliza el estado actual del proyecto y no sobrescribas funcionalidades existentes innecesariamente.

Mantén una estructura modular.

Prioriza un recorrido demostrable sobre una implementación extensa e incompleta.

No generes respuestas estáticas fingiendo que provienen de Bedrock.

No presentes datos simulados como experiencias reales.

No inventes valoraciones.

No confundas una clase planificada con una clase aplicada.

No afirmes mejoras educativas que no hayan sido evaluadas.

No publiques contenido sin confirmación.

No pierdas la atribución cuando combines recursos.

No utilices herramientas externas de nube si AWS proporciona el servicio requerido.

Si encuentras restricciones de permisos, explica cuáles son y conserva las funcionalidades ya implementadas.

## RESULTADO ESPERADO

La demostración debe poder contar esta historia:

Una profesora entra a AulaLista sin saber qué preparar.

El copiloto le hace preguntas sencillas y comprende su necesidad.

Consulta recursos pedagógicos y experiencias de otros docentes.

Amazon Bedrock propone una sesión adaptada.

La profesora la revisa y la guarda.

Después, la plataforma permite registrar lo que ocurrió cuando se utilizó la actividad.

Esa experiencia puede compartirse voluntariamente.

Otros docentes consultan las condiciones, comentarios y valoraciones.

Uno de ellos propone una mejora.

Amazon Bedrock ayuda a incorporar esa sugerencia en una nueva versión.

El nuevo recurso conserva su historia, autoría y procedencia.

Con el tiempo, las experiencias compartidas permiten que los docentes consulten alternativas y sigan perfeccionando sus propias prácticas.

## MENSAJE CENTRAL DE AULALISTA

**"Lo que un docente aprende enseñando puede ayudar al siguiente a preparar mejor su clase".**

Y nuestra propuesta de valor:

**AulaLista convierte recursos educativos y experiencias docentes en conocimiento colectivo que puede consultarse, adaptarse, aplicarse, evaluarse y mejorarse con ayuda de inteligencia artificial.**

Construye el MVP y verifica que el recorrido de aprendizaje colectivo funcione de extremo a extremo.