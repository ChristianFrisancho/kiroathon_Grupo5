import { api, detailsList, operationKey, writeErrorMessage } from '../api.js';
import { clearWorking, localCopyAvailable, persistWorking, setFlash, state } from '../state.js';
import { lessonSteps } from '../ui.js';
import { referenceMap, timeBudget } from '../viz.js';
import { announce, clear, disableAll, engineBadge, errorBox, h } from '../util.js';

const MAX_MATERIALS = 20;

const MAX_ACTIVITIES = 12;
const MAX_TITLE = 200;
const MAX_TEXT = 2000;

function nextActivityId(activities) {
  const used = new Set(activities.map((a) => a.id));
  let n = activities.length + 1;
  while (used.has(`a${n}`)) n += 1;
  return `a${n}`;
}

// Mi aula · Revisar: el docente corrige el borrador y decide qué versión guarda.
export async function renderRevisar({ navigate, isCurrent = () => true }) {
  const w = state.working;
  if (!w) {
    return h('div', { class: 'stack' },
      lessonSteps(2),
      h('h1', null, 'Revisar el borrador'),
      h('p', { class: 'lead' }, 'No hay ningún borrador en curso. Crea uno desde Preparar clase.'),
      h('a', { class: 'btn primary', href: '#/aula' }, 'Preparar clase'));
  }
  const module = await api.get(`/api/modules/${w.moduleId}`);
  const content = w.content;
  const declared = new Set((w.context.materials || []).map((m) => m.toLocaleLowerCase('es')));
  let saving = false;
  let revision = 0;

  const editor = h('div', { class: 'stack' });
  const feedback = h('div');
  const sumBox = h('p', { role: 'status' });
  const blockers = h('div', { class: 'small' });
  const activitiesBox = h('div');
  const budgetBox = h('div', { class: 'budget' });
  const refsBox = h('div', { class: 'refs-map' });
  let budget = { update() {} };
  let refMap = { update() {} };
  const localNote = h('p', { class: 'muted small' });
  const saveDraft = h('button', { type: 'button', class: 'btn', onclick: () => save(false) }, 'Guardar borrador');
  const saveReviewed = h('button', { type: 'button', class: 'btn primary big', onclick: () => save(true) }, 'Guardar versión revisada');

  function total() {
    return content.activities.reduce((acc, a) => acc + (Number.isInteger(a.minutes) ? a.minutes : 0), 0);
  }

  // Validación del cliente alineada con validators.py; el servidor vuelve a validar al guardar.
  function problems() {
    const list = [];
    const target = Number(w.context.durationMinutes);
    if (!Number.isInteger(target) || target < 10 || target > 180) list.push('La duración debe ser un entero entre 10 y 180 minutos.');
    if (!content.title.trim()) list.push('Escribe un título.');
    if (content.title.length > MAX_TITLE) list.push(`El título admite ${MAX_TITLE} caracteres.`);
    if (!content.purpose.trim()) list.push('Escribe el propósito.');
    if (!content.expectedEvidence.trim()) list.push('Escribe la evidencia esperada.');
    if (content.activities.length < 1) list.push('La sesión necesita al menos una actividad.');
    if (content.activities.length > MAX_ACTIVITIES) list.push(`Máximo ${MAX_ACTIVITIES} actividades.`);
    content.activities.forEach((a, i) => {
      if (!a.title.trim()) list.push(`Actividad ${i + 1}: falta el título.`);
      if (!a.description.trim()) list.push(`Actividad ${i + 1}: falta la descripción.`);
      if (a.description.length > MAX_TEXT) list.push(`Actividad ${i + 1}: la descripción es demasiado larga.`);
      if (!Number.isInteger(a.minutes) || a.minutes <= 0) list.push(`Actividad ${i + 1}: los minutos deben ser un entero mayor que 0.`);
    });
    if (content.materials.length > MAX_MATERIALS) list.push(`Máximo ${MAX_MATERIALS} materiales.`);
    if (content.materials.some((m) => m.length > 60)) list.push('Cada material admite 60 caracteres.');
    if (content.purpose.length > MAX_TEXT || content.expectedEvidence.length > MAX_TEXT) list.push('El propósito y la evidencia admiten 2000 caracteres.');
    if ((w.reason || '').length > 300) list.push('El motivo admite 300 caracteres.');
    const extra = content.materials.filter((m) => !declared.has(m.toLocaleLowerCase('es')));
    if (extra.length) list.push(`Materiales no declarados al preparar: ${extra.join(', ')}.`);
    if (Number.isInteger(target) && total() !== target) list.push(`Los tiempos suman ${total()} min y la clase dura ${target} min.`);
    return list;
  }

  function sync() {
    const sum = total();
    const target = Number(w.context.durationMinutes);
    const sumOk = sum === target;
    sumBox.className = sumOk ? 'sum-ok' : 'sum-bad';
    sumBox.textContent = sumOk
      ? `Los tiempos suman ${sum} de ${target} min.`
      : `Los tiempos suman ${sum} min y la clase dura ${target} min. Ajusta para poder guardar.`;
    const list = problems();
    clear(blockers);
    if (list.length) {
      blockers.appendChild(h('p', { class: 'm0' }, h('strong', null, 'Para guardar, corrige: ')));
      blockers.appendChild(h('ul', { class: 'problem-list' }, list.map((p) => h('li', null, p))));
    }
    const blocked = saving || list.length > 0;
    saveDraft.disabled = blocked;
    saveReviewed.disabled = blocked;
    budget.update();
    refMap.update();
    localNote.textContent = localCopyAvailable()
      ? 'Cambios pendientes de guardar · copia local en este navegador (aún no está en Mi portafolio).'
      : 'Cambios pendientes de guardar · este navegador no permite copias locales: guarda antes de cerrar la pestaña.';
  }

  const touch = () => {
    revision += 1;
    persistWorking();
    sync();
  };

  function refsDetails(activity) {
    const box = h('div');
    const paint = () => {
      clear(box);
      if (!activity.references.length) {
        box.appendChild(h('p', { class: 'muted small' }, 'Sin referencias al módulo.'));
        return;
      }
      box.appendChild(h('details', { class: 'fragments' },
        h('summary', null, `Ver referencias (${activity.references.join(', ')})`),
        activity.references.map((id) => {
          const fragment = module.fragments.find((f) => f.id === id);
          return fragment ? h('div', { class: 'source' }, h('strong', null, `${id}. `), fragment.text) : null;
        })));
    };
    paint();
    return { box, paint };
  }

  function paintActivities() {
    clear(activitiesBox);
    content.activities.forEach((activity, index) => {
      const refs = refsDetails(activity);
      activitiesBox.appendChild(h('section', { class: 'activity', 'aria-labelledby': `act-h-${index}` },
        h('div', { class: 'row between' },
          h('h3', { id: `act-h-${index}`, class: 'm0' }, `Actividad ${index + 1}`),
          h('span', { class: 'badge' }, `${Number.isInteger(activity.minutes) ? activity.minutes : '?'} min`)),
        h('div', { class: 'form-grid' },
          h('div', { class: 'field' },
            h('label', { for: `act-title-${index}` }, 'Título'),
            h('input', {
              id: `act-title-${index}`, type: 'text', value: activity.title, maxlength: MAX_TITLE,
              oninput: (e) => { activity.title = e.target.value; touch(); },
            })),
          h('div', { class: 'field' },
            h('label', { for: `act-min-${index}` }, 'Minutos'),
            h('input', {
              id: `act-min-${index}`, type: 'number', min: 1, max: 180, step: 1, inputmode: 'numeric',
              value: String(activity.minutes),
              oninput: (e) => {
                const raw = e.target.value.trim();
                activity.minutes = raw === '' ? 0 : Number(raw);
                const badge = e.target.closest('.activity').querySelector('.badge');
                if (badge) badge.textContent = `${Number.isInteger(activity.minutes) ? activity.minutes : '?'} min`;
                touch();
              },
            }))),
        h('div', { class: 'field' },
          h('label', { for: `act-desc-${index}` }, 'Qué hacen el docente y el grupo'),
          h('textarea', { id: `act-desc-${index}`, oninput: (e) => { activity.description = e.target.value; touch(); } },
            activity.description)),
        h('fieldset', { class: 'field refs' },
          h('legend', null, 'Referencias al módulo'),
          h('div', { class: 'row' }, module.fragments.map((f) =>
            h('label', { class: 'check' },
              h('input', {
                type: 'checkbox', checked: activity.references.includes(f.id),
                onchange: (e) => {
                  activity.references = e.target.checked
                    ? [...new Set([...activity.references, f.id])].sort()
                    : activity.references.filter((r) => r !== f.id);
                  touch();
                  refs.paint();
                },
              }), f.id))),
          refs.box),
        h('button', {
          type: 'button', class: 'btn ghost danger', disabled: content.activities.length <= 1,
          onclick: () => { content.activities.splice(index, 1); touch(); paintActivities(); },
        }, `Quitar actividad ${index + 1}`)));
    });
    activitiesBox.appendChild(h('button', {
      type: 'button', class: 'btn', disabled: content.activities.length >= MAX_ACTIVITIES,
      onclick: () => {
        content.activities.push({
          id: nextActivityId(content.activities), title: 'Nueva actividad', minutes: 1,
          description: 'Describe la actividad.', references: [],
        });
        touch();
        paintActivities();
        const last = activitiesBox.querySelectorAll('.activity');
        const input = last[last.length - 1] && last[last.length - 1].querySelector('input[type="text"]');
        if (input) input.focus();
      },
    }, 'Añadir actividad'));
  }

  async function save(markReviewed) {
    if (saving) return;
    const list = problems();
    if (list.length) { sync(); blockers.querySelector('ul') && saveDraft.focus(); return; }
    saving = true;
    const startedAt = revision;
    const workingAtStart = state.working;
    // Copia de la operación: lo que se envía no cambia aunque el estado en memoria cambie.
    // El origen (Bedrock, respaldo o docente) lo decide el servidor a partir de draftId; no se envía.
    const body = JSON.parse(JSON.stringify(w.sessionId
      ? { context: w.context, content, markReviewed, reason: w.reason || '', parentVersionId: w.parentVersionId || undefined }
      : {
        context: w.context, content, markReviewed, reason: w.reason || '', moduleId: w.moduleId,
        draftId: w.draftId || undefined,
        provenance: w.provenance && !w.draftId ? { experienceId: w.provenance.experienceId } : undefined,
      }));
    // Misma clave si se reintenta el mismo contenido: el servidor no duplica la sesión.
    const payload = { ...body, operationKey: operationKey(w, body) };
    persistWorking();
    clear(feedback);
    disableAll(editor, true);
    sync();
    const label = markReviewed ? saveReviewed : saveDraft;
    const previous = label.textContent;
    label.textContent = 'Guardando…';
    feedback.appendChild(h('p', { class: 'loading', role: 'status' }, 'Guardando en Mi portafolio…'));
    try {
      const saved = w.sessionId
        ? await api.post(`/api/sessions/${w.sessionId}/versions`, payload)
        : await api.post('/api/sessions', payload);
      if (!saved || typeof saved.id !== 'string') throw new Error('Recibimos una respuesta inesperada del servidor.');
      // Solo se limpia la copia de ESTE guardado y si no hubo ediciones después de enviar.
      if (state.working === workingAtStart && revision === startedAt) clearWorking();
      setFlash(markReviewed ? 'Versión revisada guardada' : 'Borrador guardado');
      if (isCurrent()) navigate(`/portafolio/${saved.id}`);
      else announce(markReviewed ? 'Versión revisada guardada en Mi portafolio' : 'Borrador guardado en Mi portafolio');
    } catch (error) {
      if (!isCurrent()) return;
      clear(feedback);
      const message = writeErrorMessage(error);
      const box = errorBox(message.includes('Tu edición sigue aquí') ? message : `${message} Tu edición sigue aquí.`,
        null, detailsList(error));
      if (error.outcomeUnknown) box.appendChild(h('a', { class: 'btn', href: '#/portafolio' }, 'Revisar Mi portafolio'));
      if (error.code === 'version_conflict' && w.sessionId) {
        box.appendChild(h('div', { class: 'row' },
          h('a', { class: 'btn', href: `#/portafolio/${w.sessionId}` }, 'Abrir la versión nueva'),
          h('button', {
            type: 'button', class: 'btn',
            onclick: () => {
              // La edición se conserva y se guardará como una sesión nueva, sin pisar la otra versión.
              w.provenance = null; w.sessionId = null; w.parentVersionId = null; w.draftId = null; w.op = null;
              content.title = `${content.title} (mi edición)`.slice(0, MAX_TITLE);
              persistWorking();
              navigate('/revisar');
            },
          }, 'Guardar mi edición como sesión nueva')));
      }
      feedback.appendChild(box);
      box.focus();
      announce('No se pudo confirmar el guardado');
    } finally {
      saving = false;
      label.textContent = previous;
      disableAll(editor, false);
      if (isCurrent()) { paintActivities(); sync(); }
    }
  }

  const reason = h('input', {
    id: 'f-reason', type: 'text', maxlength: 300, value: w.reason || '',
    'aria-describedby': 'h-reason',
    oninput: (e) => { w.reason = e.target.value; touch(); },
  });

  const g = w.generatedBy || {};
  const engineText = g.engine === 'manual' ? 'Esta sesión fue editada por el docente.' : (g.label || 'Origen no indicado.');

  append(editor, [
    h('div', { class: 'card stack' },
      h('div', { class: 'field' },
        h('label', { for: 'f-title' }, 'Título de la sesión'),
        h('input', { id: 'f-title', type: 'text', value: content.title, maxlength: MAX_TITLE, oninput: (e) => { content.title = e.target.value; touch(); } })),
      h('dl', { class: 'facts inline' },
        h('dt', null, 'Grado'), h('dd', null, w.context.grade),
        h('dt', null, 'Materiales declarados'), h('dd', null, w.context.materials.join(', ') || 'ninguno'),
        h('dt', null, 'Indicaciones'), h('dd', null, w.context.notes || 'ninguna')),
      h('div', { class: 'form-grid' },
        h('div', { class: 'field' },
          h('label', { for: 'f-total' }, 'Duración de la clase (min)'),
          h('input', {
            id: 'f-total', type: 'number', min: 10, max: 180, step: 1, inputmode: 'numeric',
            value: String(w.context.durationMinutes),
            oninput: (e) => {
              const v = e.target.value.trim() === '' ? 0 : Number(e.target.value);
              w.context.durationMinutes = v; content.durationMinutes = v; touch();
            },
          })),
        h('div', { class: 'field' },
          h('label', { for: 'f-mats' }, 'Materiales de la sesión'),
          h('input', {
            id: 'f-mats', type: 'text', value: content.materials.join(', '), 'aria-describedby': 'h-mats',
            oninput: (e) => { content.materials = e.target.value.split(',').map((s) => s.trim()).filter(Boolean); touch(); },
          }),
          h('span', { id: 'h-mats', class: 'hint' }, 'Solo los que declaraste al preparar.'))),
      h('div', { class: 'field' },
        h('label', { for: 'f-purpose' }, 'Propósito'),
        h('textarea', { id: 'f-purpose', oninput: (e) => { content.purpose = e.target.value; touch(); } }, content.purpose))),
    h('section', { class: 'card', 'aria-labelledby': 'acts-title' },
      h('div', { class: 'row between' }, h('h2', { id: 'acts-title', class: 'm0' }, 'Actividades con tiempos'), sumBox),
      h('p', { class: 'muted small' }, 'Arrastra el borde entre dos actividades para pasar minutos de una a otra, o edita cada campo «Minutos».'),
      budgetBox,
      activitiesBox),
    h('section', { class: 'card', 'aria-labelledby': 'refs-title' },
      h('h2', { id: 'refs-title', class: 'm0' }, 'Sustento en el módulo'),
      h('p', { class: 'muted small' }, 'Cada línea une un fragmento del módulo con la actividad que lo cita. Cambia las referencias en cada actividad.'),
      refsBox),
    h('div', { class: 'card stack' },
      h('div', { class: 'field' },
        h('label', { for: 'f-evidence' }, 'Evidencia esperada'),
        h('textarea', { id: 'f-evidence', 'aria-describedby': 'h-evidence', oninput: (e) => { content.expectedEvidence = e.target.value; touch(); } }, content.expectedEvidence),
        h('span', { id: 'h-evidence', class: 'hint' }, 'Lo que la sesión propone observar; no es lo que ocurrió en el aula.')),
      h('div', { class: 'field' },
        h('label', { for: 'f-reason' }, w.sessionId ? 'Motivo del cambio (opcional)' : 'Nota de esta versión (opcional)'),
        reason,
        h('span', { id: 'h-reason', class: 'hint' }, 'Por ejemplo: «simplifiqué las instrucciones iniciales».'))),
  ]);

  const page = h('div', null,
    lessonSteps(2),
    h('h1', null, 'Revisar el borrador'),
    h('p', { class: 'lead' }, 'La IA prepara; tú decides. Corrige lo que haga falta y elige si guardas un borrador o una versión revisada.'),
    h('div', { class: `alert ${g.isBedrock ? 'ok' : 'info'}` },
      h('div', { class: 'row' }, h('strong', null, 'Origen del borrador:'), engineBadge(g)),
      h('p', { class: 'm0 small' }, engineText)),
    Array.isArray(w.reviewNotes) && w.reviewNotes.length
      ? h('div', { class: 'alert warn' },
          h('p', { class: 'm0' }, h('strong', null, 'Revisa antes de guardar:')),
          h('ul', { class: 'problem-list' }, w.reviewNotes.map((n) => h('li', null, n))))
      : null,
    w.sessionId
      ? h('p', { class: 'alert info' }, 'Estás editando la versión vigente de una sesión guardada: al guardar se crea una versión nueva y las anteriores se conservan.')
      : null,
    w.provenance
      ? h('div', { class: 'alert info' },
          `Adaptación de «${w.provenance.title}», compartida por ${w.provenance.authorLabel}. La procedencia se conservará al guardar. `,
          h('a', { href: `#/red/${w.provenance.experienceId}` }, 'Ver experiencia original'))
      : null,
    h('p', { class: 'muted small' }, `Módulo: ${module.title} (versión ${module.version}). ${module.sourceLabel}`),
    editor,
    h('div', { class: 'card action-bar stack' },
      blockers,
      h('div', { class: 'row' }, saveReviewed, saveDraft,
        h('button', {
          type: 'button', class: 'btn ghost danger',
          onclick: () => {
            if (saving) return;
            if (window.confirm('¿Descartar este borrador? Los cambios no guardados se perderán.')) {
              clearWorking();
              navigate(w.sessionId ? `/portafolio/${w.sessionId}` : '/hoy');
            }
          },
        }, 'Descartar')),
      localNote,
      feedback),
    h('p', { class: 'muted small' }, 'Guardar no significa haber impartido la clase. Después podrás registrar lo que observes al aplicarla.'));

  budget = timeBudget(budgetBox, {
    getActivities: () => content.activities,
    getTotal: () => w.context.durationMinutes,
    isLocked: () => saving,
    onShift: (i, a, b, done) => {
      content.activities[i].minutes = a;
      content.activities[i + 1].minutes = b;
      [[i, a], [i + 1, b]].forEach(([k, v]) => {
        const input = document.getElementById(`act-min-${k}`);
        if (input) input.value = String(v);
        const badge = input && input.closest('.activity').querySelector('.badge');
        if (badge) badge.textContent = `${v} min`;
      });
      if (done) touch();
    },
  });
  refMap = referenceMap(refsBox, { fragments: module.fragments, getActivities: () => content.activities });
  paintActivities();
  sync();
  return page;
}

function append(parent, children) {
  children.forEach((c) => c && parent.appendChild(c));
  return parent;
}
