import { api } from '../api.js';
import { localCopyAvailable, state } from '../state.js';
import { clear, errorBox, formatDate, h, reviewBadge } from '../util.js';

// Hoy + Mi tiempo. La orientación y «Preparar clase» se muestran de inmediato;
// solo las sesiones recientes dependen de la API.
export async function renderHoy({ navigate, isCurrent = () => true }) {
  const recentBox = h('div', { class: 'card', 'aria-busy': 'true' },
    h('p', { class: 'loading' }, 'Cargando sesiones recientes…'));
  const engineNote = h('p', { class: 'muted small' });
  const pending = state.working;

  const page = h('div', { class: 'home-page' },
    h('section', { class: 'hero', 'aria-labelledby': 'home-title' },
      h('p', { class: 'eyebrow' }, 'Copiloto del docente público'),
      h('h1', { id: 'home-title' }, 'Tu próxima clase empieza aquí'),
      h('p', { class: 'lead' },
        'Transforma un módulo en una sesión para tu grupo, tu tiempo y tus materiales. '
        + 'Revísala, guárdala y recupérala cuando lo necesites.'),
      h('div', { class: 'row' },
        h('a', { class: 'btn primary big', href: '#/aula' }, 'Preparar clase'),
        h('a', { class: 'btn', href: '#/portafolio' }, 'Mi portafolio')),
      h('ol', { class: 'how-steps' },
        h('li', null, h('strong', null, 'Preparar: '), 'confirma grado, minutos y materiales.'),
        h('li', null, h('strong', null, 'Revisar: '), 'corrige el borrador; tú decides la versión.'),
        h('li', null, h('strong', null, 'Portafolio: '), 'recupera tu sesión y registra cómo te fue.')),
      h('p', { class: 'muted small m0' }, 'La IA prepara; tú decides. Demostración con datos simulados.')),
    state.discardedCorrupt
      ? h('p', { class: 'alert warn' }, 'Encontramos una copia local dañada en este navegador y no pudimos usarla.')
      : null,
    pending
      ? h('section', { class: 'alert info', 'aria-labelledby': 'pending-title' },
          h('h2', { id: 'pending-title', class: 'm0' }, 'Tienes cambios pendientes de guardar'),
          h('p', null, pending.content.title),
          h('p', { class: 'small' }, localCopyAvailable()
            ? 'Copia local en este navegador: todavía no está guardada en tu portafolio.'
            : 'Copia solo en esta pestaña: el navegador no permite guardar copias locales.'),
          h('button', { type: 'button', class: 'btn', onclick: () => navigate('/revisar') }, 'Continuar borrador'))
      : null,
    h('section', { 'aria-labelledby': 'recent-title' },
      h('div', { class: 'row between' },
        h('h2', { id: 'recent-title' }, 'Tus sesiones recientes'),
        h('a', { href: '#/portafolio' }, 'Ver mi portafolio')),
      recentBox),
    engineNote);

  async function loadRecent() {
    recentBox.setAttribute('aria-busy', 'true');
    clear(recentBox);
    recentBox.appendChild(h('p', { class: 'loading' }, 'Cargando sesiones recientes…'));
    try {
      const overview = await api.get('/api/overview');
      if (!isCurrent()) return;
      if (!overview || !Array.isArray(overview.recentSessions)) {
        throw new Error('No pudimos interpretar las sesiones recientes.');
      }
      clear(recentBox);
      if (overview.recentSessions.length === 0) {
        recentBox.appendChild(h('div', { class: 'empty-state' },
          h('h3', { class: 'm0' }, 'Tu portafolio empieza con una clase'),
          h('p', null, 'Prepara una sesión y guárdala para encontrarla aquí.'),
          h('a', { class: 'btn', href: '#/aula' }, 'Preparar clase')));
      } else {
        recentBox.appendChild(h('ul', { class: 'list' }, overview.recentSessions.map((s) =>
          h('li', null,
            h('div', { class: 'row between' },
              h('div', { class: 'grow' },
                h('a', { class: 'session-title', href: `#/portafolio/${s.id}` }, s.title),
                h('p', { class: 'muted small m0' },
                  `Actualizada ${formatDate(s.updatedAt)} · versión ${s.currentVersionNumber}`)),
              reviewBadge(s.reviewStatus))))));
      }
      const generator = overview.generator;
      engineNote.textContent = generator ? `Origen de los borradores: ${generator.label}` : '';
    } catch (error) {
      if (!isCurrent()) return;
      clear(recentBox);
      recentBox.appendChild(errorBox(error.message || 'No pudimos cargar tus sesiones.', loadRecent));
    } finally {
      if (isCurrent()) recentBox.setAttribute('aria-busy', 'false');
    }
  }

  void loadRecent();
  return page;
}
