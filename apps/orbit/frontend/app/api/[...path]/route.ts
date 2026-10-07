import { NextRequest, NextResponse } from 'next/server';
import { allowedRequest, apiBase } from '../../proxy-policy';
import { boundedBody } from '../../proxy-body';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!allowedRequest(request)) return new NextResponse(JSON.stringify({ error: 'Acesso negado' }), { status: 403 });
  const params = await context.params;
  const segments = params.path;
  if (segments.some(seg => !/^[a-zA-Z0-9-]+$/.test(seg))) return new NextResponse(JSON.stringify({ error: 'Caminho inválido' }), { status: 400 });

  try {
    const proxyToken = process.env.ORBIT_PROXY_TOKEN;
    if (!proxyToken) throw new Error('Token ausente');
    const body = await boundedBody(request);
    const response = await fetch(apiBase() + '/api/' + segments.join('/'), {
      method: request.method,
      headers: {
        'Content-Type': 'application/json',
        'X-Orbit-Token': proxyToken,
        'Cookie': request.headers.get('cookie') || ''
      },
      body,
      cache: 'no-store',
      signal: AbortSignal.timeout(12000),
      redirect: 'error'
    });
    const text = await response.text();
    if (Buffer.byteLength(text, 'utf8') > 1000000) throw new Error('Corpo muito grande');

    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    headers.append('Cache-Control', 'no-store');
    headers.append('X-Content-Type-Options', 'nosniff');

    for (const cookie of response.headers.getSetCookie() || []) {
      headers.append('Set-Cookie', cookie);
    }

    return new NextResponse(text, { status: response.status, headers });
  } catch (e) {
    if (e instanceof Error && e.message === 'BODY_TOO_LARGE') {
      return new NextResponse(JSON.stringify({ error: 'Corpo muito grande' }), { status: 413 });
    }
    return new NextResponse(JSON.stringify({ error: 'Erro interno' }), { status: 503 });
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
