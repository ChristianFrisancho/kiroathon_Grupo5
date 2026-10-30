import { api } from '../api.js';
import { announce, clear, errorBox, h } from '../util.js';

// Mi bienestar: preferencias elegidas por la persona. Todo está apagado por defecto.
export async function renderBienestar() {
  const prefs = await api.get('/api/preferences');
  const feedback = h('div', { 'aria-live': 'polite' });
  const reminders = h('input', { id: 'p-reminders', type: 'checkbox', checked: prefs.remindersEnabled });
  const time = h('input', { id: 'p-time', type: 'time' });
  time.value = prefs.reminderTime || '';
  const publicly = h('input', { id: 'p-public', type: 'checkbox', checked: prefs.sharePublicly });
  const submit = h('button', { type: 'submit', class: 'btn primary' }, 'Guardar preferencias');

  return h('div', null,
    h('h1', null, 'Mi bienestar'),
    h('p', { class: 'lead' }, 'Tú marcas tus límites. Aquí se guardan solo tus preferencias; no se envían avisos ni se publica un perfil.'),
    h('form', {
      class: 'card stack',
      onsubmit: async (event) => {
        event.preventDefault();
        submit.disabled = true;
        clear(feedback);
        try {
          await api.put('/api/preferences', {
            remindersEnabled: reminders.checked,
            reminderTime: time.value || null,
            sharePublicly: publicly.checked,
          });
          feedback.appendChild(h('p', { class: 'alert ok', role: 'status' }, 'Preferencias guardadas.'));
          announce('Preferencias guardadas');
        } catch (error) {
          feedback.appendChild(errorBox(error.message));
        }
        submit.disabled = false;
      },
    },
      h('h2', { class: 'm0' }, 'Avisos y privacidad'),
      h('label', { class: 'check', for: 'p-reminders' }, reminders, 'Quiero recibir un recordatorio para retomar mi trabajo.'),
      h('div', { class: 'field' },
        h('label', { for: 'p-time' }, 'Hora preferida ', h('span', { class: 'hint' }, 'Opcional. En esta versión solo se guarda la preferencia; no se envían avisos.')), time),
      h('label', { class: 'check', for: 'p-public' }, publicly, 'Me gustaría tener un perfil visible en Mi red (solo se guarda la preferencia: el perfil público aún no existe).'),
      submit, feedback),
    h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Cómo cuidamos tu tiempo'),
      h('ul', null,
        h('li', null, 'Pocos pasos: preparar, revisar, guardar.'),
        h('li', null, 'Qué se guarda en el servidor: tus sesiones, versiones, registros y estas preferencias.'),
        h('li', null, 'Si falla la creación o el guardado de una sesión, tu edición sigue en pantalla y en una copia local de este navegador, cuando el navegador lo permite.'),
        h('li', null, 'No publicamos nada sin tu confirmación expresa.'),
        h('li', null, 'No mostramos ahorros de horas: aún no se han medido.')),
      h('p', { class: 'muted small' }, 'La voz se usa solo para interactuar; no se usa para inferir emociones, salud ni calidad profesional.')));
}
