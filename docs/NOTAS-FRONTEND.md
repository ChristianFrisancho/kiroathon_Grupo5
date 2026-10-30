# Textos para el registro del frontend

URL base desplegada (sin barra final): https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com

Cada línea con prefijo se valida en `tests/test_front_static.py`: máximo 240 caracteres, sin correos ni secuencias de 7 o más dígitos, y con etiquetas que existen en la interfaz.

NOTA: 1) Pulsa Preparar clase y luego Crear borrador con el caso precargado. 2) Edita y pulsa Guardar versión revisada. 3) En Mi portafolio guarda un registro simulado de aplicación.

## Funcionalidad GenAI

Implementada en `back/aulalista/bedrock.py` (API Converse) y verificada contra la URL desplegada. Si Bedrock no responde, la pantalla muestra «Respaldo local» en lugar de atribuirlo a Bedrock. En el servidor local (`python3 back/run.py`) el origen es la plantilla local y la interfaz lo indica.

GENAI: Bedrock adapta el módulo al grado, tiempo y materiales. Pulsa Preparar clase y Crear borrador; revisa las actividades y sus referencias M1-M3. En Mi red, Resumir acuerdos resume las valoraciones.

## Recorrido probado en navegador real (tests/test_browser.py)

Chromium headless de Playwright contra el servidor local, con una base vacía. Son 10 acciones: Preparar clase → Crear borrador → Ver referencias → Editar título → Guardar versión revisada → Volver a Mi portafolio → Abrir sesión → Recargar → Usar ejemplo simulado → Guardar registro.

## Comportamiento de la interfaz

- **Hoy:** la orientación y «Preparar clase» aparecen sin esperar a la API. Solo «Tus sesiones recientes» depende de `/api/overview`; si falla, muestra el error y «Reintentar», nunca un falso «sin sesiones».
- **Preparar clase:** caso simulado precargado; validación de grado (sin solo espacios) y duración (entero de 10 a 180) con `aria-invalid`, texto visible y foco en el primer campo con error. Los campos se bloquean mientras se crea el borrador y una sola acción envía un solo POST. Si hay un borrador sin guardar, se pide elegir entre «Continuar borrador» y «Reemplazar y crear borrador». «Reintentar» pasa por la misma validación.
- **Revisar:** origen real del borrador (Amazon Bedrock, respaldo local o plantilla local); referencias con su texto en «Ver referencias». La acción principal es «Guardar versión revisada»; «Guardar borrador» sigue disponible y «Descartar» pide confirmación. Los botones se bloquean mientras hay errores o un guardado en curso. Si se pierde la confirmación: «No recibimos la confirmación. Revisa Mi portafolio antes de volver a guardar para evitar duplicados», sin reintento automático.
- **Portafolio:** «Guardado en Mi portafolio» solo tras la respuesta del servidor. Al ver una versión antigua aparece «Estás viendo la versión X», y cada acción nombra la versión a la que afecta. El registro tiene un selector «Versión utilizada». Los textos de registro y de compartir no enviados se conservan por sesión y versión al cambiar de versión o recargar.
- **Estado local:** copia en `localStorage` validada al leer; si está dañada se descarta con aviso. Si el navegador no permite almacenamiento, el flujo sigue en memoria y la interfaz no promete recuperar tras recargar.

## Capturas

`docs/capturas/` (las genera `tests/test_browser.py`): Hoy y Preparar a 320, 390, 768 y 1440 px, y la sesión guardada en escritorio.
