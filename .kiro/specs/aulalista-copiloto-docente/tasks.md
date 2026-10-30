# Plan de tareas: Docente Presente

En orden de ejecución. Estados: **[x] probado en local**, **desplegado** y **verificado públicamente** se indican aparte. La fase 3 está desplegada desde el commit `c68e513` (ver docs/VERIFICACION.md).

## Fase 1: backend y frontend locales

- [x] 1. Separar `back/` y `front/`; servidor local que sirve ambos en el mismo origen. _Req: R7.4, R8_
- [x] 2. Módulo simulado M1–M3, caso precargado y experiencia simulada con tres valoraciones. _Req: R1, R5.3_
- [x] 3. Validadores de contexto y sesión (minutos, referencias, materiales). _Req: R2.3_
- [x] 4. Persistencia SQLite y recuperación tras recarga. _Req: R4.1_
- [x] 5. Borradores, versiones, revisión expresa, regeneración y copia sin heredar revisión. _Req: R3_
- [x] 6. Registros de aplicación simulados ligados a versión. _Req: R4.3_
- [x] 7. Compartir con confirmación; valoración 1–5, media, parciales y unicidad; adaptación con procedencia. _Req: R5_
- [x] 8. Frontend con las siete secciones y paleta naranja y negro. _Req: R6, R8.1_

## Fase 2: AWS (desplegada y verificada con curl el 30-oct, antes de la fase 3)

- [x] 9. Medir Converse en la cuenta: `us.amazon.nova-lite-v1:0` respondió en 2–4 s en la URL desplegada. _Req: R2.1_
- [x] 10. `BedrockGenerator` con prompts de sistema, respaldo rotulado y 502 en otros errores. _Req: R2, R5.4, R5.5_
- [x] 11. `template.yaml`, adaptador `back/app.py`, stack `aulalista-t005` en us-east-1 con `TeamId=T005`. _Req: R9_
- [x] 12. Verificación pública con curl: GET / 200 text/html sin redirección; /health; /items; /jobs; borrador real de Bedrock. _Req: R7_

## Fase 3: integridad, procedencia, tiempos, worker y frontend

- [x] 13. Versiones atómicas y condicionadas a `parentVersionId` en SQLite (UPDATE … WHERE current_version_id) y DynamoDB (TransactWriteItems con `#doc = :expected` y marcador `VNUM#`); 409 `version_conflict`. Prueba: `tests/test_integrity.py::VersionConcurrencyTests` (incluye carrera real con 8 hilos y carrera entre lectura y transacción). _Req: R3.3, R4.1_
- [x] 14. Sin versiones huérfanas ni restauración de la vigente al actualizar fechas. Prueba: `PartialWriteTests`. _Req: R4.1_
- [x] 15. Borradores emitidos por el servidor (`draftId`, caducidad de 24 h validada al leer + TTL) y procedencia derivada en el servidor (`generatedBy`, `editedByTeacher`, `sourceDraftId`). Prueba: `ProvenanceTests`. _Req: R2.5_
- [x] 16. Claves de operación (`operationKey`) persistidas para sesiones, versiones, registros, copias, compartir y comentarios. Prueba: `IdempotencyTests` y `test_browser::test_confirmacion_perdida_y_reintento_no_duplica`. _Req: R4.1_
- [x] 17. Presupuesto de tiempo: plazo de la Lambda (`get_remaining_time_in_millis`) y reintentos solo si alcanzan; SDK sin reintentos. Prueba: `TimeBudgetTests`. _Req: R2.4_
- [x] 18. Worker Lambda de /jobs (`back/worker.py`, invocación asíncrona); GET solo lee; fallo de despacho → 503 y estado `failed`. Prueba: `tests/test_app.py::JobsTests`. _Req: R7.3_
- [x] 19. Patrones de acceso de DynamoDB por partición (USER#, SESSION#, RATINGS#, COMMENTS#, ITEMS_BY_TIME) y migración compatible del esquema anterior sin borrar datos. Prueba: `QueryPatternTests`, `MigrationTests`. _Req: R4.1, R7.2_
- [x] 20. Validación de la salida de IA (referencias mínimas, avisos de recursos no declarados, minutos ≥ 1, salidas truncadas). Prueba: `AiOutputTests`. _Req: R2.3_
- [x] 21. Frontend: portada independiente de la API, cliente HTTP con tiempo máximo, editor sin dobles guardados, conflicto 409 recuperable, versión explícita en registros, formularios conservados, almacenamiento bloqueado. Prueba: `tests/test_browser.py` (16 pruebas en Chromium). _Req: R6, R8_
- [x] 22. Empaquetador validado (directorio temporal, validación de handlers y artefactos, reemplazo final) y template con permisos específicos; `sam validate --lint` pasa. Prueba: `tests/test_packaging.py`. _Req: R9_
- [x] 23. Desplegar la fase 3 (commit `c68e513`) y repetir la verificación pública: `scripts/verify_badges.py` y `scripts/smoke_genai.py --runs 3`, con resultados en `docs/evidencias/` y resumen en `docs/VERIFICACION.md`.
- [x] 24. Validación del sobre Converse y de la estructura de la respuesta del modelo antes de normalizar (`model_output.py`), sin conversiones ni relleno; log mínimo `bedrock_converse_completed` corroborado en CloudWatch.

## Pendientes

- [ ] 25. Pegar ApiUrl en Perfil del equipo del portal y pulsar «Verificar ahora» en cada insignia (lo hace el equipo).
- [ ] 26. Registrar el frontend con la nota y el texto GenAI de `docs/NOTAS-FRONTEND.md`.
- [ ] 27. Probar el recorrido con una persona ajena al código y con un lector de pantalla.
- [ ] 28. Opcional: Transcribe como voz a texto corregible antes de generar.
- [ ] 29. Documento (PDF o PPTX) y guion del pitch coherentes con lo desplegado.
