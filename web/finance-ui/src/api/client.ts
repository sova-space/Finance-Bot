import { getApiBase, getAuthHeader } from '../lib/runtime';

function requestHeaders() {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const authHeader = getAuthHeader();
  if (authHeader) headers.Authorization = authHeader;
  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text().catch(() => String(response.status));
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, { headers: requestHeaders() });
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'POST',
    headers: requestHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'PATCH',
    headers: requestHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: 'DELETE',
    headers: requestHeaders(),
  });
  return parseResponse<T>(response);
}
