import { h } from '../util.js';

// Mis oportunidades: función futura. No hay formularios ni transacciones en esta versión.
export async function renderOportunidades() {
  return h('div', null,
    h('h1', null, 'Mis oportunidades'),
    h('div', { class: 'alert warn' },
      h('strong', null, 'Función futura. '), 'No está disponible en esta versión: no se publican ofertas ni se procesan pagos o reservas.'),
    h('p', { class: 'lead' }, 'La idea es que una persona que enseña pueda ofrecer, de forma voluntaria, recursos originales, mentorías o talleres.'),
    h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Qué describiría una oferta'),
      h('ul', null,
        h('li', null, 'Destinatarios y contenido.'),
        h('li', null, 'Modalidad, duración y disponibilidad.'),
        h('li', null, 'Precio elegido por la persona que ofrece.'))),
    h('div', { class: 'card' },
      h('h2', { class: 'm0' }, 'Principios'),
      h('ul', null,
        h('li', null, 'La IA ayudaría a redactar y a encontrar solicitudes compatibles; la persona decide publicar y aceptar.'),
        h('li', null, 'Publicar una oferta no equivale a ingresar dinero.'),
        h('li', null, 'Los materiales de otras personas no se convierten automáticamente en vendibles.'),
        h('li', null, 'Derechos de uso, reservas, pagos, cancelaciones y atención requieren desarrollo propio.'))));
}
