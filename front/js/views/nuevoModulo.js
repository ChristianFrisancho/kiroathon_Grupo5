import { h, announce } from '../util.js';

// Mi aprendizaje · Agregar módulo (maqueta visual).
// Formulario de título + fragmentos con validación en el cliente. Aún no persiste: al enviar
// solo muestra un aviso de «próximamente». No toca la API ni los contratos públicos.
export async function renderNuevoModulo({ navigate }) {
  const fragments = [
    { id: 'M1', text: '' },
    { id: 'M2', text: '' },
  ];

  const errorBox = h('div', { class: 'alert error', role: 'alert', tabindex: '-1', hidden: true });
  const okBox = h('div', { class: 'alert', role: 'status', tabindex: '-1', hidden: true });

  const title = h('input', {
    id: 'nm-title', type: 'text', maxlength: 90, autocomplete: 'off',
    placeholder: 'Por ejemplo: Escucha activa y diálogo respetuoso',
  });

  const fragmentsBox = h('div', { class: 'stack' });

  function nextId() {
    return `M${fragments.length + 1}`;
  }

  function paintFragments() {
    fragmentsBox.replaceChildren();
    fragments.forEach((fragment, index) => {
      const area = h('textarea', {
        id: `nm-frag-${index}`, rows: 3, maxlength: 600,
        placeholder: 'Describe esta parte del contenido del módulo.',
        oninput: (e) => { fragment.text = e.target.value; hideMessages(); },
      });
      area.value = fragment.text;
      fragmentsBox.appendChild(h('div', { class: 'field' },
        h('div', { class: 'row between' },
          h('label', { for: `nm-frag-${index}` }, `Fragmento ${fragment.id}`),
          h('button', {
            type: 'button', class: 'btn ghost danger', disabled: fragments.length <= 1,
            onclick: () => {
              fragments.splice(index, 1);
              fragments.forEach((f, i) => { f.id = `M${i + 1}`; });
              hideMessages();
              paintFragments();
            },
          }, 'Quitar')),
        area));
    });
  }

  function hideMessages() {
    errorBox.hidden = true;
    okBox.hidden = true;
  }

  function showError(message) {
    okBox.hidden = true;
    errorBox.replaceChildren(h('p', { class: 'm0' }, h('strong', null, 'Error: '), message));
    errorBox.hidden = false;
    errorBox.focus();
  }

  const addFragmentBtn = h('button', {
    type: 'button', class: 'btn',
    onclick: () => {
      if (fragments.length >= 8) { showError('Máximo 8 fragmentos por módulo.'); return; }
      fragments.push({ id: nextId(), text: '' });
      hideMessages();
      paintFragments();
    },
  }, '+ Agregar fragmento');

  const submit = h('button', {
    type: 'submit', class: 'btn primary',
  }, 'Guardar módulo');

  const form = h('form', {
    novalidate: true,
    onsubmit: (e) => {
      e.preventDefault();
      hideMessages();
      const problems = [];
      if (!title.value.trim()) problems.push('Escribe un título para el módulo.');
      fragments.forEach((f) => {
        if (!f.text.trim()) problems.push(`El fragmento ${f.id} está vacío.`);
      });
      if (problems.length) {
        showError(problems.join(' '));
        return;
      }
      // Maqueta visual: todavía no persiste. Avisamos con claridad.
      errorBox.hidden = true;
      okBox.replaceChildren(
        h('p', { class: 'm0' },
          h('strong', null, 'Vista previa lista. '),
          'Guardar módulos propios es una función en construcción: por ahora este formulario no almacena el contenido. Pronto podrás crear tus propios módulos.'));
      okBox.hidden = false;
      okBox.focus();
      announce('Vista previa del módulo lista. La función de guardado está en construcción.');
    },
  },
    h('div', { class: 'field' },
      h('label', { for: 'nm-title' }, 'Título del módulo'),
      title,
      h('span', { class: 'hint' }, 'Máximo 90 caracteres.')),
    h('h2', { class: 'm0 mt' }, 'Fragmentos del módulo'),
    h('p', { class: 'muted small' }, 'Cada fragmento es una parte del contenido (M1, M2, M3…) que luego se cita en las actividades de la clase.'),
    fragmentsBox,
    h('div', { class: 'row mt' }, addFragmentBtn),
    h('div', { class: 'row mt' }, submit,
      h('button', { type: 'button', class: 'btn ghost', onclick: () => navigate('/aprendizaje') }, 'Cancelar')));

  paintFragments();

  return h('div', null,
    h('h1', null, 'Agregar módulo'),
    h('p', { class: 'lead' }, 'Crea un contenido de formación propio con sus fragmentos para convertirlo en clases.'),
    errorBox,
    okBox,
    h('div', { class: 'card' },
      h('p', { class: 'muted small' }, 'Los módulos propios se rotularán como datos simulados: no son currículo oficial ni un curso identificado de APRENDE PERÚ.'),
      form));
}
