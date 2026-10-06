export function apiBase(): string {
    const raw = process.env.ORBIT_API_ORIGIN || 'http://127.0.0.1:' + (process.env.ORBIT_API_PORT || '5088');
    const u = new URL(raw);
    const p = Number(u.port);

    if (u.protocol !== 'http:') throw new Error('Configuração inválida.');
    if (u.hostname !== '127.0.0.1' && u.hostname !== 'api') throw new Error('Configuração inválida.');
    if (u.username || u.password || u.search || u.hash) throw new Error('Configuração inválida.');
    if (u.pathname !== '/') throw new Error('Configuração inválida.');
    if (isNaN(p) || p < 1024 || p > 65535) throw new Error('Configuração inválida.');
    if (u.hostname === 'api' && p !== 8080) throw new Error('Configuração inválida.');

    return u.origin;
}
