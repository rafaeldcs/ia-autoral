"use strict";
const $ = id => document.getElementById(id);
const state = { token: '', projects: [], project: null, conversation: null, busy: false, requestBusy: false, jobId: null };
let voiceChat = null;
let toastTimer;
let conversationListVersion=0;
let allProjectsVisible=false;
const recovery=window.LocalAuthorRecovery.create({
    api,input:$('message-input'),mode:$('response-mode'),notice:toast,
    readOnly:()=>state.project?.access==='reader',changed:()=>updateAvailability(),
    write:(text,mode)=>{$('message-input').value=text;$('response-mode').value=mode==='model'?'model':'auto';modeNotice();updateInputCount(false);},
    inspect:()=>recoverRequest(),retry:()=>retryRequest(),cancel:async()=>{const pending=recovery.pending;if(!pending)return;const request=await lookupRequest(pending);await api('/api/jobs/'+request.job_id+'/cancel',{});await recoverRequest();}
});
window.localAuthorInstallerState=phase=>{
    for(const link of document.querySelectorAll('.message-action[href="/api/app/installer/file"]')){
        link.textContent=phase==='loading'?'Baixando instalador…':'Baixar instalador';
        if(phase==='loading')link.setAttribute('aria-disabled','true');else link.removeAttribute('aria-disabled');
    }
};
window.LocalAuthorRecovery.flushLocal=()=>recovery.flushLocal();
function el(tag, text, cls) { const node = document.createElement(tag); node.textContent = text; if (cls)
    node.className = cls; return node; }
function toast(message) { $('notification').textContent = message; $('notification').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('notification').hidden = true, 6000); }
async function api(path, body, options={}) { const response = await fetch(path, { ...options, method: body ? 'POST' : 'GET', headers: { Authorization: 'Bearer ' + state.token, ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) }); const result = await response.json(); if (!response.ok){
    const error=Error(result.error || 'Não foi possível concluir.');error.status=response.status;throw error;} return result; }
function handle(fn) { return async (event) => { event?.preventDefault(); try {
    await fn(event);
}
catch (error) {
    toast(error.message);
} }; }
function updateAvailability() {
    const unavailable = !state.project || state.busy || state.project.access === 'reader' || Boolean(recovery.pending);
    for (const node of document.querySelectorAll('#new-chat,#compose button,#compose select,#message-input,[data-prompt]')) node.disabled = unavailable;
    $('show-rules').disabled=!state.project||state.busy;
    $('open-browser').disabled=!state.project||state.busy||state.project.access==='reader';
    const readOnly=state.project?.access==='reader';
    for(const id of ['method','wip','done','work-profile'])$(id).disabled=readOnly;
    $('rules-form').querySelector('button.primary').disabled=readOnly;
    $('project-sharing').hidden=state.project?.access!=='owner';
    $('project-access-note').textContent=state.project?.access==='owner'?'Você é o proprietário. Somente você gerencia o compartilhamento.':readOnly?'Projeto compartilhado para consulta. Peça edição ao proprietário para enviar mensagens ou fazer alterações.':'Projeto compartilhado com edição. As pessoas com acesso podem consultar seu histórico e fontes.';
    $('send').disabled = unavailable || !$('message-input').value.trim();
    $('start-project').hidden = Boolean(state.project);
    $('suggestion-help').hidden = !state.project;
    document.querySelector('.suggestions').hidden = !state.project;
    $('compose').setAttribute('aria-busy', String(state.busy));
    $('message-input').placeholder = state.project ? 'Conte o que você tem em mente…' : 'Adicione um projeto para começar a conversar.';
    voiceChat?.syncControls();
}
function busy(value) { state.requestBusy = value; state.busy = value || Boolean(voiceChat?.active); $('busy').hidden = !value; for (const node of document.querySelectorAll('#studio button,#studio select'))
    node.disabled = state.busy; $('message-input').disabled = state.busy; updateAvailability(); }
async function resetChat() { await selectProject(state.project); }
function renderProjects() {
    const limit = 4;
    const list = $('project-list');
    list.replaceChildren();
    const preview = state.projects.slice(0, limit).map(project => project.id);
    if (state.project && !preview.includes(state.project.id)) {
        preview.pop();
        preview.push(state.project.id);
    }
    const hasShared = state.projects.some(project => project.access && project.access !== 'owner');
    for (const [shared, label] of [[false, 'Meus projetos'], [true, 'Compartilhados comigo']]) {
        const projects = state.projects.filter(project => Boolean(project.access && project.access !== 'owner') === shared);
        if (!projects.length) continue;
        if (hasShared) {
            const heading = el('p', label, 'project-group');
            heading.hidden = !allProjectsVisible && !projects.some(project => preview.includes(project.id));
            list.append(heading);
        }
        for (const project of projects) {
            const selected = project.id === state.project?.id;
            const node = el('button', '', selected ? 'active' : '');
            node.disabled = state.busy;
            node.hidden = !allProjectsVisible && !preview.includes(project.id);
            const copy = el('span', '', 'nav-copy');
            copy.append(el('span', project.name, 'nav-label'));
            if (shared) copy.append(el('span', (project.access === 'reader' ? 'Leitura' : 'Edição') + ' · ' + project.owner_name, 'nav-detail'));
            node.append(copy);
            node.setAttribute('aria-current', String(selected));
            node.title = project.name;
            node.onclick = handle(() => {
                allProjectsVisible = false;
                document.querySelector('.sidebar-scroll').scrollTop = 0;
                return selectProject(project);
            });
            list.append(node);
        }
    }
    const toggle = $('toggle-projects');
    toggle.hidden = state.projects.length <= limit;
    toggle.textContent = allProjectsVisible ? 'Mostrar menos projetos' : `Ver todos os projetos (${state.projects.length})`;
    toggle.setAttribute('aria-expanded', String(allProjectsVisible));
}
$('toggle-projects').onclick=()=>{allProjectsVisible=!allProjectsVisible;renderProjects();};
async function renderConversations() { if (!state.project)
    return; const project = state.project,version=++conversationListVersion; const rows = await api('/api/conversations?project_id=' + project.id+'&mine='+($('conversation-filter').value==='mine'?'1':'0')); if (state.project?.id !== project.id||version!==conversationListVersion)
    return; const list = $('conversation-list'); list.replaceChildren(); $('conversation-empty').hidden = rows.length > 0; for (const row of rows) {
    const node = el('button', row.title, row.id === state.conversation?.id ? 'active' : '');
    node.disabled=state.busy;
    const copy=el('span','','nav-copy');copy.append(el('span', row.title, 'nav-label'));node.replaceChildren(copy);
    if(row.created_by&&row.created_by.user_id!==window.LocalAuthorIdentity?.user?.id)copy.append(el('span',row.created_by.name,'nav-detail'));
    node.setAttribute('aria-current', row.id === state.conversation?.id ? 'true' : 'false');
    node.title = row.title;
    node.onclick = handle(()=>selectProject(project,row.id));
    list.append(node);
} }
async function selectProject(project,conversation='') {
    if(state.busy||!project)return;
    busy(true);
    try{
        await recovery.flushLocal();
        const selected=conversation?await api('/api/conversation?project_id='+project.id+'&id='+conversation):null;
        hideBrowserPanel();state.project=project;state.conversation=selected;
        $('project-heading').textContent=project.name;$('project-heading').title=project.name;$('folder-path').textContent=project.root;
        $('welcome-copy').textContent='Este é o espaço de '+project.name+'. Traga uma ideia, uma dúvida ou aquele ponto que travou. Vamos organizar o próximo passo.';
        closeNavigation();renderProjects();await recovery.open(project.id,conversation);renderMessages();await renderConversations();
    }finally{busy(false);}
    if(recovery.pending)await recoverRequest();
    $('message-input').focus();
}
function messageContent(message) {
    const value = message.content;
    if (message.role !== 'assistant')
        return el(message.metadata.format === 'code' ? 'pre' : 'div', value, message.metadata.format === 'code' ? 'message-content code-content' : 'message-content');
    const content = el('div', '', 'message-content rich-content');
    const fence = /^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)/gm;
    const languages = {csharp:'C#',cs:'C#',tsx:'TSX',typescript:'TypeScript',ts:'TypeScript',javascript:'JavaScript',js:'JavaScript',sql:'SQL',python:'Python',py:'Python',json:'JSON',html:'HTML',css:'CSS',bash:'Shell',sh:'Shell'};
    function block(code, info, incomplete = false) {
        const token = info.trim().split(/\s/)[0];
        const language = languages[token.toLowerCase()] || (/^[\w+#.-]{1,24}$/.test(token) ? token : 'Código');
        const section = el('section', '', 'code-block');
        section.setAttribute('aria-label', `Bloco de código ${language}`);
        const toolbar = el('div', '', 'code-toolbar');
        toolbar.append(el('span', language, 'code-language'));
        const copy = el('button', 'Copiar código', 'copy-code');
        copy.type = 'button'; copy.setAttribute('aria-label', `Copiar código ${language}`);
        copy.onclick = handle(async () => { await navigator.clipboard.writeText(code); toast('Código copiado sem alterar o texto.'); });
        toolbar.append(copy);
        const pre = el('pre', '', 'fenced-code'); pre.tabIndex = 0;
        pre.setAttribute('aria-label', `Código ${language}`);
        pre.append(el('code', code));
        section.append(toolbar, pre);
        if (incomplete) { const warning=el('small', 'Bloco de código sem fechamento na resposta.', 'code-incomplete'); warning.setAttribute('role','status'); section.append(warning); }
        content.append(section);
    }
    let position = 0, opening;
    while ((opening = fence.exec(value)) !== null) {
        // Backticks in a backtick fence's info string are ordinary text.
        if (opening[1][0] === '`' && opening[2].includes('`')) continue;
        if (opening.index > position) content.append(el('div', value.slice(position, opening.index), 'message-prose'));
        const start = fence.lastIndex;
        const closing = new RegExp('^ {0,3}' + opening[1][0] + '{' + opening[1].length + ',}[ \\t]*(?:\\r?\\n|$)', 'gm');
        closing.lastIndex = start;
        const end = closing.exec(value);
        block(value.slice(start, end ? end.index : value.length), opening[2], !end);
        position = end ? closing.lastIndex : value.length;
        fence.lastIndex = position;
        if (!end || position === value.length) break;
    }
    if (!position) {
        if (message.metadata.format === 'code') { block(value, ''); return content; }
        return el('div', value, 'message-content');
    }
    if (position < value.length) content.append(el('div', value.slice(position), 'message-prose'));
    return content;
}
function renderMessages() { const list = $('messages'); list.replaceChildren(); const messages = state.conversation?.messages || []; $('welcome').hidden = messages.length > 0; for (const message of messages) {
    const box = el('article', '', `message ${message.role}`);
    const names = { application_support:'LocalAuthor · aplicativo',web_research:'LocalAuthor · fontes consultadas', project_memory: 'Memória do projeto · preferência registrada', foundation_text: 'LocalAuthor', project_guide: 'Guia do projeto · orientação estruturada', retrieval_only: 'Memória local · trechos recuperados', local_model: 'IA local · geração experimental', investigation_memory: 'Sistema investigado · evidências observadas', browser_session: 'Navegador da IA · sessão de investigação' };
    const person=message.metadata.author_id?(message.metadata.author_id===window.LocalAuthorIdentity?.user?.id?'Você':message.metadata.author_name||'Pessoa do projeto'):(window.LocalAuthorIdentity?.user?'Histórico anterior aos perfis':'Você');
    const label = message.role === 'user' ? person : message.metadata.qualification === 'scoped' ? 'IA local · correção avaliada em escopo limitado' : names[message.metadata.origin] || 'Assistente';
    box.append(el('div', label, 'message-label'), messageContent(message));
    const copy = el('button', 'Copiar mensagem', 'copy-message');
    copy.type = 'button';
    copy.onclick = handle(async () => {
        await navigator.clipboard.writeText(message.content);
        toast('Mensagem copiada sem alterar o texto.');
    });
    box.append(copy);
    for(const action of message.metadata.actions||[]) {
        if(action.kind!=='download_installer'||action.url!=='/api/app/installer/file')continue;
        const download=el('a','Baixar instalador','message-action');download.href=action.url;download.download='Instalar-LocalAuthor-Conectado.exe';
        download.onclick=async event=>{
            event.preventDefault();
            if(window.chrome?.webview&&window.__localAuthorNativeInstallerDownloads){window.localAuthorInstallerState('loading');window.chrome.webview.postMessage('download-installer');return;}
            if(window.chrome?.webview){toast('Atualize o aplicativo para baixar por aqui. A nova versão será aplicada quando o chat estiver livre.');return;}
            download.setAttribute('aria-disabled','true');
            try{
                const response=await fetch(action.url,{headers:{Authorization:'Bearer '+state.token}});
                if(!response.ok){const error=await response.json();throw Error(error.error||'Instalador indisponível.');}
                const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=download.download;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);toast('Instalador baixado. Abra o arquivo salvo para instalar.');
            }catch(error){toast(error.message);}finally{download.removeAttribute('aria-disabled');}
        };box.append(download);
    }
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
    if (Array.isArray(message.metadata.memory_used) && (message.metadata.memory_used.length || message.metadata.omitted_memory))
        box.append(el('small', `Memórias usadas: ${message.metadata.memory_used.length}. Fora do contexto: ${message.metadata.omitted_memory || 0}.`));
    if (message.metadata.notice) {
        if(message.metadata.origin==='foundation_text') {
            const details=el('details','','response-details');
            details.append(el('summary','Sobre esta resposta'),el('small',message.metadata.notice));
            box.append(details);
        } else box.append(el('small', message.metadata.notice));
    }
    if(message.metadata.possibly_truncated) {
        const warning=el('p','A resposta pode estar incompleta porque atingiu o limite de tamanho.','response-warning');
        warning.setAttribute('role','status');box.append(warning);
    }
    if(message.metadata.instruction_review?.violations?.length) {
        const warning=el('p','A resposta ainda não atende a estes critérios: '+message.metadata.instruction_review.violations.join(' '),'response-warning');
        warning.setAttribute('role','status');box.append(warning);
    }
    list.append(box);
} list.scrollTop = list.scrollHeight; }
$('connect-form').onsubmit = handle(async () => { state.token = $('local-token').value.trim(); await api('/api/health'); state.projects = await api('/api/projects'); renderProjects(); updateAvailability(); if (state.projects.length){
    const last=await recovery.selection();const project=state.projects.find(row=>row.id===last?.project_id)||state.projects[0];
    try{await selectProject(project,project.id===last?.project_id?last.conversation_id:'');}catch(error){toast(error.message);await selectProject(project);}
}
// Expose the workspace only after recovery finishes choosing its initial scope.
// Otherwise a click can race the automatic selection and be lost on mobile.
$('local-token').value = ''; $('connect').hidden = true; $('studio').hidden = false;
if (!state.projects.length) $('add-project').focus(); });
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
$('project-existing').onchange=$('project-managed').onchange=()=>{const existing=$('project-existing').checked;$('project-root-field').hidden=!existing;$('project-root').required=existing;};
$('conversation-filter').onchange=()=>renderConversations().catch(error=>toast(error.message));
$('project-sharing').onclick=handle(()=>window.LocalAuthorIdentity.openSharing(state.project));
$('project-create').onsubmit = handle(async () => { const managed=$('project-managed').checked;const project = await api('/api/projects', { name: $('project-name').value,...(managed?{managed:true}:{root:$('project-root').value}) }); state.projects = await api('/api/projects'); $('project-dialog').close(); $('project-create').reset();$('project-managed').onchange(); await selectProject(state.projects.find(p=>p.id===project.id)||project); toast(managed?'Projeto criado na sua pasta do servidor.':'Pasta vinculada ao seu projeto.'); });
$('new-chat').onclick = handle(async () => { if (!state.project)
    throw Error('Adicione uma pasta de projeto primeiro.'); closeNavigation(); await resetChat(); });
for (const button of document.querySelectorAll('[data-prompt]'))
    button.onclick = () => { $('tools-dialog').close(); $('message-input').value = button.dataset.prompt; $('response-mode').value = button.dataset.mode === 'model' ? 'model' : 'auto'; modeNotice(); updateInputCount(); $('message-input').focus(); toast('Exemplo preenchido. Edite a mensagem ou clique em Enviar.'); };
function modeNotice() { $('mode-notice').textContent = 'Ctrl + Enter para enviar.'; }
$('response-mode').onchange = () => { modeNotice(); updateInputCount(); };
function looksLikeCode(value) {
    // Presentation only. The server independently classifies the original string.
    const declaration = /^\s*(?:const|let|var|string|int|bool|double|decimal)\s+[\p{L}\p{N}_]+\s*=/imu;
    const codeLine = /^\s*(?:(?:def|async\s+def|class)\s+\w+[^\n]*[:{]\s*$|(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(|(?:const|let|var|string|int|bool|double|decimal)\s+\w+\s*=|(?:public|private|protected|internal)\s+(?:static\s+)?(?:class|void|async|Task|[A-Z]\w*)\b|(?:from\s+[\w.]+\s+import\s+|import\s+(?:[\w.]+|[{'\"])|using\s+[\w.]+\s*;)|(?:SELECT\s+.+\s+FROM\b|INSERT\s+INTO\b|CREATE\s+TABLE\b|UPDATE\s+\w+\s+SET\b)|(?:console\.(?:log|error)|print|Assert\.\w+|assert\.\w+)\s*\(|(?:if|for|while)\s*\([^\n]*\)\s*[{:]|(?:handle|reverse_proxy|server|location)\s+[^\n]*[{}]|(?:return|throw)\s+[^\n]+;\s*$)/im;
    if (/^\s{0,3}(?:`{3,}|~{3,})/m.test(value) || declaration.test(value) || codeLine.test(value) || /^\s*<([A-Za-z][\w:-]*)\b[^>]*>[\s\S]*<\/\1>\s*$/i.test(value)) return true;
    if (/^\s*[\[{]/.test(value)) { try { const parsed = JSON.parse(value); return parsed !== null && typeof parsed === 'object'; } catch {} }
    return false;
}
function updateInputCount(save=true) {
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
    $('send').disabled = !state.project || state.project.access === 'reader' || state.busy || Boolean(recovery.pending) || !value.trim();
    if(save!==false)recovery.capture();
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
    if(recovery.pending)throw Error('Consulte o envio anterior antes de iniciar outro.');
    if($('response-mode').value!=='model')$('response-mode').value='auto';
    const pending={request_id:window.LocalAuthorRecovery.uuid(),conversation_id:state.conversation?.id||window.LocalAuthorRecovery.uuid(),message,mode:$('response-mode').value};
    busy(true);try{await recovery.prepare(pending);await sendPending(pending);}catch(error){recovery.requestState('unknown','Envio não confirmado. Seu pedido foi preservado. Use Consultar pedido.');throw error;}finally{busy(false);}
});

const lookupRequest = pending => api('/api/chat-request?project_id='+state.project.id+'&request_id='+pending.request_id,undefined,{signal:AbortSignal.timeout(8000)});
async function finishRequest(result) {
    state.conversation=result;renderMessages();await recovery.complete(result);await renderConversations();
    const browserMessage=result.messages?.at(-1)?.metadata?.browser_session_id;if(browserMessage)await openBrowserSession(browserMessage);
    if(voiceChat?.active)voiceChat.reply(result.messages.at(-1)?.content||'');
}
async function sendPending(pending) {
    try{state.conversation=await api('/api/conversation?project_id='+state.project.id+'&id='+pending.conversation_id,undefined,{signal:AbortSignal.timeout(8000)});}
    catch(error){if(error.status!==404)throw error;state.conversation=await api('/api/conversations',{project_id:state.project.id,id:pending.conversation_id,title:Array.from(pending.message.trim()).slice(0,70).join('')},{signal:AbortSignal.timeout(8000)});}
    const response=await api('/api/chat',{project_id:state.project.id,conversation_id:pending.conversation_id,request_id:pending.request_id,message:pending.message,mode:pending.mode,input_format:'auto'},{signal:AbortSignal.timeout(20000)});
    if(!response.job){await finishRequest(response);return;}
    state.jobId=response.job.id;await pollRequest(pending);
}
async function pollRequest(pending) {
    for(let i=0;i<180;i++){
        const request=await lookupRequest(pending);state.jobId=request.job_id;
        if(request.state==='completed'){await finishRequest(request.result);return;}
        recovery.requestState(request.state,['failed','cancelled','interrupted'].includes(request.state)?'Pedido encerrado sem conclusão. Pode haver trabalho parcial; confira antes de preparar nova tentativa.':'O servidor continua trabalhando. Você pode fechar e acompanhar ao reabrir.');
        if(['failed','cancelled','interrupted'].includes(request.state))return;
        await new Promise(resolve=>setTimeout(resolve,1000));
    }
    recovery.requestState('running','O servidor ainda não concluiu. Use Consultar pedido ou Parar tarefa; o pedido não será reenviado.');
}
async function recoverRequest() {
    const pending=recovery.pending;if(!pending||state.requestBusy)return;
    busy(true);try{
        const request=await lookupRequest(pending);state.jobId=request.job_id;
        if(request.state==='completed')await finishRequest(request.result);
        else recovery.requestState(request.state,['failed','cancelled','interrupted'].includes(request.state)?'Pedido encerrado sem conclusão. Pode haver trabalho parcial; confira antes de preparar nova tentativa.':'O servidor continua trabalhando. Use Consultar pedido para acompanhar ou Parar tarefa para solicitar o cancelamento.');
    }catch(error){recovery.requestState('unknown',error.status===404?'O servidor ainda não confirmou este envio. Ele não foi reenviado.':'Não foi possível consultar o pedido. Seu texto continua salvo.');}finally{state.jobId=null;busy(false);}
}
async function retryRequest() {
    const pending=recovery.pending;if(!pending||state.busy)return;
    busy(true);try{await recovery.flushRemote();await sendPending(pending);}catch(error){recovery.requestState('unknown',error.message);throw error;}finally{state.jobId=null;busy(false);}
}
$('show-rules').onclick = handle(async () => { if (!state.project)
    throw Error('Escolha um projeto primeiro.'); const data = await api('/api/project-preferences?project_id=' + state.project.id); $('method').value = data.method; $('wip').value = data.wip_limit; $('done').value = data.definition_of_done; $('work-profile').value = data.work_profile || 'general'; $('quality-rules').replaceChildren(...data.quality.map(rule => el('li', rule))); $('official-sources').replaceChildren(...data.sources.map(source => { const a = el('a', source.title + ' ↗'); a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; })); const report = await api('/api/engineering-report'); $('learning-result').textContent = report.evaluation ? `Curso experimental: ${report.evaluation.passed}/${report.evaluation.total} decisões guiadas aprovadas. ${report.limitations}` : 'Novo currículo em preparação. As orientações acima foram escritas e revisadas; não significam domínio adquirido pelo modelo.'; const writing = await api('/api/communication-report').catch(() => ({})); if (writing.evaluation?.total) { $('learning-result').textContent += ` Escrita: ${writing.evaluation.passed}/${writing.evaluation.total} pedidos reformulados. ${writing.chatEnabled ? 'Candidato experimental habilitado.' : 'Candidato não ativado no chat.'}`; } $('rules-dialog').showModal(); });
$('rules-form').onsubmit = handle(async () => { const saved=window.LocalAuthorUpdateReadiness?.checkpoint($('rules-form')); await api('/api/project-preferences', { project_id: state.project.id, method: $('method').value, wip_limit: Number($('wip').value), definition_of_done: $('done').value, work_profile: $('work-profile').value }); saved?.(); $('rules-dialog').close(); toast('Orientações salvas para este projeto.'); });
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.querySelector('dialog[open]')) {
        if ($('sidebar').classList.contains('open')) { closeNavigation(); $('open-menu').focus(); }
        else if (!$('browser-panel').hidden) { hideBrowserPanel(); $('open-browser').focus(); }
    }
    if (event.key === 'Tab' && mobileNavigation.matches && $('sidebar').classList.contains('open')) {
        const nodes = [...$('sidebar').querySelectorAll('button:not(:disabled),select:not(:disabled),a[href],summary')].filter(node => node.getClientRects().length);
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
    const saved=window.LocalAuthorUpdateReadiness?.checkpoint($('browser-open-form'));
    try {
        const row=await api('/api/browser/start',{project_id:state.project.id,url:$('browser-url').value.trim(),allow_network:true,
            asset_hosts:$('browser-hosts').value.split(',').map(s=>s.trim()).filter(Boolean),
            auth_hosts:$('browser-auth-hosts').value.split(',').map(s=>s.trim()).filter(Boolean)});
        saved?.();
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
    let source = null, sink = null, timer = null, request = null, abort = null, voice = null, resumeSpeech = null, speechTimer = null, prepareJob = null;
    const status = value => { phase = value; $('voice-status').textContent = value; };
    const syncControls = () => {
        $('voice-start').disabled = !state.project || state.project.access==='reader' || (state.busy && !active);
        $('voice-start').setAttribute('aria-pressed', String(active));
        $('voice-start').title = active ? 'Encerrar conversa por voz' : 'Conversar por voz';
        $('voice-bar').hidden = !active;
        $('voice-stop').disabled = false; $('voice-mute').disabled = false;
        $('voice-mute').setAttribute('aria-pressed', String(muted));
        $('voice-mute').textContent = muted ? 'Ouvir respostas' : 'Silenciar resposta';
        $('voice-interrupt').hidden = !resumeSpeech;
        $('voice-interrupt').disabled = !resumeSpeech;
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
        request = null; resumeSpeech = null; clearTimeout(speechTimer); speechTimer = null; window.speechSynthesis?.cancel();
        if (state.jobId && state.token) api('/api/jobs/' + state.jobId + '/cancel', {}).catch(() => {});
        if (prepareJob && state.token) api('/api/jobs/' + prepareJob + '/cancel', {}).catch(() => {});
        prepareJob = null;
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
            $('response-mode').value = 'auto'; modeNotice(); busy(false); syncControls();
            await listen(version, true);
        } finally { $('voice-confirm').disabled = false; }
    }
    async function listen(version = epoch, prepare = false) {
        if (!active || version !== epoch) return;
        status('Ouvindo… Faça uma pausa para enviar.');
        let stage = 'microphone';
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
            // Capture is connected BEFORE awaiting network/queue work, so the
            // first words cannot disappear while the model starts loading.
            if (prepare) {
                stage = 'prepare';
                const prepared = await api('/api/voice/prepare', {project_id: state.project.id});
                if (!active || version !== epoch) {
                    api('/api/jobs/' + prepared.job.id + '/cancel', {}).catch(() => {}); return;
                }
                prepareJob = prepared.job.id;
            }
        } catch (error) {
            if (active && version === epoch) stop(stage === 'prepare' ? 'Não consegui preparar a conversa: ' + error.message : error.name === 'NotAllowedError' ? 'Permita o microfone nas configurações do aplicativo ou navegador.' : 'Não consegui abrir o microfone. Confira o dispositivo de áudio.');
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
        prepareJob = null;
        const version = epoch;
        if (muted) { listen(version); return; }
        const spoken = text.replace(/```[\s\S]*?```|~~~[\s\S]*?~~~/g, ' Há um trecho de código na resposta; consulte o chat. ').trim();
        if (!spoken) { listen(version); return; }
        status('Falando… O microfone está desligado.');
        const utterance = new SpeechSynthesisUtterance(spoken.slice(0, 1800) + (spoken.length > 1800 ? ' A resposta completa está no chat.' : ''));
        utterance.voice = voice; utterance.lang = voice.lang; utterance.rate = 1;
        let finished = false;
        const finish = () => {
            if (finished || version !== epoch) return; finished = true; clearTimeout(speechTimer); speechTimer = null;
            resumeSpeech = null; syncControls(); if (active && version === epoch) listen(version);
        };
        resumeSpeech = finish;
        syncControls();
        utterance.onend = finish;
        utterance.onerror = event => { if (muted || event.error === 'interrupted' || event.error === 'canceled') finish(); else if (active && version === epoch) stop('Não consegui ler a resposta. O texto completo permanece no chat.'); };
        speechSynthesis.cancel();
        // Some platform readers never deliver onend/onerror. Do not leave the
        // conversation permanently busy or silently reopen a microphone.
        speechTimer = setTimeout(() => {
            if (!finished && active && version === epoch) {
                finished = true; stop('A leitura demorou demais. A resposta está no chat; inicie a voz novamente para continuar.');
            }
        }, Math.min(180000, Math.max(15000, utterance.text.length * 100)));
        try { speechSynthesis.speak(utterance); }
        catch { stop('Não consegui iniciar a leitura. A resposta completa permanece no chat.'); }
    }
    $('voice-start').onclick = () => {
        if (active) { stop('Conversa por voz encerrada.'); return; }
        $('voice-setup').textContent = ''; $('voice-dialog').showModal();
    };
    $('voice-confirm').onclick = async () => { try { await start(); } catch (error) { $('voice-setup').textContent = error.message; stop(); } };
    $('voice-stop').onclick = () => stop('Conversa por voz encerrada.');
    $('voice-interrupt').onclick = () => { const next = resumeSpeech; speechSynthesis.cancel(); next?.(); };
    $('voice-mute').onclick = () => { muted = !muted; syncControls(); if (muted) { const next = resumeSpeech; speechSynthesis.cancel(); next?.(); } };
    $('voice-dialog').addEventListener('close', () => { if (!active) ++epoch; });
    document.addEventListener('visibilitychange', () => { if (document.hidden && active) stop('Voz encerrada porque o aplicativo ficou em segundo plano.'); });
    window.addEventListener('pagehide', () => stop());
    return {get active() { return active; }, start, stop, reply, syncControls};
})();
voiceChat.syncControls();
