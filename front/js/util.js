// Utilidades de interfaz. Todo texto dinámico entra como nodo de texto: nunca como HTML.

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  let value;
  for (const [key, val] of Object.entries(attrs || {})) {
    if (val === null || val === undefined || val === false) continue;
    if (key === 'class') el.className = val;
    else if (key === 'value') value = val;
    else if (key === 'checked') el.checked = Boolean(val);
    else if (key.startsWith('on') && typeof val === 'function') el.addEventListener(key.slice(2).toLowerCase(), val);
    else if (val === true) el.setAttribute(key, '');
    else el.setAttribute(key, String(val));
  }
  append(el, children);
  if (value !== undefined) el.value = value;
  return el;
}

export function append(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    parent.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return parent;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function announce(message) {
  const region = document.getElementById('status');
  if (region) region.textContent = message;
}

export function formatScore(value) {
  return value === null || value === undefined ? '' : Number(value).toFixed(1).replace('.', ',');
}

export function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso);
  return date.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
}

export function todayIso() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function ratingLine(summary, isSimulated) {
  if (!summary || summary.completeCount === 0) {
    const partial = summary && summary.partialCount ? ` · ${summary.partialCount} parciales` : '';
    return `Sin valoración general${partial}`;
  }
  const parts = [`${formatScore(summary.average)}/5`, `${summary.completeCount} valoraciones completas`];
  if (summary.partialCount) parts.push(`${summary.partialCount} parciales`);
  if (summary.label) parts.push(summary.label);
  if (isSimulated) parts.push('Datos simulados');
  return parts.join(' · ');
}

// Caja de error. `onRetry` solo para lecturas o generaciones sin persistir: nunca para escrituras.
export function errorBox(message, onRetry, problems = []) {
  return h('div', { class: 'alert error', role: 'alert', tabindex: '-1' },
    h('p', { class: 'm0' }, h('strong', null, 'Error: '), message),
    problems.length ? h('ul', { class: 'problem-list' }, problems.map((p) => h('li', null, p))) : null,
    onRetry ? h('button', { type: 'button', class: 'btn', onclick: onRetry }, 'Reintentar') : null);
}

export function reviewBadge(status) {
  return status === 'revisada'
    ? h('span', { class: 'badge ok' }, 'Revisada')
    : h('span', { class: 'badge draft' }, 'Borrador');
}

// Origen del borrador declarado por el servidor (Bedrock, respaldo local, plantilla o docente).
export function originBadges(version) {
  if (!version) return [];
  return [engineBadge(version.generatedBy),
    version.editedByTeacher && version.generatedBy && version.generatedBy.engine !== 'manual'
      ? h('span', { class: 'badge' }, 'Editada por el docente') : null];
}

export function engineBadge(generatedBy) {
  if (!generatedBy) return null;
  if (generatedBy.engine === 'manual') return h('span', { class: 'badge' }, 'Editada por el docente');
  if (generatedBy.isBedrock) return h('span', { class: 'badge ai' }, 'Amazon Bedrock');
  if (generatedBy.engine === 'local-respaldo') return h('span', { class: 'badge draft' }, 'Respaldo local');
  return h('span', { class: 'badge' }, 'Plantilla local');
}

export function disableAll(container, disabled) {
  container.querySelectorAll('input, select, textarea, button').forEach((el) => {
    if (disabled) {
      if (!el.disabled) { el.dataset.lockedByOp = '1'; el.disabled = true; }
    } else if (el.dataset.lockedByOp) {
      delete el.dataset.lockedByOp;
      el.disabled = false;
    }
  });
}

export function simBadge(isSimulated, text = 'Datos simulados') {
  return isSimulated ? h('span', { class: 'badge sim' }, text) : null;
}
