import { announce, clear, errorBox, h } from './util.js';
import { renderHoy } from './views/hoy.js';
import { renderAprendizaje } from './views/aprendizaje.js';
import { renderAula } from './views/aula.js';
import { renderRevisar } from './views/revisar.js';
import { renderPortafolio, renderSesion } from './views/portafolio.js';
import { renderRed, renderExperiencia } from './views/red.js';
import { renderOportunidades } from './views/oportunidades.js';
import { renderBienestar } from './views/bienestar.js';

const ROUTES = [
  { nav: 'hoy', re: /^\/hoy$/, view: renderHoy, title: 'Hoy' },
  { nav: 'aprendizaje', re: /^\/aprendizaje$/, view: renderAprendizaje, title: 'Mi aprendizaje' },
  { nav: 'aula', re: /^\/aula$/, view: renderAula, title: 'Preparar clase' },
  { nav: 'aula', re: /^\/revisar$/, view: renderRevisar, title: 'Revisar el borrador' },
  { nav: 'portafolio', re: /^\/portafolio$/, view: renderPortafolio, title: 'Mi portafolio' },
  { nav: 'portafolio', re: /^\/portafolio\/([\w-]+)$/, view: renderSesion, title: 'Sesión' },
  { nav: 'red', re: /^\/red$/, view: renderRed, title: 'Mi red' },
  { nav: 'red', re: /^\/red\/([\w-]+)$/, view: renderExperiencia, title: 'Experiencia' },
  { nav: 'oportunidades', re: /^\/oportunidades$/, view: renderOportunidades, title: 'Mis oportunidades' },
  { nav: 'bienestar', re: /^\/bienestar$/, view: renderBienestar, title: 'Mi bienestar' },
];

const APP_NAME = 'Docente Presente';
const root = document.getElementById('app');
let renderToken = 0;
let firstRender = true; // en la carga inicial el foco queda al principio (skip-link)

export function navigate(path) {
  if (window.location.hash === `#${path}`) render();
  else window.location.hash = path;
}

function currentPath() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash || '/hoy';
}

function setTitle(text) {
  document.title = text ? `${text} · ${APP_NAME}` : APP_NAME;
}

function focusHeading() {
  const heading = root.querySelector('h1');
  if (!heading) return;
  if (firstRender) { firstRender = false; return; }
  heading.setAttribute('tabindex', '-1');
  heading.focus({ preventScroll: true });
  announce(heading.textContent);
}

async function render() {
  const token = ++renderToken;
  const isCurrent = () => token === renderToken;
  const path = currentPath();
  let match = null;
  for (const route of ROUTES) {
    const found = route.re.exec(path);
    if (found) {
      match = { route, params: found.slice(1) };
      break;
    }
  }
  document.querySelectorAll('[data-nav]').forEach((link) => {
    if (match && link.dataset.nav === match.route.nav) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  clear(root);
  if (!match) {
    setTitle('Página no encontrada');
    root.appendChild(h('div', { class: 'card stack' },
      h('h1', null, 'No encontramos esa página'),
      h('p', null, 'La dirección no corresponde a ninguna sección de Docente Presente.'),
      h('a', { class: 'btn primary', href: '#/hoy' }, 'Volver a Hoy')));
    focusHeading();
    return;
  }
  setTitle(match.route.title);
  root.setAttribute('aria-busy', 'true');
  root.appendChild(h('p', { class: 'loading' }, 'Cargando…'));
  try {
    const content = await match.route.view({ params: match.params, navigate, isCurrent, setTitle });
    if (!isCurrent()) return; // otra navegación ganó
    clear(root);
    root.appendChild(content);
  } catch (error) {
    if (!isCurrent()) return;
    clear(root);
    root.appendChild(h('div', { class: 'stack' },
      h('h1', null, 'No pudimos abrir esta pantalla'),
      errorBox(error.message || 'No pudimos cargar esta página.', render),
      h('a', { class: 'btn', href: '#/hoy' }, 'Volver a Hoy')));
  } finally {
    if (isCurrent()) root.setAttribute('aria-busy', 'false');
  }
  if (!isCurrent()) return;
  // La confirmación de guardado (.saved-notice, role=status) se anuncia sola: aquí solo el título.
  focusHeading();
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', render);
render();
