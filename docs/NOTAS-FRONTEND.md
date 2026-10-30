# Textos para el registro del frontend

URL base desplegada (sin barra final): https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com

**Estado de esa URL:** sirve el commit `c68e513`, con las correcciones descritas abajo (verificado en modo lectura el 30-oct; ver docs/VERIFICACION.md).

Cada línea con prefijo se valida en `tests/test_front_static.py`: máximo 240 caracteres, sin correos ni secuencias de 7 o más dígitos, y con etiquetas que existen en la interfaz.

NOTA: 1) Pulsa Preparar clase y luego Crear borrador con el caso precargado. 2) Edita y pulsa Guardar versión revisada. 3) En Mi portafolio guarda un registro simulado de aplicación.

## Funcionalidad GenAI

Implementada en `back/aulalista/bedrock.py` (API Converse). En la URL desplegada se verificó la generación real con `us.amazon.nova-lite-v1:0`. Si Bedrock no responde dentro del presupuesto de tiempo, la pantalla muestra «Respaldo local» y no lo atribuye a Bedrock. En local (`python3 back/run.py`) el origen es la plantilla local.

GENAI: Bedrock adapta el módulo al grado, tiempo y materiales. Pulsa Preparar clase y Crear borrador; revisa actividades y referencias M1-M3. Si Bedrock no responde verás «Respaldo local». En Mi red, Resumir acuerdos.

## Recorrido probado en navegador real (tests/test_browser.py, local)

Chromium headless de Playwright contra el servidor local con una base vacía. Son 10 acciones: Preparar clase → Crear borrador → Ver referencias → Editar título → Guardar versión revisada → Volver a Mi portafolio → Abrir sesión → Recargar → Usar ejemplo simulado → Guardar registro.

## Comportamiento de la interfaz

- **Hoy:** la orientación y «Preparar clase» aparecen sin esperar a la API. Solo «Tus sesiones recientes» depende de `/api/overview`; si falla, muestra el error con «Reintentar», nunca un falso «sin sesiones».
- **Preparar clase:**
  - Caso simulado precargado. Se validan el grado (sin solo espacios) y la duración (entero de 10 a 180), con `aria-invalid`, texto visible y foco en el primer campo con error.
  - Los campos se bloquean mientras se crea el borrador. Si ya hay un borrador sin guardar, se pide elegir «Continuar borrador» o «Reemplazar y crear borrador». «Reintentar» pasa por la misma validación.
- **Revisar:**
  - Muestra el origen real del borrador (Amazon Bedrock, respaldo local o plantilla local) y los avisos del servidor («Revisa antes de guardar»): referencias inventadas que se quitaron y recursos mencionados que no se declararon.
  - Acción principal «Guardar versión revisada»; «Guardar borrador» sigue disponible.
  - Cada guardado lleva una clave de operación. Si se perdió la confirmación, el mismo reintento no duplica la sesión.
  - Si otra edición guardó antes una versión, aparece el mensaje de conflicto con «Abrir la versión nueva» o «Guardar mi edición como sesión nueva». La edición se conserva.
- **Portafolio:**
  - «Guardado en Mi portafolio» aparece solo tras la respuesta del servidor. Al ver una versión antigua: «Estás viendo la versión X».
  - Selector «Versión utilizada» para el registro. El texto no enviado se conserva por sesión y versión al cambiar de versión o recargar.
- **Estado local:** la copia en `localStorage` se valida al leer. Si el navegador bloquea el almacenamiento, el flujo sigue en memoria y la interfaz lo dice.

## Capturas

`docs/capturas/` (las genera `tests/test_browser.py`): Hoy y Preparar a 320, 390, 640 (equivale a 1280 px con zoom del 200 %), 768 y 1440 px, y la sesión guardada en escritorio.
