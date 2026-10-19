'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const input = $('video-images'), list = $('video-scenes'), exportButton = $('video-export');
  if (!input || !list || !exportButton) return;
  const MAX_FILES = 12, MAX_FILE_BYTES = 20_000_000, MAX_TOTAL_BYTES = 80_000_000;
  const MAX_IMAGE_PIXELS = 25_000_000, MAX_TOTAL_PIXELS = 100_000_000;
  let scenes = [], working = false;

  function notice(message) { $('video-status').textContent = message; }
  function dimensions() {
    return $('video-format').value === 'landscape' ? [1280, 720]
      : $('video-format').value === 'square' ? [720, 720] : [720, 1280];
  }
  function update() {
    list.replaceChildren();
    scenes.forEach((scene, index) => {
      const row = document.createElement('div'); row.className = 'video-scene';
      const preview = document.createElement('img'); preview.src = scene.url; preview.alt = `Prévia da cena ${index + 1}`;
      const label = document.createElement('strong'); label.textContent = `Cena ${index + 1} · ${scene.file.name}`;
      const captionLabel = document.createElement('label'); captionLabel.textContent = 'Legenda desta cena';
      const caption = document.createElement('input'); caption.type = 'text'; caption.maxLength = 120; caption.value = scene.caption;
      caption.addEventListener('input', () => { scene.caption = caption.value; });
      const actions = document.createElement('div'); actions.className = 'toolbar';
      for (const [text, delta] of [['↑ Subir', -1], ['↓ Descer', 1]]) {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = text;
        button.disabled = working || index + delta < 0 || index + delta >= scenes.length;
        button.addEventListener('click', () => { [scenes[index], scenes[index + delta]] = [scenes[index + delta], scenes[index]]; update(); });
        actions.append(button);
      }
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Remover'; remove.disabled = working;
      remove.addEventListener('click', () => { URL.revokeObjectURL(scene.url); scene.bitmap.close(); scenes.splice(index, 1); update(); }); actions.append(remove);
      row.append(preview, label, captionLabel, caption, actions); list.append(row);
    });
    exportButton.disabled = working || !scenes.length || typeof HTMLCanvasElement.prototype.captureStream !== 'function' || typeof MediaRecorder === 'undefined';
    if (scenes.length && exportButton.disabled && !working) notice('Este navegador não oferece gravação de vídeo pelo canvas. Abra o LocalAuthor em uma versão atual do Edge ou Chrome.');
  }

  input.addEventListener('change', async () => {
    if (working) return;
    const files = [...input.files]; input.value = '';
    if (!files.length) return;
    let totalBytes = scenes.reduce((sum, row) => sum + row.file.size, 0);
    if (scenes.length + files.length > MAX_FILES || files.some(file => !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
      || file.size <= 0 || file.size > MAX_FILE_BYTES) || files.reduce((sum, file) => sum + file.size, totalBytes) > MAX_TOTAL_BYTES) {
      notice('Selecione até 12 PNG/JPEG/WebP, com até 20 MB por arquivo e 80 MB no total.'); return;
    }
    const added = [];
    try {
      for (const file of files) {
        const bitmap = await createImageBitmap(file), pixels = bitmap.width * bitmap.height;
        totalBytes += file.size;
        if (!bitmap.width || !bitmap.height || pixels > MAX_IMAGE_PIXELS || scenes.reduce((sum, row) => sum + row.bitmap.width * row.bitmap.height, 0)
          + added.reduce((sum, row) => sum + row.bitmap.width * row.bitmap.height, 0) + pixels > MAX_TOTAL_PIXELS) {
          bitmap.close(); throw new Error('As dimensões das imagens excedem o limite local de segurança.');
        }
        added.push({file, bitmap, url: URL.createObjectURL(file), caption: ''});
      }
      scenes.push(...added); notice(`${scenes.length} cena(s) pronta(s). Reordene e adicione legendas antes de exportar.`);
    } catch (error) {
      for (const scene of added) { URL.revokeObjectURL(scene.url); scene.bitmap.close(); }
      notice(error.message || 'Não foi possível ler uma das imagens.');
    }
    update();
  });

  function paintImage(ctx, image, progress, alpha = 1) {
    const [width, height] = dimensions(), cover = Math.max(width / image.width, height / image.height);
    const scale = cover * (1.015 + 0.035 * progress), drawW = image.width * scale, drawH = image.height * scale;
    ctx.save(); ctx.globalAlpha = alpha;
    ctx.drawImage(image, (width - drawW) / 2, (height - drawH) / 2, drawW, drawH);
    ctx.restore();
  }
  function paintText(ctx, title, caption) {
    const [width, height] = dimensions(), titleText = title.trim(), captionText = caption.trim();
    if (!titleText && !captionText) return;
    const bandHeight = Math.min(height * .27, 240), gradient = ctx.createLinearGradient(0, height - bandHeight, 0, height);
    gradient.addColorStop(0, 'rgba(5,10,18,0)'); gradient.addColorStop(.35, 'rgba(5,10,18,.66)'); gradient.addColorStop(1, 'rgba(5,10,18,.86)');
    ctx.fillStyle = gradient; ctx.fillRect(0, height - bandHeight, width, bandHeight);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#fff';
    if (titleText) { ctx.font = `700 ${Math.round(height * .055)}px system-ui`; ctx.fillText(titleText, width / 2, height - bandHeight * .60, width * .82); }
    if (captionText) { ctx.font = `${Math.round(height * .033)}px system-ui`; ctx.fillText(captionText, width / 2, height - bandHeight * .31, width * .84); }
  }
  function supportedType() {
    for (const type of ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'])
      if (MediaRecorder.isTypeSupported(type)) return type;
    return '';
  }

  $('video-format').addEventListener('change', () => { if (scenes.length) notice('Formato atualizado. A composição usa o corte central para preencher o quadro.'); });
  exportButton.addEventListener('click', async () => {
    if (working || !scenes.length) return;
    const mimeType = supportedType();
    if (!mimeType) { notice('Este navegador não oferece codificação WebM compatível.'); return; }
    const title = $('video-title').value.slice(0, 100), seconds = Number($('video-duration').value);
    if (!Number.isInteger(seconds) || seconds < 2 || seconds > 5 || scenes.length * seconds > 60) {
      notice('O vídeo deve ter até 60 segundos. Reduza a duração ou o número de cenas.'); return;
    }
    const [width, height] = dimensions(), canvas = document.createElement('canvas');
    canvas.width = width; canvas.height = height;
    const ctx = canvas.getContext('2d', {alpha: false});
    if (!ctx) { notice('Não foi possível criar a tela de composição.'); return; }
    const stream = canvas.captureStream(30), chunks = [];
    let recorder;
    try {
      recorder = new MediaRecorder(stream, {mimeType, videoBitsPerSecond: 5_000_000});
    } catch (error) { stream.getTracks().forEach(track => track.stop()); notice(`Não foi possível iniciar o codificador local: ${error.message}`); return; }
    working = true; update(); $('video-progress').hidden = false; $('video-progress').value = 0; notice('Compondo vídeo localmente…');
    recorder.addEventListener('dataavailable', event => { if (event.data?.size) chunks.push(event.data); });
    const stopped = new Promise((resolve, reject) => { recorder.addEventListener('stop', resolve, {once: true}); recorder.addEventListener('error', event => reject(event.error || new Error('Falha na gravação WebM.')), {once: true}); });
    try {
      recorder.start(500);
      const fadeSeconds = Math.min(.6, seconds / 4), total = scenes.length * seconds, started = performance.now();
      const frame = () => {
        const elapsed = (performance.now() - started) / 1000, bounded = Math.min(elapsed, total - .001);
        const index = Math.min(Math.floor(bounded / seconds), scenes.length - 1), local = bounded - index * seconds;
        ctx.fillStyle = '#0a0e14'; ctx.fillRect(0, 0, width, height);
        paintImage(ctx, scenes[index].bitmap, local / seconds);
        if (index + 1 < scenes.length && local > seconds - fadeSeconds) {
          const progress = Math.max(0, Math.min(1, (local - seconds + fadeSeconds) / fadeSeconds));
          paintImage(ctx, scenes[index + 1].bitmap, 0, progress);
        }
        paintText(ctx, title, scenes[index].caption);
        $('video-progress').value = Math.min(99, Math.floor(bounded / total * 100));
        if (elapsed < total) requestAnimationFrame(frame);
      };
      frame();
      await new Promise(resolve => setTimeout(resolve, total * 1000 + 500));
      if (recorder.state !== 'inactive') recorder.stop();
      await stopped;
      if (!chunks.length) throw new Error('O navegador terminou sem gerar quadros de vídeo.');
      const blob = new Blob(chunks, {type: mimeType}), url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = `localauthor-video-${new Date().toISOString().replace(/[:.]/g, '-')}.webm`;
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 60_000);
      $('video-progress').value = 100; notice(`Vídeo WebM exportado (${width} × ${height}, ${scenes.length} cenas, ${total}s). O arquivo foi salvo pelo navegador.`);
    } catch (error) {
      if (recorder.state !== 'inactive') recorder.stop();
      try { await stopped; } catch { /* retain the original error */ }
      notice(`Exportação interrompida: ${error.message}`);
    } finally {
      stream.getTracks().forEach(track => track.stop()); working = false; update();
    }
  });
  update();
})();
