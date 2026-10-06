import { NextRequest } from 'next/server';
import { configuredOrigins } from './proxy-origins';
export { apiBase } from './proxy-api';

export function allowedRequest(r: NextRequest): boolean {
  try {
    const origins = configuredOrigins();
    const hosts = origins.map(o => new URL(o).host);
    const host = r.headers.get('host');
    if (!hosts.includes(host || '')) return false;
    const secFetchSite = r.headers.get('sec-fetch-site');
    if (secFetchSite && ['cross-site', 'same-site'].includes(secFetchSite)) return false;
    const origin = r.headers.get('origin');
    if (origin && !origins.includes(origin)) return false;
    const method = r.method;
    if (method !== 'GET' && !origin) return false;
    return true;
  } catch {
    return false;
  }
}
