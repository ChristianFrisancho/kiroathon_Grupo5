import { api } from '../api.js';
import { setForm, state } from '../state.js';
import { h, simBadge } from '../util.js';

// Mi aprendizaje: el módulo con su fuente y fragmentos. «Usar en mi clase» lo lleva a Mi aula.
export async function renderAprendizaje({ navigate }) {
  const summaries = await api.get('/api/modules');
  const modules = await Promise.all(summaries.map((m) => api.get(`/api/modules/${m.id}`)));

  return h('div', null,
    h('div', { class: 'row between' },
      h('h1', { class: 'm0' }, 'Mi aprendizaje'),
      h('button', {
        type: 'button', class: 'btn primary',
        onclick: () => navigate('/aprendizaje/nuevo'),
      }, '+ Agregar módulo')),
    h('p', { class: 'lead' }, 'Elige el contenido de formación que quieres convertir en una clase. Generar una clase no significa haber completado o aprobado un curso.'),
    modules.map((module) =>
      h('article', { class: 'card highlight' },
        h('div', { class: 'row between' },
          h('h2', { class: 'm0' }, module.title),
          h('div', { class: 'row' }, h('span', { class: 'badge' }, `Versión ${module.version}`), simBadge(module.isSimulated))),
        h('p', { class: 'muted' }, `Fuente: ${module.sourceLabel}`),
        h('h3', null, 'Fragmentos del módulo'),
        module.fragments.map((f) =>
          h('div', { class: 'source' }, h('strong', null, `${f.id}. `), f.text)),
        h('div', { class: 'row mt' },
          h('button', {
            type: 'button', class: 'btn primary',
            onclick: () => {
              setForm({ ...(state.form || {}), moduleId: module.id });
              navigate('/aula');
            },
          }, 'Usar en mi clase')))),
    h('p', { class: 'muted small' }, 'Las consultas explicativas y las rutas de formación son una evolución futura.'));
}
