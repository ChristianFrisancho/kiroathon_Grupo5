# Plan de tareas: AulaLista

En orden de ejecución. `[x]` solo si está implementado y probado; para lo desplegado se indica la verificación con curl.

## Fase 1: backend y frontend locales

- [x] 1. Separar `back/` y `front/`; servidor local que sirve ambos en el mismo origen. _Req: R7.4, R8_
- [x] 2. Módulo simulado M1–M3, caso precargado y experiencia simulada con tres valoraciones. _Req: R1, R5.3_
- [x] 3. Validadores de contexto y sesión (minutos, referencias, materiales). _Req: R2.3_
- [x] 4. Persistencia SQLite transaccional y recuperación tras recarga. _Req: R4.1_
- [x] 5. Borradores, versiones, revisión expresa, regeneración y copia sin heredar revisión. _Req: R3_
- [x] 6. Registros de aplicación simulados ligados a versión. _Req: R4.3_
- [x] 7. Compartir con confirmación; valoración 1–5, media, parciales y unicidad; adaptación con procedencia. _Req: R5_
- [x] 8. Frontend con las siete secciones y paleta naranja y negro. _Req: R6, R8.1_

## Fase 2: AWS

- [x] 9. Medir Converse en la cuenta: `us.amazon.nova-lite-v1:0` responde en unos 2,6 s, así que la generación es síncrona dentro del límite de 29 s. _Req: R2.1_
- [x] 10. `BedrockGenerator`: prompts de sistema, reintentos ante throttling, respaldo rotulado, 502 en otros errores (pruebas en `tests/test_app.py::BedrockFlowTests`). _Req: R2, R5.4, R5.5_
- [x] 11. `DynamoRepository` con el mismo contrato que SQLite y paginación completa (FakeTable de 2 en 2). _Req: R4.1, R7.2_
- [x] 12. Trabajos con estado persistido y resolución al leer en Lambda. _Req: R7.3_
- [x] 13. `template.yaml` (HTTP API, Lambda, DynamoDB, permisos mínimos, Output ApiUrl) y adaptador `back/app.py`. _Req: R9_
- [x] 14. Desplegar el stack `aulalista-t005` en us-east-1 con `TeamId=T005`. _Req: R9_
- [x] 15. Verificar con curl contra ApiUrl: GET / 200 text/html sin redirección; /health; /items (crear, leer, listar); /jobs done con la salida invertida a 1,5 s; borrador real de Bedrock con 45 min. _Req: R7_
- [x] 16. Una sola orden de pruebas con DynamoDB y Bedrock simulados. _Req: R8.2_

## Pendientes

- [ ] 17. Pegar ApiUrl en Perfil del equipo del portal y pulsar «Verificar ahora» en cada insignia (lo hace el equipo).
- [ ] 18. Registrar el frontend con la nota y el texto GenAI de `docs/NOTAS-FRONTEND.md`.
- [ ] 19. Probar el recorrido en un navegador real y con una persona ajena al código.
- [ ] 20. Opcional: Transcribe como voz a texto corregible antes de generar.
- [ ] 21. Documento (PDF o PPTX) y guion del pitch coherentes con lo desplegado.
