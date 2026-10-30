import { api } from '../api.js';
import { setWorking } from '../state.js';
import { announce, append, clear, errorBox, formatDate, h, reviewBadge, simBadge, todayIso } from '../util.js';

// Mi portafolio: lista de sesiones guardadas en el servidor.
export async function renderPortafolio() {
  const sessions = await api.get('/api/sessions');
  return h('div', null,
    h('h1', null, 'Mi portafolio'),
    h('p', { class: 'lead' }, 'Tus sesiones, versiones y registros de aplicación. Lo guardado persiste aunque recargues la página.'),
    sessions.length
      ? h('div', { class: 'card' }, h('ul', { class: 'list' }, sessions.map((s) =>
          h('li', null,
            h('div', { class: 'row between' },
              h('div', null,
                h('a', { href: `#/portafolio/${s.id}` }, s.title),
                h('p', { class: 'muted small' }, `Actualizada ${formatDate(s.updatedAt)} · ${s.versionCount} versión(es) · ${s.recordCount} registro(s)`),
                s.provenance && s.provenance.type === 'adaptacion'
                  ? h('p', { class: 'small' }, `Adaptada de «${s.provenance.title}» (${s.provenance.authorLabel})`) : null),
              h('div', { class: 'row' }, reviewBadge(s.reviewStatus), s.isShared ? h('span', { class: 'badge' }, 'Copia compartida') : null),
              h('a', { class: 'btn', href: `#/portafolio/${s.id}` }, 'Abrir'))))))
      : h('div', { class: 'card' },
          h('p', null, 'Todavía no hay sesiones guardadas.'),
          h('a', { class: 'btn primary', href: '#/aula' }, 'Preparar clase')));
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
        h('p', { class: 'muted small' }, 'Lo que se espera observar. No demuestra que la clase se haya impartido.'),
        h('p', null, c.expectedEvidence)),
      h('section', null,
        h('h3', { class: 'm0' }, 'Fuentes'),
        c.sources.map((s) => h('div', { class: 'source' }, h('strong', null, `${s.id}. `), s.text)),
        h('p', { class: 'muted small' }, c.moduleSourceLabel))));
}

// Detalle de una sesión: versiones, edición, copia, registro de aplicación y compartir.
export async function renderSesion({ params, navigate }) {
  const sessionId = params[0];
  let session = await api.get(`/api/sessions/${sessionId}`);
  const root = h('div');
  let shownVersionId = session.currentVersionId;

  function reload(next) {
    session = next;
    shownVersionId = session.currentVersionId;
    paint();
  }

  async function run(action, box) {
    clear(box);
    try {
      return await action();
    } catch (error) {
      box.appendChild(errorBox(error.message));
      announce('Hubo un error');
      return null;
    }
  }

  function paint() {
    clear(root);
    const current = session.currentVersion;
    const shown = session.versions.find((v) => v.id === shownVersionId) || current;
    const actionFeedback = h('div', { 'aria-live': 'polite' });

    const continueEdit = () => {
      setWorking({
        sessionId: session.id,
        moduleId: session.moduleId,
        context: JSON.parse(JSON.stringify(current.context)),
        content: JSON.parse(JSON.stringify(current.content)),
        generatedBy: current.generatedBy,
        provenance: session.provenance && session.provenance.type === 'adaptacion' ? session.provenance : null,
      });
      navigate('/revisar');
    };

    append(root, [
      h('h1', null, session.title),
      h('div', { class: 'row' }, reviewBadge(current.reviewStatus),
        h('span', { class: 'badge' }, `Versión ${current.number} de ${session.versions.length}`),
        current.generatedBy ? h('span', { class: 'badge sim' }, current.generatedBy.engine === 'manual' ? 'Editada por el docente' : current.generatedBy.label) : null),
      session.provenance && session.provenance.type === 'adaptacion'
        ? h('p', { class: 'alert info' }, `Adaptación de «${session.provenance.title}», compartida por ${session.provenance.authorLabel}. `,
            h('a', { href: `#/red/${session.provenance.experienceId}` }, 'Ver experiencia original'))
        : null,
      h('div', { class: 'row no-print mt' },
        h('button', { type: 'button', class: 'btn primary', onclick: continueEdit }, 'Continuar edición'),
        current.reviewStatus !== 'revisada'
          ? h('button', {
              type: 'button', class: 'btn',
              onclick: async () => {
                const next = await run(() => api.post(`/api/sessions/${session.id}/versions/${current.id}/review`), actionFeedback);
                if (next) reload(next);
              },
            }, 'Marcar como revisada') : null,
        h('button', {
          type: 'button', class: 'btn',
          onclick: async () => {
            const next = await run(() => api.post(`/api/sessions/${session.id}/copy`, {}), actionFeedback);
            if (next) navigate(`/portafolio/${next.id}`);
          },
        }, 'Crear copia'),
        h('button', {
          type: 'button', class: 'btn',
          onclick: async (e) => {
            e.target.disabled = true;
            e.target.textContent = 'Regenerando…';
            const next = await run(() => api.post(`/api/sessions/${session.id}/regenerate`, {}), actionFeedback);
            if (next) reload(next);
            else { e.target.disabled = false; e.target.textContent = 'Regenerar borrador'; }
          },
        }, 'Regenerar borrador'),
        h('button', { type: 'button', class: 'btn', onclick: () => window.print() }, 'Imprimir')),
      actionFeedback,
      h('div', { class: 'card' },
        h('div', { class: 'row between' },
          h('h2', { class: 'm0' }, `Versión ${shown.number}`), reviewBadge(shown.reviewStatus)),
        h('p', { class: 'muted small' }, `${formatDate(shown.createdAt)} · ${shown.reason || ''}`),
        contentView(shown)),
      h('div', { class: 'card no-print' },
        h('h2', { class: 'm0' }, 'Historial de versiones'),
        h('p', { class: 'muted small' }, 'Una versión nueva no borra las anteriores. Regenerar o copiar no hereda la revisión.'),
        h('ul', { class: 'list' }, [...session.versions].reverse().map((v) =>
          h('li', null,
            h('div', { class: 'row between' },
              h('span', null, `Versión ${v.number} · ${formatDate(v.createdAt)} · ${v.reason || ''}`),
              h('div', { class: 'row' }, reviewBadge(v.reviewStatus),
                h('button', {
                  type: 'button', class: 'btn', 'aria-pressed': v.id === shown.id ? 'true' : 'false',
                  onclick: () => { shownVersionId = v.id; paint(); },
                }, 'Ver')))))) ),
      recordsSection(),
      shareSection(),
    ]);
  }

  function recordsSection() {
    const feedback = h('div', { 'aria-live': 'polite' });
    const date = h('input', { id: 'r-date', type: 'date', value: todayIso(), required: true });
    const activity = h('textarea', { id: 'r-activity', required: true });
    activity.value = 'Actividad por parejas de escucha y parafraseo (texto de ejemplo: edítalo).';
    const observation = h('textarea', { id: 'r-obs', required: true });
    observation.value = 'Observación de ejemplo para la demostración: edítala con lo que realmente ocurrió.';
    const next = h('textarea', { id: 'r-next' });
    next.value = 'Dar las instrucciones en pasos más cortos (ejemplo).';
    const submit = h('button', { type: 'submit', class: 'btn primary' }, 'Guardar registro');

    const form = h('form', {
      class: 'stack',
      onsubmit: async (event) => {
        event.preventDefault();
        submit.disabled = true;
        clear(feedback);
        try {
          await api.post(`/api/sessions/${session.id}/records`, {
            versionId: session.currentVersionId,
            declaredDate: date.value,
            activity: activity.value,
            observation: observation.value,
            nextAdjustment: next.value,
          });
          reload(await api.get(`/api/sessions/${session.id}`));
          announce('Registro guardado');
        } catch (error) {
          feedback.appendChild(errorBox(error.message));
          submit.disabled = false;
        }
      },
    },
      h('div', { class: 'field' }, h('label', { for: 'r-date' }, 'Fecha declarada'), date),
      h('div', { class: 'field' }, h('label', { for: 'r-activity' }, 'Actividad realizada'), activity),
      h('div', { class: 'field' }, h('label', { for: 'r-obs' }, 'Observación declarada ', h('span', { class: 'hint' }, 'Lo que viste, según tú')), observation),
      h('div', { class: 'field' }, h('label', { for: 'r-next' }, 'Próximo ajuste'), next),
      submit, feedback);

    return h('div', { class: 'card no-print' },
      h('h2', { class: 'm0' }, 'Registros de aplicación'),
      h('p', { class: 'muted small' }, 'Opcionales. Se ligan a la versión que usaste. Un registro simulado no equivale a una clase aplicada.'),
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
      return h('div', { class: 'card no-print' },
        h('h2', { class: 'm0' }, 'Compartir en Mi red'),
        h('p', { class: 'muted' }, 'Marca la versión actual como revisada para poder compartir una copia. Tus registros privados no se publican automáticamente.'));
    }
    const feedback = h('div', { 'aria-live': 'polite' });
    const purpose = h('textarea', { id: 's-purpose', required: true });
    purpose.value = current.content.purpose;
    const description = h('textarea', { id: 's-desc', required: true });
    description.value = current.content.activities.map((a) => `${a.title} (${a.minutes} min)`).join('; ');
    const observation = h('textarea', { id: 's-obs' });
    const improvement = h('textarea', { id: 's-imp' });
    const confirm = h('input', { id: 's-confirm', type: 'checkbox' });
    const submit = h('button', { type: 'submit', class: 'btn primary' }, 'Compartir copia');
    return h('div', { class: 'card no-print' },
      h('h2', { class: 'm0' }, 'Compartir en Mi red'),
      h('p', { class: 'muted small' }, 'Se comparte una copia separada de la versión actual. Solo lo que escribas aquí; los registros de aplicación siguen privados.'),
      h('form', {
        class: 'stack',
        onsubmit: async (event) => {
          event.preventDefault();
          submit.disabled = true;
          clear(feedback);
          try {
            const experience = await api.post(`/api/sessions/${session.id}/share`, {
              versionId: current.id,
              confirm: confirm.checked,
              purpose: purpose.value,
              description: description.value,
              observation: observation.value,
              improvement: improvement.value,
            });
            navigate(`/red/${experience.id}`);
          } catch (error) {
            feedback.appendChild(errorBox(error.message));
            submit.disabled = false;
          }
        },
      },
        h('div', { class: 'field' }, h('label', { for: 's-purpose' }, 'Propósito'), purpose),
        h('div', { class: 'field' }, h('label', { for: 's-desc' }, 'Descripción'), description),
        h('div', { class: 'field' }, h('label', { for: 's-obs' }, 'Observación que eliges compartir ', h('span', { class: 'hint' }, 'Opcional')), observation),
        h('div', { class: 'field' }, h('label', { for: 's-imp' }, 'Mejora propuesta ', h('span', { class: 'hint' }, 'Opcional')), improvement),
        h('label', { class: 'check', for: 's-confirm' }, confirm, 'Entiendo que se publica una copia visible para otras personas de la demostración.'),
        submit, feedback));
  }

  paint();
  return root;
}
