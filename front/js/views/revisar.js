import { api } from '../api.js';
import { clearWorking, persistWorking, state } from '../state.js';
import { announce, clear, errorBox, h } from '../util.js';

// Mi aula · Revisar: el docente corrige el borrador y decide qué versión guarda.
export async function renderRevisar({ navigate }) {
  const w = state.working;
  if (!w) {
    return h('div', null,
      h('h1', null, 'Revisar'),
      h('p', { class: 'lead' }, 'No hay ningún borrador en curso. Crea uno desde Mi aula.'),
      h('a', { class: 'btn primary', href: '#/aula' }, 'Preparar clase'));
  }
  const module = await api.get(`/api/modules/${w.moduleId}`);
  const content = w.content;
  const fragmentIds = module.fragments.map((f) => f.id);

  const feedback = h('div', { 'aria-live': 'polite' });
  const sumBox = h('p', { class: 'sum-ok', role: 'status' });
  const activitiesBox = h('div');
  const saveDraft = h('button', { type: 'button', class: 'btn', onclick: () => save(false) }, 'Guardar borrador');
  const saveReviewed = h('button', { type: 'button', class: 'btn primary', onclick: () => save(true) }, 'Guardar versión revisada');

  const touch = () => {
    persistWorking();
    paintSum();
  };

  function total() {
    return content.activities.reduce((acc, a) => acc + (Number(a.minutes) || 0), 0);
  }

  function paintSum() {
    const sum = total();
    const target = Number(w.context.durationMinutes);
    const ok = sum === target;
    sumBox.className = ok ? 'sum-ok' : 'sum-bad';
    sumBox.textContent = ok
      ? `Los tiempos suman ${sum} de ${target} min.`
      : `Los tiempos suman ${sum} min y la clase dura ${target} min. Ajusta para poder guardar.`;
    saveDraft.disabled = !ok;
    saveReviewed.disabled = !ok;
  }

  function paintActivities() {
    clear(activitiesBox);
    content.activities.forEach((activity, index) => {
      const refsBox = h('div');
      const paintRefs = () => {
        clear(refsBox);
        activity.references.forEach((id) => {
          const fragment = module.fragments.find((f) => f.id === id);
          if (fragment) refsBox.appendChild(h('div', { class: 'source' }, h('strong', null, `${id}. `), fragment.text));
        });
      };
      paintRefs();
      activitiesBox.appendChild(h('div', { class: 'activity' },
        h('h3', { class: 'm0' }, `Actividad ${index + 1}`),
        h('div', { class: 'form-grid' },
          h('div', { class: 'field' },
            h('label', { for: `act-title-${index}` }, 'Título'),
            h('input', {
              id: `act-title-${index}`, type: 'text', value: activity.title, maxlength: 200,
              oninput: (e) => { activity.title = e.target.value; touch(); },
            })),
          h('div', { class: 'field' },
            h('label', { for: `act-min-${index}` }, 'Minutos'),
            h('input', {
              id: `act-min-${index}`, type: 'number', min: 1, value: activity.minutes,
              oninput: (e) => { activity.minutes = e.target.value === '' ? 0 : Number(e.target.value); touch(); },
            }))),
        h('div', { class: 'field' },
          h('label', { for: `act-desc-${index}` }, 'Qué hace el docente y el grupo'),
          h('textarea', {
            id: `act-desc-${index}`, oninput: (e) => { activity.description = e.target.value; touch(); },
          }, activity.description)),
        h('fieldset', { class: 'field' },
          h('legend', null, 'Referencias al módulo'),
          h('div', { class: 'row' }, fragmentIds.map((id) =>
            h('label', { class: 'check' },
              h('input', {
                type: 'checkbox', checked: activity.references.includes(id),
                onchange: (e) => {
                  activity.references = e.target.checked
                    ? [...activity.references, id].sort()
                    : activity.references.filter((r) => r !== id);
                  persistWorking();
                  paintRefs();
                },
              }), id))),
          refsBox),
        h('button', {
          type: 'button', class: 'btn danger', disabled: content.activities.length <= 1,
          onclick: () => { content.activities.splice(index, 1); persistWorking(); paintActivities(); paintSum(); },
        }, 'Quitar actividad')));
    });
    activitiesBox.appendChild(h('button', {
      type: 'button', class: 'btn',
      onclick: () => {
        content.activities.push({ id: `a${content.activities.length + 1}`, title: 'Nueva actividad', minutes: 1, description: 'Describe la actividad.', references: [] });
        persistWorking(); paintActivities(); paintSum();
      },
    }, 'Añadir actividad'));
  }

  async function save(markReviewed) {
    clear(feedback);
    saveDraft.disabled = true;
    saveReviewed.disabled = true;
    feedback.appendChild(h('p', { class: 'loading', role: 'status' }, 'Guardando…'));
    announce('Guardando');
    try {
      const payload = {
        context: w.context,
        content,
        markReviewed,
        generatedBy: w.generatedBy,
        reason: reason ? reason.value : '',
      };
      const saved = w.sessionId
        ? await api.post(`/api/sessions/${w.sessionId}/versions`, payload)
        : await api.post('/api/sessions', {
          ...payload,
          moduleId: w.moduleId,
          provenance: w.provenance ? { experienceId: w.provenance.experienceId } : undefined,
        });
      clearWorking();
      navigate(`/portafolio/${saved.id}`);
    } catch (error) {
      clear(feedback);
      feedback.appendChild(errorBox(`${error.message} Tu edición sigue aquí.`, () => save(markReviewed)));
      announce('No se pudo guardar');
      paintSum();
    }
  }

  const reason = w.sessionId
    ? h('input', { id: 'f-reason', type: 'text', maxlength: 300, placeholder: 'Ej.: simplifiqué las instrucciones iniciales' })
    : null;

  const generatorNote = w.generatedBy && w.generatedBy.engine === 'manual'
    ? 'Esta sesión fue editada por el docente.'
    : (w.generatedBy && w.generatedBy.label) || '';

  const page = h('div', null,
    h('h1', null, 'Revisar el borrador'),
    h('p', { class: 'lead' }, 'La IA prepara; tú decides. Corrige lo que haga falta y elige si guardas un borrador o una versión revisada.'),
    h('div', { class: `alert ${w.generatedBy && w.generatedBy.isBedrock ? 'ok' : 'info'}` },
      h('strong', null, 'Origen del borrador: '), generatorNote),
    w.provenance
      ? h('div', { class: 'alert info' },
          `Adaptación de «${w.provenance.title}», compartida por ${w.provenance.authorLabel}. La procedencia se conservará al guardar.`,
          ' ', h('a', { href: `#/red/${w.provenance.experienceId}` }, 'Ver experiencia original'))
      : null,
    h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Fuente y restricciones consideradas'),
      h('p', null, `Módulo: ${module.title} (v${module.version}). ${module.sourceLabel}`),
      h('ul', null,
        h('li', null, `Grado: ${w.context.grade}`),
        h('li', null, `Materiales declarados: ${w.context.materials.join(', ') || 'ninguno'}`),
        h('li', null, `Indicaciones: ${w.context.notes || 'ninguna'}`))),
    h('div', { class: 'card' },
      h('div', { class: 'field' },
        h('label', { for: 'f-title' }, 'Título'),
        h('input', { id: 'f-title', type: 'text', value: content.title, maxlength: 200, oninput: (e) => { content.title = e.target.value; touch(); } })),
      h('div', { class: 'field' },
        h('label', { for: 'f-purpose' }, 'Propósito'),
        h('textarea', { id: 'f-purpose', oninput: (e) => { content.purpose = e.target.value; touch(); } }, content.purpose)),
      h('div', { class: 'form-grid' },
        h('div', { class: 'field' },
          h('label', { for: 'f-total' }, 'Duración de la clase (min)'),
          h('input', {
            id: 'f-total', type: 'number', min: 10, max: 180, value: w.context.durationMinutes,
            oninput: (e) => {
              const v = e.target.value === '' ? 0 : Number(e.target.value);
              w.context.durationMinutes = v; content.durationMinutes = v; touch();
            },
          })),
        h('div', { class: 'field' },
          h('label', { for: 'f-mats' }, 'Materiales ', h('span', { class: 'hint' }, 'Solo los que declaraste')),
          h('input', {
            id: 'f-mats', type: 'text', value: content.materials.join(', '),
            oninput: (e) => { content.materials = e.target.value.split(',').map((s) => s.trim()).filter(Boolean); touch(); },
          }))),
      sumBox,
      h('h2', null, 'Actividades con tiempos'),
      activitiesBox,
      h('div', { class: 'field mt' },
        h('label', { for: 'f-evidence' }, 'Evidencia esperada ', h('span', { class: 'hint' }, 'Lo que esperas ver; no es lo que ocurrió en el aula')),
        h('textarea', { id: 'f-evidence', oninput: (e) => { content.expectedEvidence = e.target.value; touch(); } }, content.expectedEvidence)),
      reason ? h('div', { class: 'field' }, h('label', { for: 'f-reason' }, 'Motivo del cambio ', h('span', { class: 'hint' }, 'Opcional')), reason) : null),
    h('div', { class: 'row' }, saveDraft, saveReviewed,
      h('button', {
        type: 'button', class: 'btn danger',
        onclick: () => {
          if (window.confirm('¿Descartar este borrador? Los cambios no guardados se perderán.')) {
            clearWorking();
            navigate(w.sessionId ? `/portafolio/${w.sessionId}` : '/hoy');
          }
        },
      }, 'Descartar')),
    feedback,
    h('p', { class: 'muted small' }, 'Guardar no significa haber impartido la clase. Después podrás registrar lo que observes al aplicarla.'));

  paintActivities();
  paintSum();
  return page;
}
