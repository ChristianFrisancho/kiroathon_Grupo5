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
  { nav: 'hoy', re: /^\/hoy$/, view: renderHoy },
  { nav: 'aprendizaje', re: /^\/aprendizaje$/, view: renderAprendizaje },
  { nav: 'aula', re: /^\/aula$/, view: renderAula },
  { nav: 'aula', re: /^\/revisar$/, view: renderRevisar },
  { nav: 'portafolio', re: /^\/portafolio$/, view: renderPortafolio },
  { nav: 'portafolio', re: /^\/portafolio\/([\w-]+)$/, view: renderSesion },
  { nav: 'red', re: /^\/red$/, view: renderRed },
  { nav: 'red', re: /^\/red\/([\w-]+)$/, view: renderExperiencia },
  { nav: 'oportunidades', re: /^\/oportunidades$/, view: renderOportunidades },
  { nav: 'bienestar', re: /^\/bienestar$/, view: renderBienestar },
];

const root = document.getElementById('app');
let renderToken = 0;

export function navigate(path) {
  if (window.location.hash === `#${path}`) render();
  else window.location.hash = path;
}

function currentPath() {
  const hash = window.location.hash.replace(/^#/, '');
  return hash || '/hoy';
}

async function render() {
  const token = ++renderToken;
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
    root.appendChild(h('h1', null, 'No encontramos esa página'));
    root.appendChild(h('a', { class: 'btn primary', href: '#/hoy' }, 'Volver a Hoy'));
    return;
  }
  root.appendChild(h('p', { class: 'loading' }, 'Cargando…'));
  try {
    const content = await match.route.view({ params: match.params, navigate });
    if (token !== renderToken) return; // otra navegación ganó
    clear(root);
    root.appendChild(content);
  } catch (error) {
    if (token !== renderToken) return;
    clear(root);
    root.appendChild(h('h1', null, 'Algo no salió bien'));
    root.appendChild(errorBox(error.message || 'No pudimos cargar esta página.', render));
  }
  const heading = root.querySelector('h1');
  if (heading) {
    heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
    announce(heading.textContent);
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', render);
render();
