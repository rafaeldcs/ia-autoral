export function configuredOrigins(): string[] {
    const origin = process.env.ORBIT_PUBLIC_ORIGIN;
    if (origin) {
        try {
            const url = new URL(origin);
            if (url.protocol !== 'https:') {
                throw new Error('Invalid protocol');
            }
            if (url.username !== '' || url.password !== '' || url.search !== '' || url.hash !== '') {
                throw new Error('Invalid URL components');
            }
            if (origin !== url.origin) {
                throw new Error('Invalid origin');
            }
            return [url.origin];
        } catch (e) {
            throw new Error('Invalid ORBIT_PUBLIC_ORIGIN');
        }
    }
    const port = Number(process.env.ORBIT_WEB_PORT || '3100');
    if (!Number.isInteger(port) || port < 1024 || port > 65535) {
        throw new Error('Invalid ORBIT_WEB_PORT');
    }
    return [`http://127.0.0.1:${port}`, `http://localhost:${port}`];
}
