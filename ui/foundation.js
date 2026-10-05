'use strict';
(() => {
  const $ = id => document.getElementById(id);
  let token = '', busy = false, activeJob = null, renderVersion = 0, selectionVersion = 0;
  const say = text => { $('status').textContent = text; };
  async function api(path, body) {
    const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST',
      headers: {Authorization: `Bearer ${token}`, ...(body === undefined ? {} : {'Content-Type': 'application/json'})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}), cache: 'no-store', signal: AbortSignal.timeout(15000)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Erro HTTP ${response.status}`);
    return data;
  }
  function setBusy(value) {
    busy = value;
    for (const id of ['send', 'project', 'conversation', 'mode', 'new-conversation', 'marketing-use']) $(id).disabled = value;
    for (const id of ['image-size', 'image-steps', 'image-seed']) $(id).disabled = value;
    $('cancel').hidden = !value; $('cancel').disabled = false;
  }
  function addOption(select, value, label) {
    const item = document.createElement('option'); item.value = value; item.textContent = label; select.append(item);
  }
  async function capabilities() {
    const result = await api('/api/foundation/status');
    $('capabilities').textContent = Object.entries(result.capabilities).map(([kind, value]) =>
      `${kind === 'text' ? 'Texto/código' : 'Imagens'}: ${value.loaded ? 'carregado' : value.registered ? 'registrado, não carregado' : 'não configurado'}`).join(' · ');
  }
  function render(conversation, project) {
    const version = ++renderVersion;
    $('messages').replaceChildren();
    for (const message of conversation.messages || []) {
      const article = document.createElement('article'), heading = document.createElement('h3'), content = document.createElement('pre');
      heading.textContent = message.role === 'user' ? 'Você' : 'LocalAuthor'; content.textContent = message.content;
      article.append(heading, content);
      const meta = message.metadata || {};
      if (meta.notice) { const note = document.createElement('p'); note.className = 'metadata'; note.textContent = meta.notice; article.append(note); }
      if (meta.model || meta.experience_id) {
        const details = document.createElement('details'), summary = document.createElement('summary'), text = document.createElement('pre');
        summary.textContent = 'Modelo, contexto e rastreabilidade';
        text.textContent = JSON.stringify({model: meta.model, experience_id: meta.experience_id,
          history_messages_used: meta.history_messages_used, input_tokens: meta.input_tokens,
          omitted_history: meta.omitted_history, omitted_evidence: meta.omitted_evidence, evidence: meta.evidence}, null, 2);
        details.append(summary, text); article.append(details);
      }
      $('messages').append(article);
      if (meta.origin === 'foundation_image' && /^[a-f0-9]{32}$/.test(meta.artifact_id || '')) {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = 'Mostrar imagem'; article.append(button);
        button.addEventListener('click', async () => {
          button.disabled = true;
          try {
            const result = await api(`/api/foundation/image?${new URLSearchParams({project_id: project, id: meta.artifact_id})}`);
            if (version !== renderVersion) return;
            if (!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(result.data || '')) throw new Error('Imagem inválida.');
            const image = document.createElement('img'); image.alt = 'Imagem gerada pelo modelo visual local'; image.width = meta.width || 512; image.height = meta.height || 512; image.src = result.data;
            article.append(image); button.remove();
          } catch (error) { say(error.message); button.disabled = false; }
        });
      }
    }
    $('messages').scrollTop = $('messages').scrollHeight;
  }
  async function loadConversation() {
    const version = ++selectionVersion, project = $('project').value, id = $('conversation').value;
    if (!id) { render({messages: []}, project); return; }
    const data = await api(`/api/conversation?${new URLSearchParams({project_id: project, id})}`);
    if (version === selectionVersion) render(data, project);
  }
  async function loadConversations() {
    const version = ++selectionVersion, project = $('project').value;
    $('conversation').replaceChildren(); render({messages: []}, project);
    if (!project) { say('Cadastre uma pasta de projeto na tela principal.'); return; }
    const rows = await api(`/api/conversations?${new URLSearchParams({project_id: project})}`);
    if (version !== selectionVersion) return;
    for (const row of rows) addOption($('conversation'), row.id, row.title);
    await loadConversation();
  }
  async function newConversation() {
    const project = $('project').value;
    if (!project) throw new Error('Escolha um projeto.');
    const conversation = await api('/api/conversations', {project_id: project, title: 'Criação com modelos locais'});
    if (project !== $('project').value) return null;
    ++selectionVersion; addOption($('conversation'), conversation.id, conversation.title); $('conversation').value = conversation.id;
    render(conversation, project); return conversation.id;
  }
  async function poll() {
    const current = activeJob;
    if (!current) return;
    $('resume').hidden = true;
    try {
      while (activeJob === current) {
        const job = await api(`/api/jobs/${current.id}`);
        if (activeJob !== current) return;
        if (['completed', 'failed', 'cancelled', 'interrupted'].includes(job.state)) {
          activeJob = null; setBusy(false);
          if (job.state === 'completed') {
            render(job.result || {messages: []}, current.project);
            if ($('prompt').value === current.prompt) $('prompt').value = '';
            say('Concluído. Revise a resposta. Nenhum treinamento foi executado.');
          } else say(job.error || `Tarefa ${job.state}. Seu pedido foi preservado.`);
          try { await capabilities(); } catch (error) { say(`Resultado preservado. ${error.message}`); }
          return;
        }
        say(job.state === 'queued' ? 'Na fila local.' : 'Gerando localmente. Cancelamento cooperativo.');
        await new Promise(resolve => setTimeout(resolve, 800));
      }
    } catch (error) {
      if (activeJob === current) { say(`${error.message} Consulte a tarefa novamente, sem reenviar o pedido.`); $('resume').hidden = false; }
    }
  }
  $('connect').addEventListener('submit', async event => {
    event.preventDefault(); token = $('token').value.trim();
    try {
      await capabilities(); const rows = await api('/api/projects'); $('project').replaceChildren();
      for (const row of rows) addOption($('project'), row.id, row.name);
      await loadConversations(); $('token').value = ''; $('login').hidden = true; $('workspace').hidden = false;
      say(rows.length ? 'Conectado. Os modelos precisam estar registrados antes da geração.' : 'Conectado. Cadastre uma pasta na tela principal.');
    } catch (error) { token = ''; $('workspace').hidden = true; $('login').hidden = false; say(error.message); }
  });
  $('logout').addEventListener('click', () => {
    if (busy && !window.confirm('Sair não cancela a tarefa no servidor. Continuar?')) return;
    token = ''; activeJob = null; ++renderVersion; ++selectionVersion; setBusy(false); $('resume').hidden = true;
    $('messages').replaceChildren(); $('prompt').value = ''; $('workspace').hidden = true; $('login').hidden = false; say('Desconectado.');
  });
  $('project').addEventListener('change', () => loadConversations().catch(error => say(error.message)));
  $('conversation').addEventListener('change', () => loadConversation().catch(error => say(error.message)));
  $('new-conversation').addEventListener('click', async () => {
    if (busy) return; setBusy(true);
    try { await newConversation(); } catch (error) { say(error.message); } finally { setBusy(false); }
  });
  $('mode').addEventListener('change', () => {
    $('image-options').hidden = $('mode').value !== 'image';
    $('mode-help').textContent = $('mode').value === 'image' ? 'Descreva a imagem desejada. O modelo visual precisa estar configurado para as opções escolhidas.' : 'Histórico e fontes do projeto entram no contexto. Código gerado não é executado.';
    $('prompt').spellcheck = $('mode').value !== 'code';
  });
  $('compose').addEventListener('submit', async event => {
    event.preventDefault(); if (busy) return;
    const prompt = $('prompt').value, project = $('project').value;
    if (!project || !prompt.trim() || prompt.length > 8000) { say('Escolha um projeto e informe um pedido de até 8.000 caracteres.'); return; }
    setBusy(true);
    try {
      const conversation = $('conversation').value || await newConversation();
      if (!conversation) throw new Error('A seleção de projeto mudou.');
      const result = await api('/api/chat', {project_id: project, conversation_id: conversation, message: prompt,
        mode: $('mode').value === 'image' ? 'image' : 'foundation', input_format: $('mode').value === 'code' ? 'code' : 'text',
        ...($('mode').value === 'image' ? {image_options: {width: Number($('image-size').value), height: Number($('image-size').value),
          seed: Number($('image-seed').value), steps: Number($('image-steps').value)}} : {})});
      activeJob = {id: result.job.id, prompt, project}; await poll();
    } catch (error) {
      if (!activeJob) setBusy(false);
      say(`${error.message} Seu pedido foi preservado. Em falha de conexão, consulte as tarefas nas ferramentas avançadas antes de reenviar.`);
    }
  });
  $('cancel').addEventListener('click', async () => {
    if (!activeJob) { say('A solicitação ainda não recebeu um identificador de tarefa.'); return; }
    try { await api(`/api/jobs/${activeJob.id}/cancel`, {}); $('cancel').disabled = true; say('Cancelamento solicitado; uma etapa em andamento pode precisar terminar.'); }
    catch (error) { say(error.message); }
  });
  $('resume').addEventListener('click', () => poll());
  let marketingReport = null, marketingProject = null, marketingVersion = 0;
  function clearMarketing() {
    ++marketingVersion; marketingReport = null; marketingProject = null;
    $('marketing-result').replaceChildren(); $('marketing-use').hidden = true;
    $('marketing-form').reset();
  }
  $('project').addEventListener('change', clearMarketing);
  $('logout').addEventListener('click', () => { if (!token) clearMarketing(); });
  $('marketing-form').addEventListener('input', () => {
    ++marketingVersion; marketingReport = null; marketingProject = null; $('marketing-use').hidden = true;
    $('marketing-result').textContent = 'Os dados mudaram; recalcule a comparação.';
  });
  $('marketing-form').addEventListener('submit', async event => {
    event.preventDefault(); const project = $('project').value, version = ++marketingVersion;
    marketingReport = null; $('marketing-use').hidden = true;
    const button = $('marketing-form').querySelector('button'); button.disabled = true;
    try {
      const campaigns = [...document.querySelectorAll('[data-campaign]')].map(box => {
        const input = field => box.querySelector(`[data-field="${field}"]`).value;
        return {name: input('name'), impressions: Number(input('impressions')), clicks: Number(input('clicks')),
          conversions: Number(input('conversions')), spend_cents: Math.round(Number(input('spend')) * 100)};
      });
      const report = await api('/api/foundation/marketing-metrics', {project_id: project, campaigns});
      if (version !== marketingVersion || project !== $('project').value || !token) return;
      const nodes = report.campaigns.map(row => {
        const p = document.createElement('p'), metric = value => value === null ? 'indisponível' : value;
        p.textContent = `${row.name}: CTR ${metric(row.ctr_percent)}%; conversão por clique ${metric(row.click_conversion_percent)}%; custo por clique R$ ${metric(row.cpc_brl)}; custo por conversão R$ ${metric(row.cpa_brl)}.`;
        return p;
      });
      const best = document.createElement('p'); best.textContent = report.best_ctr.length ? `Maior CTR: ${report.best_ctr.join(', ')}.` : 'CTR indisponível: não há impressões.';
      const note = document.createElement('p'); note.textContent = report.notice;
      $('marketing-result').replaceChildren(...nodes, best, note);
      marketingReport = report; marketingProject = project; $('marketing-use').hidden = false;
    } catch (error) { if (version === marketingVersion) $('marketing-result').textContent = error.message; }
    finally { button.disabled = false; }
  });
  $('marketing-use').addEventListener('click', () => {
    if (busy || !marketingReport || marketingProject !== $('project').value) return;
    const proposal = 'Proponha próximos experimentos a partir destes cálculos locais sobre dados fornecidos, sem afirmar que houve publicação ou gasto real:\n' + JSON.stringify(marketingReport);
    if (proposal.length > 8000) { say('Análise excede o orçamento do pedido.'); return; }
    $('mode').value = 'text'; $('mode').dispatchEvent(new Event('change')); $('prompt').value = proposal; $('prompt').focus();
  });
})();
