// Cliente HTTP del mismo origen. Tiempo máximo de espera del lado del navegador y errores legibles.
// Abortar la espera NO cancela el trabajo del servidor: por eso una escritura sin confirmación queda
// marcada como `outcomeUnknown` y nunca se reintenta automáticamente.

export class ApiClientError extends Error {
  constructor(message, status = 0, code = 'unknown', details = null) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.outcomeUnknown = false;
  }
}

// Límites del cliente. La API Gateway corta a los 30 s y la Lambda a los 29 s; la generación con
// Bedrock tarda unos 2-5 s en la cuenta del evento.
const TIMEOUTS = { generate: 35000, write: 20000, read: 12000 };

function isGeneration(path) {
  return /\/(generate|regenerate|adapt)$/.test(path) || /\/summary$/.test(path);
}

async function request(method, path, body, options = {}) {
  const writing = method !== 'GET';
  const timeoutMs = options.timeoutMs
    ?? (isGeneration(path) ? TIMEOUTS.generate : writing ? TIMEOUTS.write : TIMEOUTS.read);
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response;
    try {
      response = await fetch(path, {
        method,
        credentials: 'same-origin',
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      const timedOut = controller.signal.aborted;
      const result = new ApiClientError(
        timedOut ? 'La respuesta está tardando más de lo esperado.' : 'No hay conexión con el servidor.',
        0, timedOut ? 'timeout' : 'network');
      result.outcomeUnknown = writing;
      throw result;
    }

    let data = null;
    const type = response.headers.get('Content-Type') || '';
    if (type.includes('application/json')) {
      try {
        data = await response.json();
      } catch (error) {
        data = null;
      }
    }

    if (!response.ok) {
      const info = data && data.error ? data.error : null;
      const result = new ApiClientError(
        (info && info.message) || 'El servidor no pudo completar la acción. Intenta nuevamente.',
        response.status, (info && info.code) || 'http_error', info ? (info.details ?? null) : null);
      // Sin cuerpo JSON (p. ej. 502/504 del balanceador) no sabemos si la escritura se aplicó.
      result.outcomeUnknown = writing && !info && response.status >= 500;
      throw result;
    }
    if (data === null) {
      const result = new ApiClientError('Recibimos una respuesta inesperada del servidor.', response.status, 'invalid_response');
      result.outcomeUnknown = writing;
      throw result;
    }
    return data;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  get: (path, options) => request('GET', path, undefined, options),
  post: (path, body = {}, options) => request('POST', path, body, options),
  put: (path, body, options) => request('PUT', path, body, options),
};

// Mensaje para escrituras: distingue «falló» de «no sabemos si se guardó».
export function writeErrorMessage(error, what = 'guardar') {
  if (error && error.outcomeUnknown) {
    return 'No recibimos la confirmación. Revisa Mi portafolio antes de volver a guardar para evitar duplicados.';
  }
  return (error && error.message) || `No pudimos ${what}.`;
}

// Resumen legible de `details` (lista de problemas o {field}). Nunca imprime JSON.
export function detailsList(error) {
  const details = error && error.details;
  if (Array.isArray(details)) return details.filter((d) => typeof d === 'string');
  return [];
}
