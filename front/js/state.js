// Estado de trabajo en curso. Es solo una copia local para poder detenerse y retomar:
// lo que cuenta como guardado vive en el servidor (portafolio).

const WORKING_KEY = 'aulalista.working';
const FORM_KEY = 'aulalista.form';

function read(key) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    /* sin almacenamiento local: el flujo sigue funcionando sin retomar */
  }
}

export const state = {
  working: read(WORKING_KEY),
  form: read(FORM_KEY),
};

export function setWorking(working) {
  state.working = working;
  write(WORKING_KEY, working);
}

export function persistWorking() {
  write(WORKING_KEY, state.working);
}

export function clearWorking() {
  state.working = null;
  write(WORKING_KEY, null);
}

export function setForm(form) {
  state.form = form;
  write(FORM_KEY, form);
}
