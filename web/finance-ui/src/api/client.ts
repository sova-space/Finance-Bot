import { getApiBase, getAuthHeader } from '../lib/runtime';

export async function apiGet<T>(path: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const authHeader = getAuthHeader();
  if (authHeader) {
    headers.Authorization = authHeader;
  }

  const response = await fetch(`${getApiBase()}${path}`, { headers });
  if (!response.ok) {
    const body = await response.text().catch(() => String(response.status));
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
