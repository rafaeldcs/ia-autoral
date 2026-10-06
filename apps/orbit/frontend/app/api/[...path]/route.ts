import { NextRequest, NextResponse } from 'next/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
async function handle(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const origin = request.headers.get('origin');
  const host = request.headers.get('host');
  const port = process.env.ORBIT_WEB_PORT || '3100';
  const apiPort = process.env.ORBIT_API_PORT || '5088';
  if (!/^\d{4,5}$/.test(port) || !/^\d{4,5}$/.test(apiPort)) throw Error('Invalid local port');
  const hosts = [`127.0.0.1:${port}`, `localhost:${port}`];
  if (!hosts.includes(host || '') || (origin && !hosts.map(h=>`http://${h}`).includes(origin)) || ['cross-site','same-site'].includes(request.headers.get('sec-fetch-site') || '')) return NextResponse.json({error:'Origem não autorizada.'},{status:403});
  const segments = (await context.params).path;
  if (segments.some(s=>!/^[-a-zA-Z0-9]+$/.test(s))) return NextResponse.json({error:'Caminho inválido.'},{status:400});
  try {
    const proxyToken = process.env.ORBIT_PROXY_TOKEN;
    if (!proxyToken) throw Error('Local server configuration missing.');
    const body = request.method === 'GET' ? undefined : await request.text();
    if (body && Buffer.byteLength(body)>100000) return NextResponse.json({error:'Solicitação muito grande.'},{status:413});
    const response = await fetch(`http://127.0.0.1:${apiPort}/api/${segments.join('/')}`, {method:request.method,headers:{'Content-Type':'application/json','X-Orbit-Token':proxyToken,'Cookie':request.headers.get('cookie')||''},body,cache:'no-store',signal:AbortSignal.timeout(12000)});
    const text = await response.text();
    const headers:Record<string,string>={'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
    const cookie=response.headers.get('set-cookie');if(cookie)headers['Set-Cookie']=cookie;
    return new NextResponse(text,{status:response.status,headers});
  } catch {return NextResponse.json({error:'O serviço local está indisponível. Inicie o Orbit e tente novamente.'},{status:503})}
}
export const GET=handle; export const POST=handle; export const PUT=handle;
