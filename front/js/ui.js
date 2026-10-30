import { h } from './util.js';

// Indicador de avance: orienta, no añade pasos ni confirmaciones.
// «Portafolio» solo aparece completado cuando el servidor confirmó el guardado (current = 4).
export function lessonSteps(current) {
  const labels = ['Preparar', 'Revisar', 'Portafolio'];
  return h('nav', { class: 'lesson-progress', 'aria-label': 'Progreso de la sesión' },
    h('ol', { class: 'stepper' },
      labels.map((label, index) => {
        const step = index + 1;
        const active = step === current;
        const completed = step < current;
        return h('li', {
          class: ['step', active ? 'is-current' : '', completed ? 'is-complete' : ''].filter(Boolean).join(' '),
          'aria-current': active ? 'step' : null,
        },
          h('span', { class: 'step-number', 'aria-hidden': 'true' }, completed ? '✓' : String(step)),
          h('span', null, label,
            active ? h('span', { class: 'sr-only' }, ', paso actual') : null,
            completed ? h('span', { class: 'sr-only' }, ', completado') : null));
      })));
}

export function savedNotice(message) {
  return h('div', { class: 'alert ok saved-notice', role: 'status' },
    h('strong', null, message),
    h('p', { class: 'small m0' }, 'Guardado en Mi portafolio. Puedes recuperar esta sesión cuando lo necesites.'),
    h('a', { href: '#/portafolio' }, 'Volver a Mi portafolio'));
}

// Marca o limpia el error de un campo (texto visible + aria-invalid + aria-describedby).
export function setFieldError(input, message) {
  const id = `${input.id}-error`;
  const old = document.getElementById(id);
  if (old) old.remove();
  const described = (input.getAttribute('aria-describedby') || '').split(' ').filter((x) => x && x !== id);
  if (message) {
    input.setAttribute('aria-invalid', 'true');
    const error = h('p', { id, class: 'field-error' }, message);
    input.insertAdjacentElement('afterend', error);
    described.push(id);
  } else {
    input.removeAttribute('aria-invalid');
  }
  if (described.length) input.setAttribute('aria-describedby', described.join(' '));
  else input.removeAttribute('aria-describedby');
}

export function problemList(problems) {
  if (!problems.length) return null;
  return h('ul', { class: 'problem-list' }, problems.map((p) => h('li', null, p)));
}
