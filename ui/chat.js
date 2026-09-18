"use strict";
const $ = id => document.getElementById(id);
const state = { token: '', projects: [], project: null, conversation: null, busy: false };
let toastTimer;
function el(tag, text, cls) { const node = document.createElement(tag); node.textContent = text; if (cls)
    node.className = cls; return node; }
function toast(message) { $('notification').textContent = message; $('notification').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('notification').hidden = true, 6000); }
async function api(path, body) { const response = await fetch(path, { method: body ? 'POST' : 'GET', headers: { Authorization: 'Bearer ' + state.token, ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) }); const result = await response.json(); if (!response.ok)
    throw Error(result.error || 'Não foi possível concluir.'); return result; }
function handle(fn) { return async (event) => { event?.preventDefault(); try {
    await fn(event);
}
catch (error) {
    toast(error.message);
} }; }
function updateAvailability() {
    const unavailable = !state.project || state.busy;
    for (const node of document.querySelectorAll('#new-chat,#show-rules,#compose button,#compose select,#message-input,[data-prompt]')) node.disabled = unavailable;
    $('start-project').hidden = Boolean(state.project);
    $('suggestion-help').hidden = !state.project;
    document.querySelector('.suggestions').hidden = !state.project;
    $('compose').setAttribute('aria-busy', String(state.busy));
    $('message-input').placeholder = state.project ? 'Descreva uma ideia, uma dúvida ou o próximo passo…' : 'Adicione um projeto para começar a conversar.';
}
function busy(value) { state.busy = value; $('busy').hidden = !value; for (const node of document.querySelectorAll('#studio button,#studio select'))
    node.disabled = value; $('message-input').disabled = value; updateAvailability(); }
function resetChat() { state.conversation = null; $('messages').replaceChildren(); $('welcome').hidden = false; $('message-input').value = ''; updateInputCount(); updateAvailability(); renderConversations().catch(error => toast(error.message)); $('message-input').focus(); }
function renderProjects() { const list = $('project-list'); list.replaceChildren(); for (const project of state.projects) {
    const node = el('button', project.name, project.id === state.project?.id ? 'active' : '');
    node.setAttribute('aria-current', project.id === state.project?.id ? 'true' : 'false');
    node.onclick = handle(() => selectProject(project));
    list.append(node);
} }
async function renderConversations() { if (!state.project)
    return; const project = state.project; const rows = await api('/api/conversations?project_id=' + project.id); if (state.project?.id !== project.id)
    return; const list = $('conversation-list'); list.replaceChildren(); $('conversation-empty').hidden = rows.length > 0; for (const row of rows) {
    const node = el('button', row.title, row.id === state.conversation?.id ? 'active' : '');
    node.setAttribute('aria-current', row.id === state.conversation?.id ? 'true' : 'false');
    node.onclick = handle(async () => { const data = await api('/api/conversation?project_id=' + project.id + '&id=' + row.id); if (state.project?.id === project.id) {
        state.conversation = data;
        renderMessages();
        await renderConversations();
    } });
    list.append(node);
} }
async function selectProject(project) { if (state.busy)
    return; hideBrowserPanel(); state.project = project; state.conversation = null; $('project-heading').textContent = project.name; $('folder-path').textContent = project.root; $('welcome-copy').textContent = 'Converse sobre ' + project.name + '. Comece com o problema, combine o critério de pronto e planeje como testar.'; $('sidebar').classList.remove('open'); renderProjects(); resetChat(); }
function renderMessages() { const list = $('messages'); list.replaceChildren(); const messages = state.conversation?.messages || []; $('welcome').hidden = messages.length > 0; for (const message of messages) {
    const box = el('article', '', `message ${message.role}`);
    const names = { project_guide: 'Guia do projeto · orientação estruturada', retrieval_only: 'Memória local · trechos recuperados', local_model: 'IA local · geração experimental', investigation_memory: 'Sistema investigado · evidências observadas', browser_session: 'Navegador da IA · sessão de investigação' };
    const code = message.metadata.format === 'code';
    box.append(el('div', message.role === 'user' ? 'Você' : names[message.metadata.origin] || 'Assistente', 'message-label'), el(code ? 'pre' : 'div', message.content, code ? 'message-content code-content' : 'message-content'));
    const copy = el('button', 'Copiar mensagem', 'copy-message');
    copy.type = 'button';
    copy.onclick = handle(async () => {
        await navigator.clipboard.writeText(message.content);
        toast('Mensagem copiada sem alterar o texto.');
    });
    box.append(copy);
    if(message.metadata.browser_session_id) { const view=el('button','Acompanhar investigação','copy-message'); view.onclick=handle(()=>openBrowserSession(message.metadata.browser_session_id)); box.append(view); }
    for (const source of message.metadata.sources || []) {
        if (!source.url.startsWith('https://'))
            continue;
        const link = el('a', source.title);
        link.href = source.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        box.append(link);
    }
    if (message.metadata.notice)
        box.append(el('small', message.metadata.notice));
    list.append(box);
} list.scrollTop = list.scrollHeight; }
$('connect-form').onsubmit = handle(async () => { state.token = $('local-token').value.trim(); await api('/api/health'); state.projects = await api('/api/projects'); $('local-token').value = ''; $('connect').hidden = true; $('studio').hidden = false; renderProjects(); updateAvailability(); if (state.projects.length)
    await selectProject(state.projects[0]);
else
    $('add-project').focus(); });
$('logout').onclick = () => { hideBrowserPanel(); state.token = ''; state.project = null; state.conversation = null; state.projects = []; $('messages').replaceChildren(); $('project-list').replaceChildren(); $('conversation-list').replaceChildren(); $('studio').hidden = true; $('connect').hidden = false; $('local-token').focus(); };
$('open-menu').onclick = () => { $('sidebar').classList.add('open'); $('close-menu').focus(); };
$('close-menu').onclick = () => { $('sidebar').classList.remove('open'); $('open-menu').focus(); };
$('start-project').onclick = () => $('add-project').click();
$('add-project').onclick = () => { $('project-dialog').showModal(); $('project-name').focus(); };
for (const button of document.querySelectorAll('[data-close]'))
    button.onclick = () => $(button.dataset.close).close();
$('project-create').onsubmit = handle(async () => { const project = await api('/api/projects', { name: $('project-name').value, root: $('project-root').value }); state.projects = await api('/api/projects'); $('project-dialog').close(); $('project-create').reset(); await selectProject(project); toast('Projeto adicionado. Sua pasta foi preservada.'); });
$('new-chat').onclick = handle(async () => { if (!state.project)
    throw Error('Adicione uma pasta de projeto primeiro.'); resetChat(); });
for (const button of document.querySelectorAll('[data-prompt]'))
    button.onclick = () => { $('message-input').value = button.dataset.prompt; $('response-mode').value = button.dataset.mode || 'guide'; modeNotice(); updateInputCount(); $('message-input').focus(); toast('Exemplo preenchido. Edite a mensagem ou clique em Enviar.'); };
function modeNotice() { const modes = { browser: 'Envie um endereço HTTPS para abrir o navegador da IA e acompanhar as capturas. Isso autoriza conexão ao site nesta sessão. Nunca envie senhas no chat.', investigation: 'Consulta as telas já observadas neste projeto, com data e origem. Não navega agora. Não envie senhas no chat.', guide: 'Guias estruturados e referências. Não é geração neural. Ctrl + Enter para enviar.', knowledge: 'Consulta apenas fontes deste projeto. Não inclui conversas ou fontes de outros projetos.', model: 'Laboratório: pedido curto, sem histórico nem arquivos no contexto. A saída pode estar errada e não é executada.' }; $('mode-notice').textContent = modes[$('response-mode').value]; }
$('response-mode').onchange = () => { modeNotice(); updateInputCount(); };
function updateInputCount() {
    const value = $('message-input').value;
    const chars = Array.from(value).length;
    const bytes = new TextEncoder().encode(value).length;
    $('input-count').textContent = `${chars.toLocaleString('pt-BR')} / 8.000 caracteres` + ($('response-mode').value === 'model' ? ` · IA: ${bytes}/180 bytes` : '');
    $('input-count').classList.toggle('input-over-limit', chars > 8000 || ($('response-mode').value === 'model' && bytes > 180));
}
$('message-input').oninput = updateInputCount;
$('input-format').onchange = () => {
    const code = $('input-format').value === 'code';
    const input = $('message-input');
    input.spellcheck = !code;
    input.setAttribute('autocorrect', code ? 'off' : 'on');
    input.setAttribute('autocapitalize', code ? 'off' : 'sentences');
    input.classList.toggle('code-input', code);
};
$('message-input').onkeydown = event => { if (!event.isComposing && event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    $('compose').requestSubmit();
} };
$('compose').onsubmit = handle(async () => { if (state.busy)
    return; if (!state.project)
    throw Error('Adicione uma pasta de projeto primeiro.'); const message = $('message-input').value; if (!message.trim())
    return;
    if (Array.from(message).length > 8000)
        throw Error('O pedido excede 8.000 caracteres. O conteúdo foi mantido no campo; divida-o em mensagens.');
    if ($('response-mode').value === 'model' && new TextEncoder().encode(message).length > 180)
        throw Error('Este modelo aceita até 180 bytes por pedido. O texto foi mantido; reduza o pedido ou escolha outro modo.');
    busy(true); try {
    if (!state.conversation)
        state.conversation = await api('/api/conversations', { project_id: state.project.id, title: Array.from(message.trim()).slice(0, 70).join('') });
    let response = await api('/api/chat', { project_id: state.project.id, conversation_id: state.conversation.id, message, mode: $('response-mode').value, input_format: $('input-format').value });
    if (response.job) {
        for (let i = 0; i < 180; i++) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const job = await api('/api/jobs/' + response.job.id);
            if (job.state === 'completed') {
                response = job.result;
                break;
            }
            if (['failed', 'cancelled', 'interrupted'].includes(job.state))
                throw Error(job.error || 'Geração interrompida.');
        }
        if (response.job)
            throw Error('Geração ainda em andamento. Consulte Atividade nas ferramentas avançadas.');
    }
    state.conversation = response;
    const browserMessage=response.messages?.at(-1)?.metadata?.browser_session_id;
    if(browserMessage) await openBrowserSession(browserMessage);
    $('message-input').value = '';
    updateInputCount();
    renderMessages();
    await renderConversations();
}
finally {
    busy(false);
    $('message-input').focus();
} });
$('show-rules').onclick = handle(async () => { if (!state.project)
    throw Error('Escolha um projeto primeiro.'); const data = await api('/api/project-preferences?project_id=' + state.project.id); $('method').value = data.method; $('wip').value = data.wip_limit; $('done').value = data.definition_of_done; $('quality-rules').replaceChildren(...data.quality.map(rule => el('li', rule))); $('official-sources').replaceChildren(...data.sources.map(source => { const a = el('a', source.title + ' ↗'); a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; })); const report = await api('/api/engineering-report'); $('learning-result').textContent = report.evaluation ? `Curso experimental: ${report.evaluation.passed}/${report.evaluation.total} decisões guiadas aprovadas. ${report.limitations}` : 'Novo currículo em preparação. As orientações acima foram escritas e revisadas; não significam domínio adquirido pelo modelo.'; const writing = await api('/api/communication-report').catch(() => ({})); if (writing.evaluation?.total) { $('learning-result').textContent += ` Escrita: ${writing.evaluation.passed}/${writing.evaluation.total} pedidos reformulados. ${writing.chatEnabled ? 'Candidato experimental habilitado.' : 'Candidato não ativado no chat.'}`; } $('rules-dialog').showModal(); });
$('rules-form').onsubmit = handle(async () => { await api('/api/project-preferences', { project_id: state.project.id, method: $('method').value, wip_limit: Number($('wip').value), definition_of_done: $('done').value }); $('rules-dialog').close(); toast('Orientações salvas para este projeto.'); });
document.addEventListener('keydown', event => { if (event.key === 'Escape')
    $('sidebar').classList.remove('open'); });

updateAvailability();

// Browser workspace: snapshots come from the server's isolated LocalAuthor tool.
const browserState = {id:null, project:null, row:null, timer:null, selected:null, generation:0};
function hideBrowserPanel() {
    clearTimeout(browserState.timer); browserState.generation++;
    browserState.id=null; browserState.row=null; browserState.selected=null;
    $('browser-panel').hidden=true; document.body.classList.remove('browser-visible');
    $('browser-login-dialog').close(); $('browser-login-form').reset();
    $('browser-image').removeAttribute('src'); $('browser-image').hidden=true;
    $('browser-links').replaceChildren(); $('browser-frames').replaceChildren();
    $('browser-tools').hidden=true; $('browser-open-form').hidden=false; $('browser-start').disabled=false;
    $('browser-status').textContent='Informe um endereço ou escolha uma sessão para continuar.';
    $('browser-current-url').textContent=''; $('browser-interpretation').textContent='';
}
async function browserSessionList() {
    const project=state.project?.id;
    if(!project) throw Error('Escolha um projeto antes de investigar um site.');
    const rows=await api('/api/browser/sessions?project_id='+project);
    if(state.project?.id!==project) return;
    const select=$('browser-sessions'); select.replaceChildren(el('option','Escolha uma sessão'));
    select.firstChild.value='';
    for(const row of rows) { const option=el('option',new URL(row.url).hostname+' · '+new Date(row.created_at).toLocaleString('pt-BR')); option.value=row.id; select.append(option); }
    select.value=browserState.id || '';
    return rows;
}
async function openBrowserPanel(resume=true) {
    if(!state.project) throw Error('Adicione ou escolha um projeto primeiro.');
    $('browser-panel').hidden=false; document.body.classList.add('browser-visible');
    browserState.project=state.project.id;
    const rows=await browserSessionList();
    const active=rows?.find(r=>['starting','busy','ready'].includes(r.state));
    if(resume && active && !browserState.id) {
        browserState.id=active.id; browserState.generation++;
        $('browser-sessions').value=active.id;
        await pollBrowser(browserState.generation);
    }
}
async function openBrowserSession(id) {
    await openBrowserPanel(false); clearTimeout(browserState.timer);
    browserState.id=id; browserState.selected=null; browserState.generation++;
    $('browser-sessions').value=id;
    await pollBrowser(browserState.generation);
}
async function showBrowserFrame(number) {
    const row=browserState.row, project=browserState.project, id=browserState.id;
    const frame=row?.frames.find(f=>f.number===number);
    if(!frame) return;
    browserState.selected=number;
    $('browser-current-url').textContent=frame.url;
    $('browser-interpretation').textContent='Leitura da IA: '+frame.interpretation.description+' (categoria prevista; descrição fixa).'+(frame.truncated?' A lista de controles excedeu o limite desta observação.':'');
    if(frame.blockedRequests?.length) $('browser-interpretation').textContent+=' Conexões bloqueadas: '+frame.blockedRequests.join(', ')+'.';
    if(frame.reason) $('browser-interpretation').textContent+=' '+frame.reason;
    $('browser-image').hidden=true;
    if(frame.file) {
        const artifact=await api(`/api/browser/image?project_id=${project}&id=${id}&frame=${number}`);
        if(browserState.id!==id || browserState.selected!==number || browserState.project!==project) return;
        $('browser-image').src=artifact.data; $('browser-image').hidden=false;
    }
    const latest=row.frames.at(-1)?.number===number && row.state==='ready';
    $('browser-links').replaceChildren();
    for(const control of frame.controls.filter(c=>c.safe)) {
        const button=el('button',control.name+(control.visited?' · visitado':''));
        button.disabled=!latest;
        button.onclick=handle(()=>browserAction('link',{target:control.id}));
        $('browser-links').append(button);
    }
    $('browser-login').disabled=!latest || !frame.loginAvailable;
    for(const button of document.querySelectorAll('[data-browser-action]')) button.disabled=button.dataset.browserAction==='stop' ? !['starting','busy','ready'].includes(row.state) : !latest;
}
async function pollBrowser(generation) {
    const id=browserState.id, project=browserState.project;
    if(!id || generation!==browserState.generation || state.project?.id!==project) return;
    try {
        const row=await api(`/api/browser/session?project_id=${project}&id=${id}`);
        if(generation!==browserState.generation) return;
        const previous=browserState.row;
        browserState.row=row;
        const names={starting:'Preparando navegador isolado…',busy:'A IA está trabalhando. Você pode encerrar a sessão.',ready:'Pronto para a próxima ação.',stopped:'Sessão encerrada.',failed:'Não foi possível concluir.',interrupted:'Sessão interrompida.'};
        $('browser-status').textContent=(row.error || names[row.state])+' '+row.frames.length+' observação(ões).';
        $('browser-tools').hidden=false;
        $('browser-login').disabled=row.state!=='ready' || !row.frames.at(-1)?.loginAvailable;
        $('browser-start').disabled=['starting','busy','ready'].includes(row.state);
        $('browser-open-form').hidden=['starting','busy','ready'].includes(row.state);
        const frames=$('browser-frames'); frames.replaceChildren();
        for(const frame of row.frames) {
            const button=el('button',frame.number+' · '+frame.title);
            button.setAttribute('aria-pressed',String(frame.number===browserState.selected));
            button.onclick=handle(()=>showBrowserFrame(frame.number)); frames.append(button);
        }
        if(row.frames.length && (row.frames.length!==previous?.frames.length || browserState.selected===null)) await showBrowserFrame(row.frames.at(-1).number);
        else if(row.frames.length && row.state!==previous?.state) await showBrowserFrame(browserState.selected);
        for(const button of document.querySelectorAll('[data-browser-action]')) {
            if(button.dataset.browserAction==='stop') button.disabled=!['starting','busy','ready'].includes(row.state);
            else if(row.state!=='ready') button.disabled=true;
        }
        if(['starting','busy','ready'].includes(row.state)) browserState.timer=setTimeout(()=>pollBrowser(generation),1200);
    } catch(error) { $('browser-status').textContent=error.message; }
}
async function browserAction(action, fields={}) {
    const row=browserState.row;
    if(!row) return;
    const command=action==='stop' ? {action} : {action,snapshot:row.frames.at(-1)?.snapshot,...fields};
    await api('/api/browser/action',{project_id:browserState.project,id:row.id,command});
    clearTimeout(browserState.timer); await pollBrowser(browserState.generation);
}
$('open-browser').onclick=handle(openBrowserPanel);
$('browser-close').onclick=()=>{ hideBrowserPanel(); $('open-browser').focus(); };
$('browser-sessions').onchange=handle(()=>{if($('browser-sessions').value) return openBrowserSession($('browser-sessions').value);});
$('browser-open-form').onsubmit=handle(async()=>{
    $('browser-start').disabled=true;
    try {
        const row=await api('/api/browser/start',{project_id:state.project.id,url:$('browser-url').value.trim(),allow_network:true,
            asset_hosts:$('browser-hosts').value.split(',').map(s=>s.trim()).filter(Boolean),
            auth_hosts:$('browser-auth-hosts').value.split(',').map(s=>s.trim()).filter(Boolean)});
        await openBrowserSession(row.id);
    } finally { if(!['starting','busy','ready'].includes(browserState.row?.state)) $('browser-start').disabled=false; }
});
for(const button of document.querySelectorAll('[data-browser-action]')) button.onclick=handle(()=>browserAction(button.dataset.browserAction));
$('browser-login').onclick=()=>{
    $('browser-login-form').reset();
    $('browser-login-origin').textContent='Destino: '+new URL(browserState.row.frames.at(-1).url).origin;
    $('browser-login-dialog').showModal(); $('browser-username').focus();
};
$('browser-login-form').onsubmit=handle(async()=>{
    const credentials={username:$('browser-username').value,password:$('browser-password').value};
    $('browser-login-form').reset(); $('browser-login-dialog').close();
    try { await browserAction('login',credentials); }
    finally {credentials.username='';credentials.password='';}
});
