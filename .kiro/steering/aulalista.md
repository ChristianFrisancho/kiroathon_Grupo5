# AulaLista: reglas del proyecto

- Producto: copiloto del docente de colegio público. Historia única: módulo → sesión adaptada → revisión → guardado → portafolio → registro de aplicación. La IA prepara; el docente decide.
- Estructura: `back/` (API Python, biblioteca estándar), `front/` (HTML, CSS y módulos ES sin compilar), `tests/`. No mezclar código de back y front.
- Verdad ante todo: distinguir propuesto, implementado, probado y desplegado. Un dato simulado se rotula («Datos simulados», «Registro simulado»). Una salida de la plantilla local nunca se presenta como Amazon Bedrock.
- Guardar o revisar una sesión no significa haberla impartido. No inventar resultados, valoraciones, ahorros de horas ni integraciones con APRENDE PERÚ.
- Valoraciones: ausentes nunca valen 0; editar reemplaza; la autoevaluación del autor no cuenta; una versión nueva no hereda la media.
- Interfaz: paleta Halloween (negro `#0b0a0d`, naranja `#ff7a1a`, hueso `#f7efe3`), contraste AA, teclado completo. Todo texto dinámico entra como texto; nunca `innerHTML`.
- Pruebas: una sola orden, `python3 -m unittest discover -s tests`. Ejecutarla antes de dar una tarea por terminada.
- Sin secretos en el repositorio. Los servicios AWS se añaden en la fase 2 detrás de las interfaces `Generator` y `Repository`.
