import { api } from '../api.js';
import { setForm, setWorking, state } from '../state.js';
import { announce, clear, errorBox, h } from '../util.js';

// Mi aula · Preparar: módulo y contexto editable. «Crear borrador» pide el borrador al motor.
export async function renderAula({ navigate }) {
  const [modules, overview] = await Promise.all([api.get('/api/modules'), api.get('/api/overview')]);
  const defaults = overview.defaultCase;
  const saved = state.form || {};
  const values = {
    moduleId: saved.moduleId || defaults.moduleId,
    grade: saved.grade ?? defaults.grade,
    durationMinutes: saved.durationMinutes ?? defaults.durationMinutes,
    materials: saved.materials ?? defaults.materials.join(', '),
    notes: saved.notes ?? defaults.notes,
  };

  const feedback = h('div', { 'aria-live': 'polite' });
  const summary = h('div', { class: 'card' });
  const submit = h('button', { type: 'submit', class: 'btn primary big' }, 'Crear borrador');

  const moduleSelect = h('select', { id: 'f-module', name: 'moduleId', value: values.moduleId },
    modules.map((m) => h('option', { value: m.id }, `${m.title} (v${m.version})`)));
  const grade = h('input', { id: 'f-grade', type: 'text', name: 'grade', value: values.grade, required: true, maxlength: 60 });
  const duration = h('input', { id: 'f-duration', type: 'number', name: 'durationMinutes', value: values.durationMinutes, min: 10, max: 180, required: true });
  const materials = h('input', { id: 'f-materials', type: 'text', name: 'materials', value: values.materials, maxlength: 400 });
  const notes = h('textarea', { id: 'f-notes', name: 'notes', maxlength: 500 }, '');
  notes.value = values.notes;

  function read() {
    return {
      moduleId: moduleSelect.value,
      grade: grade.value,
      durationMinutes: duration.value === '' ? '' : Number(duration.value),
      materials: materials.value,
      notes: notes.value,
    };
  }

  function paintSummary() {
    const v = read();
    const module = modules.find((m) => m.id === v.moduleId);
    clear(summary);
    summary.appendChild(h('h2', { class: 'm0' }, 'Lo que se usará para crear el borrador'));
    summary.appendChild(h('ul', null,
      h('li', null, `Módulo: ${module ? module.title : '—'} (v${module ? module.version : ''})`),
      h('li', null, `Grado: ${v.grade || '—'}`),
      h('li', null, `Duración: ${v.durationMinutes || '—'} minutos`),
      h('li', null, `Materiales: ${v.materials || 'ninguno declarado'}`),
      h('li', null, `Indicaciones: ${v.notes || 'ninguna'}`)));
    summary.appendChild(h('p', { class: 'muted small' },
      'El contenido del módulo se trata como datos de consulta, nunca como instrucciones. La pertinencia pedagógica la revisas tú.'));
    setForm(v);
  }

  [moduleSelect, grade, duration, materials, notes].forEach((el) => el.addEventListener('input', paintSummary));

  async function create(event) {
    if (event) event.preventDefault();
    clear(feedback);
    submit.disabled = true;
    submit.textContent = 'Creando borrador…';
    feedback.appendChild(h('p', { class: 'loading', role: 'status' }, 'Esto puede tardar unos segundos. Tus datos no se borrarán.'));
    announce('Creando borrador');
    try {
      const draft = await api.post('/api/drafts/generate', read());
      setWorking({
        sessionId: null,
        moduleId: draft.module.id,
        context: draft.context,
        content: draft.content,
        generatedBy: draft.generatedBy,
        provenance: null,
      });
      navigate('/revisar');
    } catch (error) {
      clear(feedback);
      feedback.appendChild(errorBox(error.message, () => create()));
      announce('No se pudo crear el borrador');
    } finally {
      submit.disabled = false;
      submit.textContent = 'Crear borrador';
    }
  }

  paintSummary();

  const form = h('form', { class: 'card', novalidate: false, onsubmit: create },
    h('div', { class: 'form-grid' },
      h('div', { class: 'field' }, h('label', { for: 'f-module' }, 'Módulo'), moduleSelect),
      h('div', { class: 'field' }, h('label', { for: 'f-grade' }, 'Grado'), grade),
      h('div', { class: 'field' }, h('label', { for: 'f-duration' }, 'Duración en minutos'), duration),
      h('div', { class: 'field' },
        h('label', { for: 'f-materials' }, 'Materiales ', h('span', { class: 'hint' }, 'Separados por comas')), materials)),
    h('div', { class: 'field' },
      h('label', { for: 'f-notes' }, 'Indicaciones ', h('span', { class: 'hint' }, 'Opcional')), notes),
    h('div', { class: 'row' }, submit,
      h('a', { class: 'btn', href: '#/aprendizaje' }, 'Cambiar de módulo')));

  return h('div', null,
    h('h1', null, 'Mi aula · Preparar clase'),
    h('p', { class: 'lead' }, 'Confirma el contexto de tu grupo. Se precargó el caso de ejemplo: puedes editar cualquier dato.'),
    form, feedback, summary);
}
