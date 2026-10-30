import { api, detailsList } from '../api.js';
import { setForm, setWorking, state } from '../state.js';
import { lessonSteps, setFieldError } from '../ui.js';
import { announce, clear, disableAll, errorBox, h, simBadge } from '../util.js';

// Nombres de campo que devuelve el backend en error.details.field → id del control.
const BACKEND_FIELDS = {
  grado: 'f-grade', grade: 'f-grade',
  durationMinutes: 'f-duration',
  materials: 'f-materials',
  indicaciones: 'f-notes', notes: 'f-notes',
};

const FALLBACK_CASE = {
  moduleId: 'mod-escucha-activa', grade: 'Cuarto de primaria', durationMinutes: 45,
  materials: ['pizarra', 'papel', 'lápiz'], notes: '',
};

// Mi aula · Preparar: módulo y contexto confirmados. «Crear borrador» pide el borrador al motor.
export async function renderAula({ navigate, isCurrent = () => true }) {
  const [modules, overview] = await Promise.all([api.get('/api/modules'), api.get('/api/overview')]);
  const defaults = (overview && overview.defaultCase) || FALLBACK_CASE;
  const saved = state.form || {};
  const values = {
    moduleId: modules.some((m) => m.id === saved.moduleId) ? saved.moduleId : defaults.moduleId,
    grade: saved.grade ?? defaults.grade,
    durationMinutes: saved.durationMinutes ?? defaults.durationMinutes,
    materials: saved.materials ?? defaults.materials.join(', '),
    notes: saved.notes ?? defaults.notes,
  };
  const moduleDetails = {};
  async function loadModule(id) {
    if (!moduleDetails[id]) moduleDetails[id] = await api.get(`/api/modules/${id}`);
    return moduleDetails[id];
  }
  await loadModule(values.moduleId);

  let busy = false;
  let replaceConfirmed = false;
  const feedback = h('div');
  const summary = h('aside', { class: 'card context-summary', 'aria-labelledby': 'summary-title' });
  const submit = h('button', { type: 'submit', class: 'btn primary big' }, 'Crear borrador');

  const help = (id, text) => h('span', { id, class: 'hint' }, text);
  const moduleSelect = h('select', { id: 'f-module', name: 'moduleId', value: values.moduleId },
    modules.map((m) => h('option', { value: m.id }, `${m.title} (v${m.version})`)));
  const grade = h('input', {
    id: 'f-grade', type: 'text', name: 'grade', value: values.grade, required: true, maxlength: 60,
    autocomplete: 'off', 'aria-describedby': 'h-grade',
  });
  const duration = h('input', {
    id: 'f-duration', type: 'number', name: 'durationMinutes', value: String(values.durationMinutes),
    min: 10, max: 180, step: 1, required: true, inputmode: 'numeric', 'aria-describedby': 'h-duration',
  });
  const materials = h('input', {
    id: 'f-materials', type: 'text', name: 'materials', value: values.materials, maxlength: 400,
    autocomplete: 'off', 'aria-describedby': 'h-materials',
  });
  const notes = h('textarea', { id: 'f-notes', name: 'notes', maxlength: 500, 'aria-describedby': 'h-notes' });
  notes.value = values.notes;
  const fields = { 'f-grade': grade, 'f-duration': duration, 'f-materials': materials, 'f-notes': notes };

  function read() {
    return {
      moduleId: moduleSelect.value,
      grade: grade.value,
      durationMinutes: duration.value.trim() === '' ? '' : Number(duration.value),
      materials: materials.value,
      notes: notes.value,
    };
  }

  // Validación del cliente: orienta antes de enviar; el servidor sigue siendo quien decide.
  function validate(v) {
    const problems = [];
    if (!v.grade.trim()) problems.push(['f-grade', 'Escribe el grado (por ejemplo, Cuarto de primaria).']);
    const d = v.durationMinutes;
    if (d === '' || !Number.isInteger(d) || d < 10 || d > 180) {
      problems.push(['f-duration', 'La duración debe ser un número entero de minutos entre 10 y 180.']);
    }
    if (v.notes.length > 500) problems.push(['f-notes', 'Las indicaciones admiten como máximo 500 caracteres.']);
    return problems;
  }

  function showFieldErrors(problems) {
    Object.values(fields).forEach((input) => setFieldError(input, null));
    problems.forEach(([id, message]) => fields[id] && setFieldError(fields[id], message));
    const first = problems.find(([id]) => fields[id]);
    if (first) fields[first[0]].focus();
  }

  async function paintSummary() {
    const v = read();
    const module = modules.find((m) => m.id === v.moduleId);
    let detail = moduleDetails[v.moduleId];
    clear(summary);
    summary.appendChild(h('h2', { id: 'summary-title', class: 'm0' }, 'Lo que se usará para crear el borrador'));
    summary.appendChild(h('dl', { class: 'facts' },
      h('dt', null, 'Módulo'), h('dd', null, module ? `${module.title} (versión ${module.version})` : '—'),
      h('dt', null, 'Grado'), h('dd', null, v.grade.trim() || '—'),
      h('dt', null, 'Duración'), h('dd', null, v.durationMinutes === '' ? '—' : `${v.durationMinutes} minutos`),
      h('dt', null, 'Materiales'), h('dd', null, v.materials.trim() || 'ninguno declarado'),
      h('dt', null, 'Indicaciones'), h('dd', null, v.notes.trim() || 'ninguna')));
    if (detail) {
      summary.appendChild(h('details', { class: 'fragments' },
        h('summary', null, `Ver fragmentos del módulo (${detail.fragments.length})`),
        detail.fragments.map((f) => h('div', { class: 'source' }, h('strong', null, `${f.id}. `), f.text)),
        h('p', { class: 'muted small' }, detail.sourceLabel)));
    }
    summary.appendChild(h('p', { class: 'muted small' },
      'El contenido del módulo se usa como datos de consulta, nunca como instrucciones. La pertinencia pedagógica la revisas tú.'));
    setForm({ ...v, durationMinutes: v.durationMinutes });
    if (!detail) {
      try { await loadModule(v.moduleId); if (isCurrent()) paintSummary(); } catch (e) { /* el resumen funciona sin fragmentos */ }
    }
  }

  [moduleSelect, grade, duration, materials, notes].forEach((el) => el.addEventListener('input', () => {
    if (el.getAttribute('aria-invalid') === 'true') setFieldError(el, null);
    paintSummary();
  }));

  function pendingChoice() {
    const pending = state.working;
    return h('div', { class: 'alert warn', role: 'alert', tabindex: '-1' },
      h('p', { class: 'm0' }, h('strong', null, 'Ya tienes un borrador sin guardar: '), pending.content.title),
      h('p', { class: 'small' }, 'Si creas uno nuevo, reemplazará esa copia local. Elige qué prefieres.'),
      h('div', { class: 'row' },
        h('button', { type: 'button', class: 'btn', onclick: () => navigate('/revisar') }, 'Continuar borrador'),
        h('button', {
          type: 'button', class: 'btn danger',
          onclick: () => { replaceConfirmed = true; form.requestSubmit(); },
        }, 'Reemplazar y crear borrador')));
  }

  async function create(event) {
    event.preventDefault();
    if (busy) return;
    clear(feedback);
    const payload = read();
    const problems = validate(payload);
    if (problems.length) {
      showFieldErrors(problems);
      announce('Revisa los campos marcados');
      return;
    }
    showFieldErrors([]);
    if (state.working && !replaceConfirmed) {
      const choice = pendingChoice();
      feedback.appendChild(choice);
      choice.focus();
      return;
    }
    replaceConfirmed = false;
    busy = true;
    disableAll(form, true);
    submit.textContent = 'Creando borrador…';
    feedback.appendChild(h('p', { class: 'loading', role: 'status' },
      'Creando el borrador. Puede tardar unos segundos; tus datos no se borrarán.'));
    try {
      const draft = await api.post('/api/drafts/generate', { ...payload, grade: payload.grade.trim() });
      setWorking({
        sessionId: null, moduleId: draft.module.id, context: draft.context, content: draft.content,
        draftId: draft.draftId, reviewNotes: draft.reviewNotes || [],
        generatedBy: draft.generatedBy, provenance: draft.provenance || null, reason: '',
      });
      if (isCurrent()) navigate('/revisar');
      else announce('Tu borrador está listo. Puedes abrirlo desde Hoy con «Continuar borrador».');
    } catch (error) {
      if (!isCurrent()) return;
      clear(feedback);
      const field = error.details && !Array.isArray(error.details) ? BACKEND_FIELDS[error.details.field] : null;
      if (field) showFieldErrors([[field, error.message]]);
      // La generación no guarda nada: es seguro volver a intentarlo pasando por la misma validación.
      const box = errorBox(`${error.message} Tus datos siguen en el formulario.`, () => form.requestSubmit(), detailsList(error));
      feedback.appendChild(box);
      if (!field) box.focus();
      announce('No se pudo crear el borrador');
    } finally {
      busy = false;
      disableAll(form, false);
      submit.textContent = 'Crear borrador';
    }
  }

  const form = h('form', { class: 'card stack', novalidate: true, onsubmit: create, 'aria-labelledby': 'form-title' },
    h('div', { class: 'row between' },
      h('h2', { id: 'form-title', class: 'm0' }, 'Contexto de tu clase'),
      simBadge(true, 'Caso simulado precargado')),
    h('div', { class: 'form-grid' },
      h('div', { class: 'field' }, h('label', { for: 'f-module' }, 'Módulo'), moduleSelect),
      h('div', { class: 'field' }, h('label', { for: 'f-grade' }, 'Grado'), grade,
        help('h-grade', 'Nivel y grado de tu grupo.')),
      h('div', { class: 'field' }, h('label', { for: 'f-duration' }, 'Duración en minutos'), duration,
        help('h-duration', 'Número entero entre 10 y 180.')),
      h('div', { class: 'field' }, h('label', { for: 'f-materials' }, 'Materiales'), materials,
        help('h-materials', 'Separados por comas. El borrador solo usará estos materiales.'))),
    h('div', { class: 'field' },
      h('label', { for: 'f-notes' }, 'Indicaciones (opcional)'), notes,
      help('h-notes', 'Por ejemplo: «el grupo es muy conversador». Máximo 500 caracteres.')),
    h('div', { class: 'row' }, submit,
      h('a', { class: 'btn ghost', href: '#/aprendizaje' }, 'Cambiar de módulo')));

  paintSummary();

  return h('div', null,
    lessonSteps(1),
    h('h1', null, 'Preparar clase'),
    h('p', { class: 'lead' }, 'Confirma el contexto de tu grupo. Se precargó un caso de ejemplo: puedes editar cualquier dato.'),
    state.working
      ? h('div', { class: 'alert info' },
          h('p', { class: 'm0' }, `Tienes un borrador sin guardar: «${state.working.content.title}». `),
          h('a', { href: '#/revisar' }, 'Continuar borrador'))
      : null,
    h('div', { class: 'prepare-layout' }, h('div', { class: 'stack' }, form, feedback), summary));
}
