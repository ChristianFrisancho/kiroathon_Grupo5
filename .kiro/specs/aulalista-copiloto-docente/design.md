# Diseño: AulaLista

## Estructura del repositorio

- `back/`: API en Python 3.9+ solo con biblioteca estándar (apta para Lambda Python 3.12 en la fase 2).
- `front/`: aplicación web estática (HTML, CSS y módulos ES), sin paso de compilación.
- `tests/`: pruebas del flujo completo; se ejecutan con una sola orden.
- `.kiro/`: spec, steering y hooks de este trabajo.

## Backend (`back/aulalista/`)

| Archivo | Responsabilidad |
|---|---|
| `api.py` | Enrutador `handle_request(service, método, ruta, cabeceras, cuerpo)`. No depende de ningún servidor, por lo que la fase 2 lo envuelve en un handler de Lambda. |
| `server.py` | Servidor `http.server` local que sirve la API y `front/` en el mismo origen, con cabeceras de seguridad y CSP. |
| `service.py` | Reglas de negocio: borradores, versiones, revisión, copias, registros, compartir, valoraciones, adaptación, preferencias, items y jobs. |
| `validators.py` | Validación determinista de contexto y sesión (minutos, IDs de referencias, materiales declarados). El servidor resuelve las fuentes; no confía en lo que devuelva el motor. |
| `scoring.py` | Media de valoraciones completas con `Fraction` y redondeo ROUND_HALF_UP a un decimal. |
| `generator.py` | Interfaz `Generator`. `LocalSimulatedGenerator` es una plantilla determinista rotulada «No es Bedrock». `BedrockGenerator` falla de forma explícita hasta la fase 2. |
| `repository.py` | Persistencia SQLite con transacciones. En la fase 2 se sustituye por DynamoDB con los mismos métodos. |
| `seed.py` | Módulo simulado, caso de ejemplo y experiencia simulada con tres valoraciones. |

## Modelo de datos

- **Session** (dueño, título, módulo y versión, procedencia, versión vigente).
- **LessonVersion** (número, versión padre, contexto, contenido, `reviewStatus` borrador|revisada, motivo, motor de origen). Es inmutable salvo el estado de revisión.
- **ApplicationRecord** (sesión, versión, fecha declarada, actividad, observación, próximo ajuste, `isSimulated`).
- **Experience** (copia compartida e inmutable de una versión revisada; su id es también el id de versión valorada).
- **Rating** con unicidad (`versionId`, `reviewerId`): editar actualiza la fila, no inserta otra.
- **Comment** (comentario de diseño, separado de las valoraciones), **Preferences**, **Item**, **Job**.

## Decisiones

1. **Borrador no persistido hasta que el docente guarda.** `POST /api/drafts/generate` no escribe nada; así un fallo no deja sesiones a medias.
2. **Revisión explícita.** `markReviewed: true` es la única forma de crear una versión revisada; copiar o regenerar siempre crea borradores.
3. **Demo sin login.** El usuario es `u-demo`; la cabecera `X-User-Id` solo sirve para probar a varias personas y no es autenticación. La fase 2 usa identidad real.
4. **Jobs reales.** `POST /jobs` guarda el estado `queued`, lo ejecuta un `ThreadPoolExecutor` y persiste `running` y `done`.
5. **Seguridad.** CSP `default-src 'self'`, sin HTML dinámico, validación en el servidor, rutas estáticas confinadas a `front/`.

## Frontend (`front/`)

Enrutamiento por hash. Vistas: Hoy, Mi aprendizaje, Mi aula (Preparar y Revisar), Mi portafolio (lista y detalle), Mi red (lista y detalle), Mis oportunidades y Mi bienestar. Paleta en variables CSS: negro `#0b0a0d`, naranja `#ff7a1a`, hueso `#f7efe3`, con acentos morado, verde y amarillo solo para estados. La copia de trabajo en curso se guarda en `localStorage` únicamente para retomar; lo guardado vive en el servidor.

## Fase 2 (AWS)

`BedrockGenerator` con Converse API, `DynamoRepository`, `template.yaml` (API Gateway HTTP + Lambda + DynamoDB), despliegue y medición del tiempo de generación; Transcribe como entrada de voz opcional.
