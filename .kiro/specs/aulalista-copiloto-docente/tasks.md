# Plan de tareas: AulaLista

Estado real al cierre de la fase 1. Marcado `[x]` solo lo implementado y probado localmente; nada está desplegado en AWS.

## Fase 1: backend y frontend locales

- [x] 1. Estructura `back/` y `front/` separadas; servidor local que sirve ambos. _Req: R7.4, R8_
- [x] 2. Módulo simulado, caso precargado y datos simulados con rótulos. _Req: R1, R5.4_
- [x] 3. Validadores de contexto y sesión (minutos, referencias, materiales). _Req: R2.2_
- [x] 4. Interfaz de generador y plantilla local rotulada; `BedrockGenerator` falla de forma explícita. _Req: R2.4_
- [x] 5. Persistencia SQLite transaccional y recuperación tras recarga. _Req: R4.1_
- [x] 6. Borradores, versiones, revisión expresa, regeneración y copia sin heredar revisión. _Req: R3_
- [x] 7. Registros de aplicación simulados ligados a versión. _Req: R4.3, R4.4_
- [x] 8. Compartir copia con confirmación sin registros privados; valoración 1–5, media, parciales y unicidad. _Req: R5_
- [x] 9. Adaptación con procedencia y versión nueva sin media heredada. _Req: R5.5_
- [x] 10. Contratos `/health`, `/items`, `/jobs` con worker real. _Req: R7_
- [x] 11. Frontend con las siete secciones y paleta naranja y negro. _Req: R6, R8.2_
- [x] 12. Pruebas del flujo completo con una sola orden: `python3 -m unittest discover -s tests`. _Req: R8.3_

## Fase 2: conexión con AWS (pendiente)

- [ ] 13. Medir el tiempo de generación y decidir si requiere trabajo asíncrono.
- [ ] 14. `BedrockGenerator` con la Converse API: prompts que tratan el módulo como datos, validación de salida y errores.
- [ ] 15. `DynamoRepository` con los mismos métodos que `Repository` y pruebas equivalentes.
- [ ] 16. `template.yaml` (API Gateway HTTP, Lambda, DynamoDB, permisos mínimos) y adaptador Lambda sobre `handle_request`.
- [ ] 17. Despliegue, URL HTTPS pública y verificación de GET / (200 text/html, sin redirección).
- [ ] 18. Verificar los contratos de insignias contra la URL desplegada.
- [ ] 19. Opcional: Transcribe como voz a texto corregible antes de generar.

## Pendientes de producto y entrega

- [ ] 20. Prueba con navegador real y con una persona ajena al código.
- [ ] 21. Documento (PDF o PPTX), guion del pitch y notas del frontend coherentes con lo desplegado.
