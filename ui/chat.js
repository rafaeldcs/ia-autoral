"use strict";
const $ = id => document.getElementById(id);
const state = { token: '', projects: [], project: null, conversation: null, busy: false, requestBusy: false, jobId: null };
let voiceChat = null;
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
    $('send').disabled = unavailable || !$('message-input').value.trim();
    $('start-project').hidden = Boolean(state.project);
    $('suggestion-help').hidden = !state.project;
    document.querySelector('.suggestions').hidden = !state.project;
    $('compose').setAttribute('aria-busy', String(state.busy));
    $('message-input').placeholder = state.project ? 'Descreva uma ideia, uma dúvida ou o próximo passo…' : 'Adicione um projeto para começar a conversar.';
    voiceChat?.syncControls();
}
function busy(value) { state.requestBusy = value; state.busy = value || Boolean(voiceChat?.active); $('busy').hidden = !value; for (const node of document.querySelectorAll('#studio button,#studio select'))
    node.disabled = state.busy; $('message-input').disabled = state.busy; updateAvailability(); }
function resetChat() { state.conversation = null; $('messages').replaceChildren(); $('welcome').hidden = false; $('message-input').value = ''; updateInputCount(); updateAvailability(); renderConversations().catch(error => toast(error.message)); $('message-input').focus(); }
function renderProjects() { const list = $('project-list'); list.replaceChildren(); for (const project of state.projects) {
    const node = el('button', project.name, project.id === state.project?.id ? 'active' : '');
    node.replaceChildren(el('span', project.name, 'nav-label'));
    node.setAttribute('aria-current', project.id === state.project?.id ? 'true' : 'false');
    node.title = project.name;
    node.onclick = handle(() => selectProject(project));
    list.append(node);
} }
async function renderConversations() { if (!state.project)
    return; const project = state.project; const rows = await api('/api/conversations?project_id=' + project.id); if (state.project?.id !== project.id)
    return; const list = $('conversation-list'); list.replaceChildren(); $('conversation-empty').hidden = rows.length > 0; for (const row of rows) {
    const node = el('button', row.title, row.id === state.conversation?.id ? 'active' : '');
    node.replaceChildren(el('span', row.title, 'nav-label'));
    node.setAttribute('aria-current', row.id === state.conversation?.id ? 'true' : 'false');
    node.title = row.title;
    node.onclick = handle(async () => { const data = await api('/api/conversation?project_id=' + project.id + '&id=' + row.id); if (state.project?.id === project.id) {
        state.conversation = data;
        renderMessages();
        closeNavigation();
        await renderConversations();
    } });
    list.append(node);
} }
async function selectProject(project) { if (state.busy)
    return; hideBrowserPanel(); state.project = project; state.conversation = null; $('project-heading').textContent = project.name; $('project-heading').title = project.name; $('folder-path').textContent = project.root; $('welcome-copy').textContent = 'Converse sobre ' + project.name + '. Comece com o problema, combine o critério de pronto e planeje como testar.'; closeNavigation(); renderProjects(); resetChat(); }
function renderMessages() { const list = $('messages'); list.replaceChildren(); const messages = state.conversation?.messages || []; $('welcome').hidden = messages.length > 0; for (const message of messages) {
    const box = el('article', '', `message ${message.role}`);
    const names = { foundation_text: 'LocalAuthor · modelo local com contexto', project_guide: 'Guia do projeto · orientação estruturada', retrieval_only: 'Memória local · trechos recuperados', local_model: 'IA local · geração experimental', investigation_memory: 'Sistema investigado · evidências observadas', browser_session: 'Navegador da IA · sessão de investigação' };
    const code = message.metadata.format === 'code';
    const label = message.role === 'user' ? 'Você' : message.metadata.qualification === 'scoped' ? 'IA local · correção avaliada em escopo limitado' : names[message.metadata.origin] || 'Assistente';
    box.append(el('div', label, 'message-label'), el(code ? 'pre' : 'div', message.content, code ? 'message-content code-content' : 'message-content'));
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
$('logout').onclick = () => { voiceChat?.stop(); hideBrowserPanel(); state.token = ''; state.project = null; state.conversation = null; state.projects = []; $('messages').replaceChildren(); $('project-list').replaceChildren(); $('conversation-list').replaceChildren(); $('studio').hidden = true; $('connect').hidden = false; $('local-token').focus(); };
const mobileNavigation = matchMedia('(max-width:760px)');
function closeNavigation(collapse = false) {
    $('sidebar').classList.remove('open'); $('sidebar-scrim').hidden = true;
    if (collapse && !mobileNavigation.matches) document.body.classList.add('sidebar-collapsed');
    $('open-menu').setAttribute('aria-expanded', String(!mobileNavigation.matches && !document.body.classList.contains('sidebar-collapsed')));
}
$('open-menu').onclick = () => { document.body.classList.remove('sidebar-collapsed'); if (mobileNavigation.matches) { $('sidebar').classList.add('open'); $('sidebar-scrim').hidden = false; } $('open-menu').setAttribute('aria-expanded', 'true'); $('close-menu').focus(); };
$('close-menu').onclick = () => { closeNavigation(true); $('open-menu').focus(); };
$('sidebar-scrim').onclick = () => { closeNavigation(); $('open-menu').focus(); };
mobileNavigation.addEventListener('change', () => closeNavigation());
closeNavigation();
$('open-tools').onclick = $('sidebar-tools').onclick = () => $('tools-dialog').showModal();
$('start-project').onclick = () => $('add-project').click();
$('add-project').onclick = () => { $('project-dialog').showModal(); $('project-name').focus(); };
for (const button of document.querySelectorAll('[data-close]'))
    button.onclick = () => $(button.dataset.close).close();
$('project-create').onsubmit = handle(async () => { const project = await api('/api/projects', { name: $('project-name').value, root: $('project-root').value }); state.projects = await api('/api/projects'); $('project-dialog').close(); $('project-create').reset(); await selectProject(project); toast('Projeto adicionado. Sua pasta foi preservada.'); });
$('new-chat').onclick = handle(async () => { if (!state.project)
    throw Error('Adicione uma pasta de projeto primeiro.'); closeNavigation(); resetChat(); });
for (const button of document.querySelectorAll('[data-prompt]'))
    button.onclick = () => { $('tools-dialog').close(); $('message-input').value = button.dataset.prompt; $('response-mode').value = button.dataset.mode || 'guide'; modeNotice(); updateInputCount(); $('message-input').focus(); toast('Exemplo preenchido. Edite a mensagem ou clique em Enviar.'); };
function modeNotice() { const modes = { foundation: 'Conversa com o modelo local, histórico e fontes deste projeto. Respostas podem estar erradas; código não é executado.', browser: 'Envie um endereço HTTPS para abrir o navegador da IA e acompanhar as capturas. Isso autoriza conexão ao site nesta sessão. Nunca envie senhas no chat.', investigation: 'Consulta as telas já observadas neste projeto, com data e origem. Não navega agora. Não envie senhas no chat.', guide: 'Guias estruturados e referências. Não é geração neural. Ctrl + Enter para enviar.', knowledge: 'Consulta apenas fontes deste projeto. Não inclui conversas ou fontes de outros projetos.', model: 'Laboratório: pedido curto, sem histórico nem arquivos no contexto. A saída pode estar errada e não é executada.' }; $('mode-notice').textContent = modes[$('response-mode').value]; }
$('response-mode').onchange = () => { modeNotice(); updateInputCount(); };
function looksLikeCode(value) {
    // Presentation only. The server independently classifies the original string.
    const codeLine = /^\s*(?:(?:def|async\s+def|class)\s+\w+[^\n]*[:{]\s*$|(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(|(?:const|let|var|string|int|bool|double|decimal)\s+\w+\s*=|(?:public|private|protected|internal)\s+(?:static\s+)?(?:class|void|async|Task|[A-Z]\w*)\b|(?:from\s+[\w.]+\s+import\s+|import\s+(?:[\w.]+|[{'\"])|using\s+[\w.]+\s*;)|(?:SELECT\s+.+\s+FROM\b|INSERT\s+INTO\b|CREATE\s+TABLE\b|UPDATE\s+\w+\s+SET\b)|(?:console\.(?:log|error)|print|Assert\.\w+|assert\.\w+)\s*\(|(?:if|for|while)\s*\([^\n]*\)\s*[{:]|(?:handle|reverse_proxy|server|location)\s+[^\n]*[{}]|(?:return|throw)\s+[^\n]+;\s*$)/im;
    if (/^\s{0,3}(?:`{3,}|~{3,})/m.test(value) || codeLine.test(value) || /^\s*<([A-Za-z][\w:-]*)\b[^>]*>[\s\S]*<\/\1>\s*$/i.test(value)) return true;
    if (/^\s*[\[{]/.test(value)) { try { const parsed = JSON.parse(value); return parsed !== null && typeof parsed === 'object'; } catch {} }
    return false;
}
function updateInputCount() {
    const value = $('message-input').value;
    const chars = Array.from(value).length;
    const bytes = new TextEncoder().encode(value).length;
    $('input-count').textContent = `${chars.toLocaleString('pt-BR')} / 8.000 caracteres` + ($('response-mode').value === 'model' ? ` · IA: ${bytes}/180 bytes` : '');
    $('input-count').classList.toggle('input-over-limit', chars > 8000 || ($('response-mode').value === 'model' && bytes > 180));
    $('input-count').hidden = chars < 6400 && !($('response-mode').value === 'model' && bytes > 150);
    const input = $('message-input');
    const code = looksLikeCode(value);
    input.spellcheck = !code;
    input.setAttribute('autocorrect', 'off');
    input.setAttribute('autocapitalize', 'off');
    input.classList.toggle('code-input', code);
    input.style.height = 'auto';
    input.style.height = Math.min(Math.max(input.scrollHeight, 52), Math.min(220, innerHeight * .28)) + 'px';
    $('send').disabled = !state.project || state.busy || !value.trim();
}
$('message-input').oninput = updateInputCount;
// Compatibility with installed clients that restore draft format through this ID.
$('input-format').onchange = updateInputCount;
window.addEventListener('resize', updateInputCount);
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
    let response = await api('/api/chat', { project_id: state.project.id, conversation_id: state.conversation.id, message, mode: $('response-mode').value, input_format: 'auto' });
    if (response.job) {
        state.jobId = response.job.id;
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
catch (error) {
    voiceChat?.stop(error.message);
    throw error;
}
finally {
    state.jobId = null;
    busy(false);
    $('message-input').focus();
}
if (voiceChat?.active) voiceChat.reply(state.conversation.messages.at(-1)?.content || ''); });
$('show-rules').onclick = handle(async () => { if (!state.project)
    throw Error('Escolha um projeto primeiro.'); const data = await api('/api/project-preferences?project_id=' + state.project.id); $('method').value = data.method; $('wip').value = data.wip_limit; $('done').value = data.definition_of_done; $('work-profile').value = data.work_profile || 'general'; $('quality-rules').replaceChildren(...data.quality.map(rule => el('li', rule))); $('official-sources').replaceChildren(...data.sources.map(source => { const a = el('a', source.title + ' ↗'); a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; })); const report = await api('/api/engineering-report'); $('learning-result').textContent = report.evaluation ? `Curso experimental: ${report.evaluation.passed}/${report.evaluation.total} decisões guiadas aprovadas. ${report.limitations}` : 'Novo currículo em preparação. As orientações acima foram escritas e revisadas; não significam domínio adquirido pelo modelo.'; const writing = await api('/api/communication-report').catch(() => ({})); if (writing.evaluation?.total) { $('learning-result').textContent += ` Escrita: ${writing.evaluation.passed}/${writing.evaluation.total} pedidos reformulados. ${writing.chatEnabled ? 'Candidato experimental habilitado.' : 'Candidato não ativado no chat.'}`; } $('rules-dialog').showModal(); });
$('rules-form').onsubmit = handle(async () => { await api('/api/project-preferences', { project_id: state.project.id, method: $('method').value, wip_limit: Number($('wip').value), definition_of_done: $('done').value, work_profile: $('work-profile').value }); $('rules-dialog').close(); toast('Orientações salvas para este projeto.'); });
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.querySelector('dialog[open]')) {
        if ($('sidebar').classList.contains('open')) { closeNavigation(); $('open-menu').focus(); }
        else if (!$('browser-panel').hidden) { hideBrowserPanel(); $('open-browser').focus(); }
    }
    if (event.key === 'Tab' && mobileNavigation.matches && $('sidebar').classList.contains('open')) {
        const nodes = [...$('sidebar').querySelectorAll('button:not(:disabled),a[href],summary')].filter(node => node.getClientRects().length);
        const first = nodes[0], last = nodes.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
});

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
// Speech input is decoded only by our server. Never use cloud SpeechRecognition.
function voiceWav(chunks, sampleRate) {
    const length = chunks.reduce((n, part) => n + part.length, 0);
    const source = new Float32Array(length); let offset = 0;
    for (const part of chunks) { source.set(part, offset); offset += part.length; }
    const count = Math.min(480000, Math.floor(length * 16000 / sampleRate));
    const bytes = new Uint8Array(44 + count * 2), view = new DataView(bytes.buffer);
    const ascii = (at, value) => [...value].forEach((ch, i) => view.setUint8(at + i, ch.charCodeAt(0)));
    ascii(0, 'RIFF'); view.setUint32(4, bytes.length - 8, true); ascii(8, 'WAVEfmt ');
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, 16000, true); view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    ascii(36, 'data'); view.setUint32(40, count * 2, true);
    for (let i = 0; i < count; i++) {
        const start = i * sampleRate / 16000, end = Math.min(length, (i + 1) * sampleRate / 16000);
        let sum = 0, weight = 0;
        for (let j = Math.floor(start); j < Math.ceil(end); j++) {
            const w = Math.min(end, j + 1) - Math.max(start, j); sum += source[j] * w; weight += w;
        }
        const value = Math.max(-1, Math.min(1, sum / (weight || 1)));
        view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
    }
    let binary = ''; for (let i = 0; i < bytes.length; i += 16384) binary += String.fromCharCode(...bytes.subarray(i, i + 16384));
    return btoa(binary);
}
voiceChat = (() => {
    let active = false, muted = false, epoch = 0, phase = '', stream = null, context = null, processor = null;
    let source = null, sink = null, timer = null, request = null, abort = null, voice = null, resumeSpeech = null;
    const status = value => { phase = value; $('voice-status').textContent = value; };
    const syncControls = () => {
        $('voice-start').disabled = !state.project || (state.busy && !active);
        $('voice-start').setAttribute('aria-pressed', String(active));
        $('voice-start').title = active ? 'Encerrar conversa por voz' : 'Conversar por voz';
        $('voice-bar').hidden = !active;
        $('voice-stop').disabled = false; $('voice-mute').disabled = false;
        $('voice-mute').setAttribute('aria-pressed', String(muted));
        $('voice-mute').textContent = muted ? 'Ouvir respostas' : 'Silenciar resposta';
    };
    function releaseMicrophone() {
        clearTimeout(timer); timer = null;
        if (processor) { processor.onaudioprocess = null; processor.disconnect(); processor = null; }
        source?.disconnect(); sink?.disconnect(); source = sink = null;
        stream?.getTracks().forEach(track => track.stop()); stream = null;
        if (context) { context.close().catch(() => {}); context = null; }
    }
    function stop(message = '') {
        active = false; ++epoch; releaseMicrophone();
        abort?.abort(); abort = null;
        if (request && state.project && state.token) api('/api/voice/cancel', {project_id: state.project.id, request_id: request}).catch(() => {});
        request = null; resumeSpeech = null; window.speechSynthesis?.cancel();
        if (state.jobId && state.token) api('/api/jobs/' + state.jobId + '/cancel', {}).catch(() => {});
        busy(state.requestBusy); syncControls();
        if (message) toast(message);
    }
    async function localVoice() {
        if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) throw Error('Este aplicativo não oferece leitura de voz.');
        for (let attempt = 0; attempt < 15; attempt++) {
            const voices = speechSynthesis.getVoices().filter(v => v.localService === true && /^pt(?:-|$)/i.test(v.lang));
            if (voices.length) return voices.find(v => /^pt-BR$/i.test(v.lang)) || voices[0];
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw Error('Instale uma voz em português no Windows para ouvir as respostas. Nenhuma voz na nuvem foi utilizada.');
    }
    async function start() {
        if (active || state.busy) return;
        if (!state.project) throw Error('Escolha um projeto para conversar.');
        if ($('message-input').value.trim()) throw Error('Envie ou guarde a mensagem digitada antes de iniciar a voz.');
        const version = ++epoch, project = state.project.id;
        $('voice-confirm').disabled = true; $('voice-setup').textContent = 'Conferindo voz e modelo locais…';
        try {
            if (!isSecureContext || !navigator.mediaDevices?.getUserMedia) throw Error('Abra o aplicativo instalado ou um endereço HTTPS para usar o microfone.');
            const [speech, models, selectedVoice] = await Promise.all([api('/api/voice/status'), api('/api/foundation/status'), localVoice()]);
            if (!speech.registered) throw Error(speech.notice || 'Reconhecimento de voz não instalado no servidor.');
            if (!models.capabilities.text.registered) throw Error('Configure o modelo de conversa local no servidor.');
            if (version !== epoch || state.project?.id !== project) return;
            voice = selectedVoice; active = true; muted = false; $('voice-dialog').close();
            clearTimeout(toastTimer); $('notification').hidden = true;
            $('response-mode').value = 'foundation'; modeNotice(); busy(false); syncControls();
            await listen(version);
        } finally { $('voice-confirm').disabled = false; }
    }
    async function listen(version = epoch) {
        if (!active || version !== epoch) return;
        status('Ouvindo… Faça uma pausa para enviar.');
        try {
            const captured = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}, video: false});
            if (!active || version !== epoch) { captured.getTracks().forEach(track => track.stop()); return; }
            stream = captured;
            for (const track of stream.getAudioTracks()) track.onended = () => { if (active && version === epoch) stop('O microfone foi desconectado.'); };
            context = new AudioContext({sampleRate: 16000}); await context.resume();
            if (!active || version !== epoch) return;
            source = context.createMediaStreamSource(stream);
            // Bounded PCM only; no downloadable encoder or script from another origin.
            processor = context.createScriptProcessor(4096, 1, 1); sink = context.createGain(); sink.gain.value = 0;
            source.connect(processor); processor.connect(sink); sink.connect(context.destination);
            const rate = context.sampleRate, chunks = []; let count = 0, speech = false, lastSpeech = 0, finishing = false;
            function finish() {
                if (finishing || !active || version !== epoch) return; finishing = true; releaseMicrophone();
                if (!speech) { stop('Não ouvi sua fala. Confira o microfone e comece novamente.'); return; }
                transcribe(voiceWav(chunks, rate), version).catch(error => { if (active && version === epoch) stop(error.message); });
            }
            timer = setTimeout(finish, 30000);
            processor.onaudioprocess = event => {
                if (finishing || !active || version !== epoch) return;
                const remaining = Math.max(0, rate * 30 - count);
                const part = Float32Array.from(event.inputBuffer.getChannelData(0).subarray(0, remaining));
                chunks.push(part); count += part.length;
                const seconds = count / rate, rms = Math.sqrt(part.reduce((sum, v) => sum + v * v, 0) / (part.length || 1));
                if (rms > .015) { speech = true; lastSpeech = seconds; }
                if (seconds >= 30 || (speech && seconds - lastSpeech >= 1.5) || (!speech && seconds >= 10)) finish();
            };
        } catch (error) {
            if (active && version === epoch) stop(error.name === 'NotAllowedError' ? 'Permita o microfone nas configurações do aplicativo ou navegador.' : 'Não consegui abrir o microfone. Confira o dispositivo de áudio.');
        }
    }
    async function transcribe(audio, version) {
        status('Entendendo sua fala no servidor local…');
        request = crypto.randomUUID().replaceAll('-', ''); abort = new AbortController();
        const response = await fetch('/api/voice/transcribe', {method: 'POST', cache: 'no-store',
            headers: {Authorization: 'Bearer ' + state.token, 'Content-Type': 'application/json'},
            body: JSON.stringify({project_id: state.project.id, request_id: request, audio}),
            signal: AbortSignal.any([abort.signal, AbortSignal.timeout(115000)])});
        audio = ''; const result = await response.json(); request = null; abort = null;
        if (!active || version !== epoch) return;
        if (!response.ok) throw Error(result.error || 'Não consegui reconhecer a fala.');
        if (!result.offline || typeof result.text !== 'string' || !result.text.trim() || Array.from(result.text).length > 8000) throw Error('Transcrição inválida.');
        $('message-input').value = result.text; updateInputCount();
        status('A IA está preparando a resposta…');
        // A voice turn is an ordinary chat turn; it gains no code/deploy permissions.
        state.busy = false; $('compose').requestSubmit();
    }
    function reply(text) {
        if (!active) return;
        const version = epoch;
        if (muted) { listen(version); return; }
        const spoken = text.replace(/```[\s\S]*?```|~~~[\s\S]*?~~~/g, ' Há um trecho de código na resposta; consulte o chat. ').trim();
        if (!spoken) { listen(version); return; }
        status('Falando… O microfone está desligado.');
        const utterance = new SpeechSynthesisUtterance(spoken.slice(0, 1800) + (spoken.length > 1800 ? ' A resposta completa está no chat.' : ''));
        utterance.voice = voice; utterance.lang = voice.lang; utterance.rate = 1;
        let finished = false;
        const finish = () => { if (finished) return; finished = true; resumeSpeech = null; if (active && version === epoch) listen(version); };
        resumeSpeech = finish;
        utterance.onend = finish;
        utterance.onerror = event => { if (muted || event.error === 'interrupted' || event.error === 'canceled') finish(); else if (active && version === epoch) stop('Não consegui ler a resposta. O texto completo permanece no chat.'); };
        speechSynthesis.cancel(); speechSynthesis.speak(utterance);
    }
    $('voice-start').onclick = () => {
        if (active) { stop('Conversa por voz encerrada.'); return; }
        $('voice-setup').textContent = ''; $('voice-dialog').showModal();
    };
    $('voice-confirm').onclick = async () => { try { await start(); } catch (error) { $('voice-setup').textContent = error.message; stop(); } };
    $('voice-stop').onclick = () => stop('Conversa por voz encerrada.');
    $('voice-mute').onclick = () => { muted = !muted; syncControls(); if (muted) { const next = resumeSpeech; speechSynthesis.cancel(); next?.(); } };
    $('voice-dialog').addEventListener('close', () => { if (!active) ++epoch; });
    document.addEventListener('visibilitychange', () => { if (document.hidden && active) stop('Voz encerrada porque o aplicativo ficou em segundo plano.'); });
    window.addEventListener('pagehide', () => stop());
    return {get active() { return active; }, start, stop, reply, syncControls};
})();
voiceChat.syncControls();
