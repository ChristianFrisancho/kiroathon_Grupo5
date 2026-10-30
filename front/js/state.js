// Copias locales de trabajo en curso. Solo sirven para detenerse y retomar en este navegador:
// lo que cuenta como «Guardado en Mi portafolio» vive en el servidor.
// Se tocan únicamente claves que empiezan por «aulalista.».

const WORKING_KEY = 'aulalista.working';
const FORM_KEY = 'aulalista.form';
const DRAFT_PREFIX = 'aulalista.draft.';

let storageOk = true;

function read(key) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    storageOk = false;
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null || value === undefined) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
    storageOk = true;
  } catch (error) {
    storageOk = false; // almacenamiento deshabilitado o lleno: el flujo sigue en memoria
  }
  return storageOk;
}

const isText = (v) => typeof v === 'string';

// JSON válido no implica borrador válido: se comprueba la estructura mínima.
export function isValidWorking(w) {
  if (!w || typeof w !== 'object') return false;
  const c = w.content;
  const ctx = w.context;
  return isText(w.moduleId)
    && ctx && typeof ctx === 'object' && isText(ctx.grade) && Array.isArray(ctx.materials)
    && c && typeof c === 'object' && isText(c.title) && isText(c.purpose) && isText(c.expectedEvidence)
    && Array.isArray(c.materials) && Array.isArray(c.activities)
    && c.activities.every((a) => a && isText(a.title) && isText(a.description) && Array.isArray(a.references))
    && (w.sessionId === null || w.sessionId === undefined || isText(w.sessionId));
}

function isValidForm(f) {
  return f && typeof f === 'object' && ['moduleId', 'grade', 'materials', 'notes']
    .every((k) => f[k] === undefined || isText(f[k]));
}

function load() {
  const working = read(WORKING_KEY);
  const form = read(FORM_KEY);
  const result = {
    working: isValidWorking(working) ? { reason: '', ...working } : null,
    form: isValidForm(form) ? form : null,
    discardedCorrupt: Boolean(working) && !isValidWorking(working),
  };
  if (result.discardedCorrupt) write(WORKING_KEY, null);
  return result;
}

const initial = load();

export const state = {
  working: initial.working,
  form: initial.form,
  discardedCorrupt: initial.discardedCorrupt,
};

// true si la última escritura local funcionó: solo entonces se promete recuperar tras recargar.
export function localCopyAvailable() {
  return storageOk;
}

export function setWorking(working) {
  state.working = working ? { reason: '', ...working } : null;
  return write(WORKING_KEY, state.working);
}

export function persistWorking() {
  return write(WORKING_KEY, state.working);
}

export function clearWorking() {
  state.working = null;
  write(WORKING_KEY, null);
}

export function setForm(form) {
  state.form = form;
  return write(FORM_KEY, form);
}

// Borradores de formularios ligados a una sesión y una versión concretas (registro, compartir).
export function draftKey(kind, sessionId, versionId) {
  return `${DRAFT_PREFIX}${kind}.${sessionId}.${versionId || 'actual'}`;
}

export function readDraft(key) {
  const value = read(key);
  return value && typeof value === 'object' ? value : null;
}

export function writeDraft(key, value) {
  return write(key, value);
}

export function clearDraft(key) {
  write(key, null);
}

// Mensaje de una sola lectura para mostrar en la vista siguiente (p. ej. confirmación de guardado).
let flash = null;
export function setFlash(message) { flash = message; }
export function takeFlash() { const m = flash; flash = null; return m; }
