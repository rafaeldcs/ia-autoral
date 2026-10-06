import { NextRequest } from 'next/server';

export async function boundedBody(request: NextRequest): Promise<string | undefined> {
  if (request.method === 'GET') return undefined;
  if (!request.body) return '';

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    reader.cancel().catch(() => {});
  }, 12000);

  try {
    while (true) {
      if (timedOut) break;
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      length += value.byteLength;
      if (length > 100000) {
        await reader.cancel();
        throw new Error("BODY_TOO_LARGE");
      }
    }
  } finally {
    clearTimeout(timer);
  }

  if (timedOut) throw new Error("BODY_TIMEOUT");
  return new TextDecoder().decode(Buffer.concat(chunks));
}
