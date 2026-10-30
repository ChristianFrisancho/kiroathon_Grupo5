// Cliente de la API. Los errores llegan con un mensaje que el docente puede leer.

export class ApiClientError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    throw new ApiClientError('No hay conexión con el servidor. Tu trabajo sigue aquí; revisa la conexión y reintenta.', 0, 'network');
  }
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok) {
    const info = data && data.error ? data.error : {};
    throw new ApiClientError(info.message || 'No pudimos completar la acción. Intenta de nuevo.', response.status, info.code);
  }
  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body === undefined ? {} : body),
  put: (path, body) => request('PUT', path, body),
};
