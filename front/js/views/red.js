import { api, detailsList, operationKey, writeErrorMessage } from '../api.js';
import { setWorking, state } from '../state.js';
import { announce, append, clear, errorBox, formatDate, h, ratingLine, simBadge, formatScore } from '../util.js';
import { ratingRadar } from '../viz.js';

const CRITERIA = [
  ['clarity', '¿Se entendían las instrucciones?', 'Claridad de instrucciones'],
  ['feasibility', '¿Pude realizarla con el tiempo y los materiales indicados?', 'Viabilidad'],
  ['coherence', '¿Permitió trabajar el propósito planteado?', 'Coherencia con el propósito'],
  ['observation', '¿Me ayudó a observar qué comprendía el grupo?', 'Apoyo para observar la comprensión'],
];

// Mi red · Aprendemos juntos: experiencias compartidas (simuladas en esta demostración).
export async function renderRed() {
  const [experiences, recognitions] = await Promise.all([api.get('/api/experiences'), api.get('/api/recognitions')]);
  return h('div', null,
    h('h1', null, 'Mi red · Aprendemos juntos'),
    h('p', { class: 'lead' }, 'Aprende de actividades y experiencias de colegas. En esta demostración las experiencias y valoraciones son simuladas: no hay una comunidad real.'),
    h('div', { class: 'alert info' }, recognitions.text),
    experiences.map((e) =>
      h('article', { class: 'card' },
        h('div', { class: 'row between' },
          h('h2', { class: 'm0' }, e.title),
          h('div', { class: 'row' }, simBadge(e.isSimulated), e.isMine ? h('span', { class: 'badge' }, 'Mi copia compartida') : null)),
        h('p', { class: 'muted' }, `${e.authorLabel} · ${e.grade} · Materiales: ${e.materials.join(', ') || 'ninguno'}`),
        h('p', null, e.purpose),
        h('p', { class: 'score' }, ratingLine(e.ratingSummary, e.isSimulated)),
        h('a', { class: 'btn', href: `#/red/${e.id}` }, 'Abrir experiencia'))),
    h('p', { class: 'muted small' }, 'Para compartir tu propia experiencia, revisa una sesión en Mi portafolio y elige «Compartir copia».'));
}

function activityView(content) {
  return h('div', null,
    h('p', null, h('strong', null, 'Propósito: '), content.purpose),
    content.activities.map((a, i) =>
      h('div', { class: 'activity' },
        h('h3', { class: 'm0' }, `${i + 1}. ${a.title} · ${a.minutes} min`),
        h('p', null, a.description),
        a.references.length ? h('p', { class: 'small muted' }, `Referencias: ${a.references.join(', ')}`) : null)),
    h('p', null, h('strong', null, 'Evidencia esperada: '), content.expectedEvidence));
}

export async function renderExperiencia({ params, navigate }) {
  const commentOp = {};
  const id = params[0];
  let exp = await api.get(`/api/experiences/${id}`);
  const root = h('div');

  function paint() {
    clear(root);
    const summaryBox = h('div', { class: 'card', 'aria-live': 'polite' });
    append(root, [
      h('a', { href: '#/red' }, '← Volver a Mi red'),
      h('h1', null, exp.title),
      h('div', { class: 'row' }, simBadge(exp.isSimulated), h('span', { class: 'badge' }, exp.authorLabel),
        h('span', { class: 'badge' }, `Versión ${exp.versionId}`)),
      h('div', { class: 'card' }, h('h2', { class: 'm0' }, 'Actividad'), activityView(exp.content)),
      h('div', { class: 'section-split' },
        h('section', null,
          h('h2', { class: 'm0' }, 'Contexto'),
          h('ul', null,
            h('li', null, `Grado: ${exp.grade}`),
            h('li', null, `Duración: ${exp.context.durationMinutes} min`),
            h('li', null, `Materiales: ${exp.materials.join(', ') || 'ninguno'}`)),
          h('p', { class: 'muted small' }, exp.content.moduleSourceLabel)),
        h('section', null,
          h('h2', { class: 'm0' }, 'Observación del autor'),
          h('p', null, exp.observation || 'El autor no compartió observaciones.'),
          h('h3', null, 'Mejora propuesta'),
          h('p', null, exp.improvement || 'Sin propuesta de mejora.'))),
      ratingsSection(),
      commentsSection(),
      h('div', { class: 'card' },
        h('h2', { class: 'm0' }, 'Resumen de acuerdos'),
        h('p', { class: 'muted small' }, 'Se construye solo con las valoraciones y comentarios registrados.'),
        h('button', {
          type: 'button', class: 'btn',
          onclick: async (e) => {
            const button = e.currentTarget;
            button.disabled = true;
            clear(summaryBox);
            summaryBox.appendChild(h('p', { class: 'loading', role: 'status' }, 'Resumiendo…'));
            try {
              const result = await api.get(`/api/experiences/${exp.id}/summary`);
              clear(summaryBox);
              append(summaryBox, [h('p', { class: 'pre' }, result.text), h('p', { class: 'muted small' }, result.generatedBy.label)]);
            } catch (error) {
              clear(summaryBox);
              summaryBox.appendChild(errorBox(error.message));
            } finally {
              button.disabled = false;
            }
          },
        }, 'Resumir acuerdos'),
        summaryBox),
      adaptSection(),
    ]);
  }

  function ratingsSection() {
    const s = exp.ratingSummary;
    const feedback = h('div', { 'aria-live': 'polite' });
    const used = h('input', { id: 'v-used', type: 'checkbox', checked: Boolean(exp.myRating) });
    const selects = {};
    const mine = exp.myRating;
    CRITERIA.forEach(([key]) => {
      const sel = h('select', { id: `v-${key}` },
        h('option', { value: '' }, 'No puedo valorarlo'),
        [1, 2, 3, 4, 5].map((n) => h('option', { value: String(n) }, String(n))));
      sel.value = mine && mine[key] ? String(mine[key]) : '';
      selects[key] = sel;
    });
    const context = h('input', { id: 'v-context', type: 'text', maxlength: 200, placeholder: 'Ej.: Cuarto de primaria · pizarra y papel' });
    context.value = mine ? mine.context : '';
    const keep = h('textarea', { id: 'v-keep' }); keep.value = mine ? mine.whatToKeep : '';
    const change = h('textarea', { id: 'v-change' }); change.value = mine ? mine.whatToChange : '';
    const submit = h('button', { type: 'submit', class: 'btn' }, mine ? 'Actualizar mi valoración' : 'Enviar valoración');

    const form = exp.isMine
      ? h('p', { class: 'alert info' }, 'Eres la persona autora: tu autoevaluación no entra en la valoración de la comunidad.')
      : h('form', {
        class: 'stack',
        onsubmit: async (event) => {
          event.preventDefault();
          submit.disabled = true;
          clear(feedback);
          const body = { declaredUse: used.checked, context: context.value, whatToKeep: keep.value, whatToChange: change.value };
          CRITERIA.forEach(([key]) => { body[key] = selects[key].value === '' ? null : Number(selects[key].value); });
          try {
            const result = await api.post(`/api/experiences/${exp.id}/ratings`, body);
            exp = result.experience;
            paint();
            announce('Valoración guardada');
          } catch (error) {
            feedback.appendChild(errorBox(writeErrorMessage(error, 'guardar la valoración'), null, detailsList(error)));
            submit.disabled = false;
          }
        },
      },
        h('h3', null, mine ? 'Tu valoración (editar reemplaza, no duplica)' : 'Valorar mi uso'),
        h('label', { class: 'check', for: 'v-used' }, used, 'He utilizado esta actividad y quiero compartir mi valoración.'),
        h('div', { class: 'form-grid' }, CRITERIA.map(([key, question, name]) =>
          h('div', { class: 'field' }, h('label', { for: `v-${key}` }, name, h('span', { class: 'hint' }, question)), selects[key]))),
        h('div', { class: 'field' }, h('label', { for: 'v-context' }, 'Contexto de uso'), context),
        h('div', { class: 'field' }, h('label', { for: 'v-keep' }, '¿Qué mantendrías?'), keep),
        h('div', { class: 'field' }, h('label', { for: 'v-change' }, '¿Qué cambiarías?'), change),
        submit, feedback);

    const radarBox = h('figure', { class: 'radar m0' });
    ratingRadar(radarBox, {
      criteriaMeans: s.criteriaMeans, ratings: exp.ratings,
      labels: { clarity: 'Claridad', feasibility: 'Viabilidad', coherence: 'Coherencia', observation: 'Observación' },
    });
    if (radarBox.firstChild) {
      radarBox.appendChild(h('figcaption', { class: 'muted small' },
        'Naranja: media de las valoraciones completas. Líneas finas: cada valoración. Escala de 1 a 5.'));
    }
    return h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Valoración de uso'),
      h('div', { class: 'rating-head' },
        h('div', null,
          h('p', { class: 'score' }, s.completeCount ? `${formatScore(s.average)}/5` : 'Sin valoración general'),
          h('p', null, ratingLine(s, exp.isSimulated))),
        radarBox.firstChild ? radarBox : null),
      s.contexts.length ? h('p', { class: 'muted small' }, `Contextos: ${s.contexts.join(' · ')}`) : null,
      s.lastRatedAt ? h('p', { class: 'muted small' }, `Última valoración: ${formatDate(s.lastRatedAt)}`) : null,
      h('p', { class: 'muted small' }, 'La valoración refleja experiencias declaradas de uso; no prueba mejoras de aprendizaje. Las personas que solo leyeron la actividad dejan un comentario de diseño.'),
      exp.ratings.length
        ? h('ul', { class: 'list' }, exp.ratings.map((r) =>
            h('li', null,
              h('div', { class: 'row' }, h('strong', null, r.reviewerLabel),
                h('span', { class: `badge ${r.complete ? 'ok' : 'draft'}` }, r.complete ? 'Valoración completa' : 'Valoración parcial'),
                simBadge(r.isSimulated)),
              h('p', { class: 'small' }, CRITERIA.map(([key, , name]) => `${name}: ${r[key] === null ? 'no puede valorarlo' : r[key]}`).join(' · ')),
              h('p', { class: 'muted small' }, r.context),
              r.whatToKeep ? h('p', { class: 'small' }, `Mantendría: ${r.whatToKeep}`) : null,
              r.whatToChange ? h('p', { class: 'small' }, `Cambiaría: ${r.whatToChange}`) : null)))
        : null,
      form);
  }

  function commentsSection() {
    const feedback = h('div', { 'aria-live': 'polite' });
    const text = h('textarea', { id: 'c-text', maxlength: 1000, required: true });
    const submit = h('button', { type: 'submit', class: 'btn' }, 'Publicar comentario');
    return h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Comentarios de diseño'),
      h('p', { class: 'muted small' }, 'No cuentan como valoraciones de uso.'),
      exp.comments.length
        ? h('ul', { class: 'list' }, exp.comments.map((c) =>
            h('li', null, h('strong', null, c.authorLabel), ' ', simBadge(c.isSimulated), h('p', null, c.text))))
        : h('p', { class: 'muted' }, 'Aún no hay comentarios.'),
      h('form', {
        class: 'stack',
        onsubmit: async (event) => {
          event.preventDefault();
          submit.disabled = true;
          clear(feedback);
          try {
            const body = { text: text.value };
            exp = await api.post(`/api/experiences/${exp.id}/comments`, { ...body, operationKey: operationKey(commentOp, body) });
            paint();
          } catch (error) {
            feedback.appendChild(errorBox(writeErrorMessage(error, 'publicar el comentario')));
            submit.disabled = false;
          }
        },
      },
        h('div', { class: 'field' }, h('label', { for: 'c-text' }, 'Tu comentario'), text), submit, feedback));
  }

  function adaptSection() {
    const feedback = h('div', { 'aria-live': 'polite' });
    const grade = h('input', { id: 'a-grade', type: 'text', maxlength: 60 }); grade.value = exp.context.grade;
    const duration = h('input', { id: 'a-duration', type: 'number', min: 10, max: 180 }); duration.value = exp.context.durationMinutes;
    const materials = h('input', { id: 'a-materials', type: 'text' }); materials.value = exp.context.materials.join(', ');
    const notes = h('textarea', { id: 'a-notes', maxlength: 500 });
    const submit = h('button', { type: 'submit', class: 'btn primary' }, 'Adaptar en Mi aula');
    return h('div', { class: 'card highlight' },
      h('h2', { class: 'm0' }, 'Adaptar en Mi aula'),
      h('p', { class: 'muted small' }, 'Se crea un borrador nuevo que conserva la procedencia y empieza sin valoraciones. La experiencia original no cambia.'),
      h('form', {
        class: 'stack',
        onsubmit: async (event) => {
          event.preventDefault();
          if (state.working && !window.confirm('Tienes otro borrador sin guardar en este navegador. ¿Reemplazarlo por esta adaptación?')) return;
          submit.disabled = true;
          submit.textContent = 'Adaptando…';
          clear(feedback);
          try {
            const draft = await api.post(`/api/experiences/${exp.id}/adapt`, {
              grade: grade.value, durationMinutes: Number(duration.value), materials: materials.value, notes: notes.value,
            });
            setWorking({
              sessionId: null, moduleId: draft.module.id, context: draft.context, content: draft.content,
              draftId: draft.draftId, reviewNotes: draft.reviewNotes || [],
              generatedBy: draft.generatedBy, provenance: draft.provenance, reason: '',
            });
            navigate('/revisar');
          } catch (error) {
            feedback.appendChild(errorBox(error.message));
            submit.disabled = false;
            submit.textContent = 'Adaptar en Mi aula';
          }
        },
      },
        h('div', { class: 'form-grid' },
          h('div', { class: 'field' }, h('label', { for: 'a-grade' }, 'Grado'), grade),
          h('div', { class: 'field' }, h('label', { for: 'a-duration' }, 'Duración (min)'), duration),
          h('div', { class: 'field' }, h('label', { for: 'a-materials' }, 'Materiales'), materials)),
        h('div', { class: 'field' }, h('label', { for: 'a-notes' }, 'Indicaciones ', h('span', { class: 'hint' }, 'Opcional')), notes),
        submit, feedback));
  }

  paint();
  return root;
}
