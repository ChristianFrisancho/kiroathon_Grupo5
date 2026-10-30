import { api } from '../api.js';
import { state } from '../state.js';
import { formatDate, h, reviewBadge } from '../util.js';

// Hoy + Mi tiempo: portada mínima para preparar o retomar el trabajo.
export async function renderHoy({ navigate }) {
  const overview = await api.get('/api/overview');
  const pending = state.working;

  const recent = overview.recentSessions.length
    ? h('ul', { class: 'list' }, overview.recentSessions.map((s) =>
        h('li', null,
          h('div', { class: 'row between' },
            h('div', null,
              h('a', { href: `#/portafolio/${s.id}` }, s.title),
              h('p', { class: 'muted small' }, `Actualizada ${formatDate(s.updatedAt)} · versión ${s.currentVersionNumber}`)),
            h('div', { class: 'row' }, reviewBadge(s.reviewStatus),
              s.recordCount ? h('span', { class: 'badge sim' }, `${s.recordCount} registro(s)`) : null)))))
    : h('p', { class: 'muted' }, 'Aún no tienes sesiones guardadas. Prepara tu primera clase.');

  return h('div', null,
    h('h1', null, 'Hola, profe: ¿qué quieres hacer hoy?'),
    h('p', { class: 'lead' }, 'Convierte un módulo en una clase para tu grupo, revísala y guarda tu trabajo. Tú decides cada paso.'),
    h('div', { class: 'grid' },
      h('div', { class: 'card highlight stack' },
        h('h2', null, 'Mi aula'),
        h('p', null, 'Crea un borrador de sesión con tu grado, tiempo y materiales.'),
        h('a', { class: 'btn primary big', href: '#/aula' }, 'Preparar clase')),
      h('div', { class: 'card stack' },
        h('h2', null, 'Mi portafolio'),
        h('p', null, 'Recupera tus sesiones, continúa editando y añade registros de aplicación.'),
        h('a', { class: 'btn big', href: '#/portafolio' }, 'Mi portafolio'))),
    pending
      ? h('div', { class: 'alert info' },
          h('p', null, `Tienes un borrador sin guardar: «${pending.content.title}». Es una copia de trabajo local; aún no está en tu portafolio.`),
          h('button', { type: 'button', class: 'btn', onclick: () => navigate('/revisar') }, 'Continuar borrador'))
      : null,
    h('h2', null, 'Mi tiempo · sesiones recientes'),
    h('div', { class: 'card' }, recent),
    h('p', { class: 'muted small' },
      overview.generator.isBedrock
        ? 'Los borradores se generan con Amazon Bedrock.'
        : `Motor de borradores en esta versión: ${overview.generator.label}`));
}
