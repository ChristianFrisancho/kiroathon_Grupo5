import { api, detailsList, operationKey, writeErrorMessage } from '../api.js';
import {
  clearDraft, draftKey, readDraft, setFlash, setWorking, state, takeFlash, writeDraft,
} from '../state.js';
import { lessonSteps, savedNotice } from '../ui.js';
import { versionTimeline } from '../viz.js';
import {
  announce, append, clear, disableAll, errorBox, formatDate, h, originBadges, reviewBadge, simBadge, todayIso,
} from '../util.js';

// Mi portafolio: lista de sesiones guardadas en el servidor. Vacío y error se distinguen.
export async function renderPortafolio({ isCurrent = () => true }) {
  const box = h('div', { class: 'card', 'aria-busy': 'true' }, h('p', { class: 'loading' }, 'Cargando tus sesiones…'));

  async function load() {
    box.setAttribute('aria-busy', 'true');
    clear(box);
    box.appendChild(h('p', { class: 'loading' }, 'Cargando tus sesiones…'));
    try {
      const sessions = await api.get('/api/sessions');
      if (!isCurrent()) return;
      if (!Array.isArray(sessions)) throw new Error('No pudimos interpretar la lista de sesiones.');
      clear(box);
      if (!sessions.length) {
        box.appendChild(h('div', { class: 'empty-state' },
          h('h2', { class: 'm0' }, 'Todavía no hay sesiones guardadas'),
          h('p', null, 'Cuando guardes un borrador o una versión revisada, aparecerá aquí.'),
          h('a', { class: 'btn primary', href: '#/aula' }, 'Preparar clase')));
        return;
      }
      box.appendChild(h('ul', { class: 'list' }, sessions.map((s) =>
        h('li', null,
          h('div', { class: 'row between' },
            h('div', { class: 'grow' },
              h('a', { class: 'session-title', href: `#/portafolio/${s.id}` }, s.title),
              h('p', { class: 'muted small m0' },
                `Versión ${s.currentVersionNumber} de ${s.versionCount} · actualizada ${formatDate(s.updatedAt)} · ${s.recordCount} registro(s)`),
              s.provenance && s.provenance.type === 'adaptacion'
                ? h('p', { class: 'small m0' }, `Adaptada de «${s.provenance.title}» (${s.provenance.authorLabel})`) : null),
            h('div', { class: 'row' }, reviewBadge(s.reviewStatus),
              s.isShared ? h('span', { class: 'badge' }, 'Copia compartida') : null,
              h('a', { class: 'btn', href: `#/portafolio/${s.id}` }, 'Abrir')))))));
    } catch (error) {
      if (!isCurrent()) return;
      clear(box);
      box.appendChild(errorBox(error.message || 'No pudimos cargar tu portafolio.', load));
    } finally {
      if (isCurrent()) box.setAttribute('aria-busy', 'false');
    }
  }
  void load();

  return h('div', null,
    h('div', { class: 'row between' },
      h('h1', null, 'Mi portafolio'),
      h('a', { class: 'btn primary', href: '#/aula' }, 'Preparar clase')),
    h('p', { class: 'lead' }, 'Tus sesiones, versiones y registros de aplicación, guardados en el servidor.'),
    box);
}

function contentView(version) {
  const c = version.content;
  return h('div', null,
    h('p', null, h('strong', null, 'Propósito: '), c.purpose),
    h('p', { class: 'muted' }, `${version.context.grade} · ${version.context.durationMinutes} min · Materiales: ${c.materials.join(', ') || 'ninguno'}`),
    c.activities.map((a, i) =>
      h('div', { class: 'activity' },
        h('h3', { class: 'm0' }, `${i + 1}. ${a.title} · ${a.minutes} min`),
        h('p', null, a.description),
        a.references.length ? h('p', { class: 'small muted' }, `Referencias: ${a.references.join(', ')}`) : null)),
    h('div', { class: 'section-split' },
      h('section', null,
        h('h3', { class: 'm0' }, 'Evidencia esperada'),
        h('p', { class: 'muted small' }, 'Lo que la sesión propone observar. No demuestra que la clase se haya impartido.'),
        h('p', null, c.expectedEvidence)),
      h('section', null,
        h('h3', { class: 'm0' }, 'Fuentes'),
        c.sources.map((s) => h('div', { class: 'source' }, h('strong', null, `${s.id}. `), s.text)),
        h('p', { class: 'muted small' }, c.moduleSourceLabel))));
}

const SIMULATED_EXAMPLE = {
  activity: 'Actividad por parejas de escucha y parafraseo (ejemplo simulado).',
  observation: 'Ejemplo simulado: varias parejas pidieron repetir las instrucciones antes de empezar.',
  nextAdjustment: 'Ejemplo simulado: dar las instrucciones en tres pasos cortos.',
};

// Detalle de una sesión: versiones, edición, copia, registro de aplicación y compartir.
export async function renderSesion({ params, navigate, isCurrent = () => true, setTitle = () => {} }) {
  const sessionId = params[0];
  let session = await api.get(`/api/sessions/${sessionId}`);
  setTitle(session.title);
  const root = h('div');
  let shownVersionId = session.currentVersionId;
  let notice = takeFlash();
  let pending = false; // una operación de escritura en curso en esta vista
  // Copias de formularios aún no enviados (memoria + localStorage), por sesión y versión.
  const memory = {};
  const getDraft = (key) => memory[key] || readDraft(key);
  const putDraft = (key, value) => { memory[key] = value; writeDraft(key, value); };
  const dropDraft = (key) => { delete memory[key]; clearDraft(key); };
  let recordVersionId = session.currentVersionId;
  let recordVersionChosen = false; // si el docente no eligió, el registro sigue a la versión mostrada
  const ops = {}; // claves de operación por formulario (reintento del mismo contenido = misma clave)
  const showVersion = (id) => {
    shownVersionId = id;
    if (!recordVersionChosen) recordVersionId = id;
    paint();
  };

  function reload(next, message) {
    session = next;
    shownVersionId = session.currentVersionId;
    if (!session.versions.some((v) => v.id === recordVersionId)) recordVersionId = session.currentVersionId;
    notice = message || null;
    paint();
  }

  // Ejecuta una escritura sin reintento automático. Devuelve el resultado o null.
  async function write(action, box, what) {
    if (pending) return null;
    pending = true;
    clear(box);
    disableAll(root, true);
    try {
      return await action();
    } catch (error) {
      if (isCurrent()) {
        const err = errorBox(writeErrorMessage(error, what), null, detailsList(error));
        box.appendChild(err);
        err.focus();
        announce('No se pudo completar la acción');
      }
      return null;
    } finally {
      pending = false;
      if (isCurrent()) disableAll(root, false);
    }
  }

  function paint() {
    clear(root);
    const current = session.currentVersion;
    const shown = session.versions.find((v) => v.id === shownVersionId) || current;
    const viewingOld = shown.id !== current.id;
    const actionFeedback = h('div');
    const timelineBox = h('div', { class: 'timeline' });

    const continueEdit = () => {
      if (state.working && !window.confirm('Tienes otro borrador sin guardar en este navegador. ¿Reemplazarlo por esta sesión?')) return;
      setWorking({
        sessionId: session.id, moduleId: session.moduleId, parentVersionId: current.id, draftId: null, reviewNotes: [],
        context: JSON.parse(JSON.stringify(current.context)),
        content: JSON.parse(JSON.stringify(current.content)),
        generatedBy: current.generatedBy,
        provenance: session.provenance && session.provenance.type === 'adaptacion' ? session.provenance : null,
        reason: '',
      });
      navigate('/revisar');
    };

    append(root, [
      notice ? lessonSteps(4) : null,
      h('a', { class: 'no-print', href: '#/portafolio' }, '← Volver a Mi portafolio'),
      h('h1', null, session.title),
      notice ? savedNotice(notice) : null,
      h('div', { class: 'row' }, reviewBadge(current.reviewStatus),
        h('span', { class: 'badge' }, `Versión vigente: ${current.number} de ${session.versions.length}`),
        originBadges(current), h('span', { class: 'badge saved' }, 'Guardado en Mi portafolio')),
      session.provenance && session.provenance.type === 'adaptacion'
        ? h('p', { class: 'alert info' }, `Adaptación de «${session.provenance.title}», compartida por ${session.provenance.authorLabel}. `,
            h('a', { href: `#/red/${session.provenance.experienceId}` }, 'Ver experiencia original'))
        : null,
      h('div', { class: 'row no-print mt' },
        h('button', { type: 'button', class: 'btn primary', onclick: continueEdit },
          viewingOld ? `Continuar edición (versión vigente ${current.number})` : 'Continuar edición'),
        current.reviewStatus !== 'revisada'
          ? h('button', {
              type: 'button', class: 'btn',
              onclick: async () => {
                const next = await write(() => api.post(`/api/sessions/${session.id}/versions/${current.id}/review`), actionFeedback, 'marcar como revisada');
                if (next && isCurrent()) reload(next, `Versión ${current.number} marcada como revisada`);
              },
            }, `Marcar versión ${current.number} como revisada`) : null,
        h('button', {
          type: 'button', class: 'btn',
          onclick: async () => {
            const body = { versionId: shown.id };
            const next = await write(() => api.post(`/api/sessions/${session.id}/copy`,
              { ...body, operationKey: operationKey(ops.copy || (ops.copy = {}), body) }), actionFeedback, 'crear la copia');
            if (next && isCurrent()) { setFlash(`Copia de la versión ${shown.number} guardada como borrador`); navigate(`/portafolio/${next.id}`); }
          },
        }, `Crear copia de la versión ${shown.number}`),
        h('button', {
          type: 'button', class: 'btn',
          onclick: async (e) => {
            e.target.textContent = 'Regenerando…';
            const next = await write(() => api.post(`/api/sessions/${session.id}/regenerate`, { parentVersionId: current.id }), actionFeedback, 'regenerar');
            if (next && isCurrent()) reload(next, 'Nueva versión regenerada guardada como borrador');
            else if (isCurrent()) e.target.textContent = 'Regenerar borrador';
          },
        }, 'Regenerar borrador'),
        h('button', { type: 'button', class: 'btn ghost', onclick: () => window.print() }, 'Imprimir')),
      actionFeedback,
      h('section', { class: `card${viewingOld ? ' old-version' : ''}`, 'aria-labelledby': 'shown-title' },
        viewingOld
          ? h('p', { class: 'alert warn m0', role: 'status' },
              h('strong', null, `Estás viendo la versión ${shown.number}. `),
              `La versión vigente es la ${current.number}. `,
              h('button', { type: 'button', class: 'btn ghost', onclick: () => showVersion(current.id) }, 'Ver la versión vigente'))
          : null,
        h('div', { class: 'row between' },
          h('h2', { id: 'shown-title', class: 'm0' }, `Versión ${shown.number}${viewingOld ? '' : ' (vigente)'}`), reviewBadge(shown.reviewStatus)),
        h('p', { class: 'muted small' }, `${formatDate(shown.createdAt)}${shown.reason ? ` · ${shown.reason}` : ''}`),
        contentView(shown)),
      h('section', { class: 'card no-print', 'aria-labelledby': 'history-title' },
        h('h2', { id: 'history-title', class: 'm0' }, 'Historial de versiones'),
        h('p', { class: 'muted small' }, 'Una versión nueva no borra las anteriores. Regenerar o copiar no hereda la revisión. Las gotas son registros de aplicación sobre la versión que usaron.'),
        timelineBox,
        h('ul', { class: 'list' }, [...session.versions].reverse().map((v) =>
          h('li', null,
            h('div', { class: 'row between' },
              h('span', null, `Versión ${v.number}${v.id === current.id ? ' (vigente)' : ''} · ${formatDate(v.createdAt)}${v.reason ? ` · ${v.reason}` : ''}`),
              h('div', { class: 'row' }, reviewBadge(v.reviewStatus),
                h('button', {
                  type: 'button', class: 'btn', 'aria-pressed': v.id === shown.id ? 'true' : 'false',
                  onclick: () => showVersion(v.id),
                }, v.id === shown.id ? `Mostrando versión ${v.number}` : `Ver versión ${v.number}`))))))),
      recordsSection(),
      shareSection(),
    ]);
    versionTimeline(timelineBox, {
      versions: session.versions, records: session.records, currentId: current.id, shownId: shown.id,
      onSelect: (id) => showVersion(id),
    });
  }

  function recordsSection() {
    const feedback = h('div');
    const key = draftKey('record', session.id, recordVersionId);
    const draft = getDraft(key) || {};
    const versionSelect = h('select', { id: 'r-version', 'aria-describedby': 'h-r-version' },
      [...session.versions].reverse().map((v) =>
        h('option', { value: v.id }, `Versión ${v.number}${v.id === session.currentVersionId ? ' (vigente)' : ''} · ${v.reviewStatus === 'revisada' ? 'Revisada' : 'Borrador'}`)));
    versionSelect.value = recordVersionId;
    const date = h('input', { id: 'r-date', type: 'date', value: draft.declaredDate || todayIso(), required: true });
    const activity = h('textarea', { id: 'r-activity', required: true, placeholder: 'Qué actividad realizaste y cómo', 'aria-describedby': 'h-r-activity' });
    activity.value = draft.activity || '';
    const observation = h('textarea', { id: 'r-obs', required: true, placeholder: 'Qué viste en el aula, según tú', 'aria-describedby': 'h-r-obs' });
    observation.value = draft.observation || '';
    const next = h('textarea', { id: 'r-next', placeholder: 'Qué cambiarías la próxima vez' });
    next.value = draft.nextAdjustment || '';
    const submit = h('button', { type: 'submit', class: 'btn primary' }, 'Guardar registro');
    const persist = () => {
      // En cuanto el docente escribe, el registro queda fijo en esta versión aunque consulte otra.
      if (activity.value || observation.value || next.value) recordVersionChosen = true;
      putDraft(key, {
        declaredDate: date.value, activity: activity.value, observation: observation.value, nextAdjustment: next.value,
      });
    };
    [date, activity, observation, next].forEach((el) => el.addEventListener('input', persist));
    versionSelect.addEventListener('change', () => {
      recordVersionId = versionSelect.value;
      recordVersionChosen = true;
      paint();
      document.getElementById('r-version').focus();
    });

    const form = h('form', {
      class: 'stack', novalidate: true,
      onsubmit: async (event) => {
        event.preventDefault();
        clear(feedback);
        const versionId = versionSelect.value;
        const chosen = session.versions.find((v) => v.id === versionId);
        const missing = [];
        if (!chosen) missing.push('Elige una versión de esta sesión.');
        if (!date.value) missing.push('Indica la fecha declarada.');
        if (!activity.value.trim()) missing.push('Describe la actividad realizada.');
        if (!observation.value.trim()) missing.push('Escribe la observación declarada.');
        if (missing.length) {
          const box = errorBox('Completa el registro antes de guardarlo.', null, missing);
          feedback.appendChild(box);
          box.focus();
          return;
        }
        const body = {
          versionId, declaredDate: date.value, activity: activity.value,
          observation: observation.value, nextAdjustment: next.value,
        };
        submit.textContent = 'Guardando…';
        const keyed = { ...body, operationKey: operationKey(ops.record || (ops.record = {}), body) };
        const saved = await write(() => api.post(`/api/sessions/${session.id}/records`, keyed), feedback, 'guardar el registro');
        if (!isCurrent()) return;
        if (saved) {
          dropDraft(key);
          ops.record = null;
          let fresh = null;
          try { fresh = await api.get(`/api/sessions/${session.id}`); } catch (e) { /* abajo */ }
          if (!isCurrent()) return;
          if (fresh) reload(fresh, `Registro simulado guardado para la versión ${chosen.number}`);
          else { session.records = [...session.records, saved]; reload(session, `Registro simulado guardado para la versión ${chosen.number}`); }
        } else {
          submit.textContent = 'Guardar registro';
        }
      },
    },
      h('div', { class: 'field' }, h('label', { for: 'r-version' }, 'Versión utilizada'), versionSelect,
        h('span', { id: 'h-r-version', class: 'hint' }, 'El registro queda ligado a esta versión.')),
      h('div', { class: 'field' }, h('label', { for: 'r-date' }, 'Fecha declarada'), date),
      h('div', { class: 'field' }, h('label', { for: 'r-activity' }, 'Actividad realizada'), activity,
        h('span', { id: 'h-r-activity', class: 'hint' }, 'Lo que hiciste con tu grupo.')),
      h('div', { class: 'field' }, h('label', { for: 'r-obs' }, 'Observación declarada'), observation,
        h('span', { id: 'h-r-obs', class: 'hint' }, 'Tu observación, distinta de la evidencia esperada de la sesión.')),
      h('div', { class: 'field' }, h('label', { for: 'r-next' }, 'Próximo ajuste (opcional)'), next),
      h('div', { class: 'row' }, submit,
        h('button', {
          type: 'button', class: 'btn ghost',
          onclick: () => {
            activity.value = SIMULATED_EXAMPLE.activity;
            observation.value = SIMULATED_EXAMPLE.observation;
            next.value = SIMULATED_EXAMPLE.nextAdjustment;
            persist();
            activity.focus();
          },
        }, 'Usar ejemplo simulado')),
      feedback);

    return h('section', { class: 'card no-print', 'aria-labelledby': 'records-title' },
      h('h2', { id: 'records-title', class: 'm0' }, 'Registros de aplicación'),
      h('p', { class: 'muted small' }, 'Opcionales. En esta demostración cada registro se guarda como «Registro simulado» y no equivale a una clase aplicada.'),
      session.records.length
        ? h('ul', { class: 'list' }, session.records.map((r) =>
            h('li', null,
              h('div', { class: 'row' }, simBadge(r.isSimulated, 'Registro simulado'),
                h('span', { class: 'muted small' }, `${r.declaredDate} · versión ${(session.versions.find((v) => v.id === r.versionId) || {}).number || '?'}`)),
              h('p', null, h('strong', null, 'Actividad realizada: '), r.activity),
              h('p', null, h('strong', null, 'Observación declarada: '), r.observation),
              r.nextAdjustment ? h('p', null, h('strong', null, 'Próximo ajuste: '), r.nextAdjustment) : null)))
        : h('p', { class: 'muted' }, 'Aún no hay registros.'),
      h('h3', null, 'Añadir registro simulado'),
      form);
  }

  function shareSection() {
    const current = session.currentVersion;
    if (current.reviewStatus !== 'revisada') {
      return h('section', { class: 'card no-print' },
        h('h2', { class: 'm0' }, 'Compartir en Mi red'),
        h('p', { class: 'muted' }, `Marca la versión ${current.number} como revisada para poder compartir una copia. Tus registros privados no se publican automáticamente.`));
    }
    const key = draftKey('share', session.id, current.id);
    const draft = getDraft(key) || {};
    const feedback = h('div');
    const purpose = h('textarea', { id: 's-purpose', required: true });
    purpose.value = draft.purpose ?? current.content.purpose;
    const description = h('textarea', { id: 's-desc', required: true });
    description.value = draft.description ?? current.content.activities.map((a) => `${a.title} (${a.minutes} min)`).join('; ');
    const observation = h('textarea', { id: 's-obs' }); observation.value = draft.observation || '';
    const improvement = h('textarea', { id: 's-imp' }); improvement.value = draft.improvement || '';
    const confirm = h('input', { id: 's-confirm', type: 'checkbox' });
    const submit = h('button', { type: 'submit', class: 'btn' }, 'Compartir copia');
    const persist = () => putDraft(key, {
      purpose: purpose.value, description: description.value, observation: observation.value, improvement: improvement.value,
    });
    [purpose, description, observation, improvement].forEach((el) => el.addEventListener('input', persist));
    return h('section', { class: 'card no-print', 'aria-labelledby': 'share-title' },
      h('h2', { id: 'share-title', class: 'm0' }, 'Compartir en Mi red'),
      h('p', { class: 'muted small' }, `Se comparte una copia separada de la versión ${current.number}. Solo lo que escribas aquí; los registros de aplicación siguen privados.`),
      h('form', {
        class: 'stack',
        onsubmit: async (event) => {
          event.preventDefault();
          clear(feedback);
          if (!confirm.checked) {
            const box = errorBox('Marca la casilla de confirmación para compartir la copia.');
            feedback.appendChild(box);
            box.focus();
            return;
          }
          const shareBody = {
            versionId: current.id, confirm: true, purpose: purpose.value, description: description.value,
            observation: observation.value, improvement: improvement.value,
          };
          const experience = await write(() => api.post(`/api/sessions/${session.id}/share`,
            { ...shareBody, operationKey: operationKey(ops.share || (ops.share = {}), shareBody) }), feedback, 'compartir');
          if (experience && isCurrent()) { dropDraft(key); navigate(`/red/${experience.id}`); }
        },
      },
        h('div', { class: 'field' }, h('label', { for: 's-purpose' }, 'Propósito'), purpose),
        h('div', { class: 'field' }, h('label', { for: 's-desc' }, 'Descripción'), description),
        h('div', { class: 'field' }, h('label', { for: 's-obs' }, 'Observación que eliges compartir (opcional)'), observation),
        h('div', { class: 'field' }, h('label', { for: 's-imp' }, 'Mejora propuesta (opcional)'), improvement),
        h('label', { class: 'check', for: 's-confirm' }, confirm, 'Entiendo que se publica una copia visible para otras personas de la demostración.'),
        submit, feedback));
  }

  paint();
  return root;
}
