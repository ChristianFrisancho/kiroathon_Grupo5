# Textos para el registro del frontend

URL base desplegada (sin barra final): https://nxrlbbnerb.execute-api.us-east-1.amazonaws.com

Cada línea con prefijo se valida en `tests/test_front_static.py`: máximo 240 caracteres, sin correos ni secuencias de 7 o más dígitos, y con etiquetas que existen en la interfaz.

NOTA: 1) Pulsa Preparar clase y luego Crear borrador con el caso precargado. 2) Edita y pulsa Guardar versión revisada. 3) En Mi portafolio guarda un registro simulado de aplicación.

## Funcionalidad GenAI

Implementada en `back/aulalista/bedrock.py` (API Converse) y verificada contra la URL desplegada. Si Bedrock no responde, la pantalla muestra «Respaldo local» en lugar de atribuirlo a Bedrock.

GENAI: Bedrock adapta el módulo al grado, tiempo y materiales. Pulsa Preparar clase y Crear borrador; revisa las actividades y sus referencias M1-M3. En Mi red, Resumir acuerdos resume las valoraciones.
