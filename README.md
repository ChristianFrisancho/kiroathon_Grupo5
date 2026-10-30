# AulaLista: ayuda al docente de colegio público a pasar del módulo del curso a una clase y a su portafolio

**Equipo T005, Los 4 del grupo 5 · Track: Copiloto del docente público.** *Del módulo del curso a la sesión de clase y al portafolio de evidencias.*

Un docente de colegio público necesita convertir el contenido de un curso en una clase para su grupo, su tiempo y sus materiales, conservar su trabajo y registrar lo que observa al aplicarla. Principio: **la IA prepara; el docente decide.**

## Estado (fase 1, local)

| Elemento | Estado |
|---|---|
| Backend (`back/`) y frontend (`front/`) | Implementados y probados en local |
| Persistencia | SQLite real (se conserva al recargar y al reiniciar) |
| Generación de la sesión | **Plantilla local determinista, rotulada «No es Amazon Bedrock»** |
| Amazon Bedrock, DynamoDB, API Gateway, Lambda | **Pendientes (fase 2).** Nada está desplegado en AWS |
| Voz con Transcribe | Pendiente (opcional, fase 2) |

No se entrevistó a docentes ni se midió ahorro de tiempo o mejora educativa. Todos los datos son simulados y no hay integración con APRENDE PERÚ.

## Qué hace

- **Hoy / Mi tiempo:** «Preparar clase», «Mi portafolio», sesiones recientes y retomar un borrador.
- **Mi aprendizaje:** módulo «Escucha activa y diálogo respetuoso» (simulado) con fragmentos M1–M3 y «Usar en mi clase».
- **Mi aula:** módulo, grado, duración, materiales e indicaciones → «Crear borrador» → revisar y editar → guardar borrador o versión revisada. El código valida formato, que los minutos sumen y que las referencias existan.
- **Mi portafolio:** sesiones, versiones, copia, regeneración, impresión y registros de aplicación (rotulados «Registro simulado»).
- **Mi red · Aprendemos juntos:** experiencia simulada con valoración de uso 1–5 (4 criterios, «No puedo valorarlo»), media (ejemplo: **4,4/5 · 3 valoraciones completas · Pocas valoraciones · Datos simulados**), comentarios de diseño, resumen y adaptación con procedencia.
- **Mis oportunidades:** función futura, sin pagos ni reservas.
- **Mi bienestar:** preferencias elegidas (apagadas por defecto).

## Estructura

```
back/    API en Python (solo biblioteca estándar): api, service, validators, scoring, generator, repository
front/   Aplicación web estática: index.html, css/, js/ (módulos ES, sin compilar)
tests/   Pruebas del flujo completo
.kiro/   Spec (requirements, design, tasks), steering y hook
```

## Ejecutar

```bash
python3 back/run.py          # http://127.0.0.1:8000 (API + front en el mismo origen)
```

Variables opcionales: `AULALISTA_DB`, `AULALISTA_PORT`, `AULALISTA_HOST`, `AULALISTA_DEMO_MODE`, `AULALISTA_GENERATOR` (`local`).

## Pruebas (una sola orden)

```bash
python3 -m unittest discover -s tests
```

No requiere instalar nada. Las pruebas son clases `unittest`, que pytest también descubre (`python -m pytest -q tests`); esa vía no se ha ejecutado porque pytest no está instalado en este entorno.

## API

`GET /health`, `POST /items`, `GET /items`, `GET /items/{id}`, `POST /jobs`, `GET /jobs/{id}` y las rutas `/api/...` de la aplicación (ver `back/aulalista/api.py`). La demo no tiene login: el usuario es `u-demo` y la cabecera `X-User-Id` solo sirve para probar con varias personas.

## Fase 2

Bedrock (Converse API) detrás de la interfaz `Generator`, DynamoDB detrás de `Repository`, `template.yaml` y despliegue. Ver `.kiro/specs/aulalista-copiloto-docente/tasks.md`.
