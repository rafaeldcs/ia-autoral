"use strict";
// Durable local snapshots plus versioned server copies. This module never sends
// a chat command on startup: recovery reads the accepted-request journal only.
window.LocalAuthorRecovery = (() => {
  const uuid = () => crypto.randomUUID().replaceAll('-', '');
  const modes = new Set(['guide','knowledge','model','foundation','image','investigation','browser']);
  let database;
  function db() {
    if (!database) database = new Promise((resolve, reject) => {
      const request = indexedDB.open('localauthor-chat-recovery', 1);
      request.onupgradeneeded = () => {
        const drafts = request.result.createObjectStore('drafts', {keyPath:'key'});
        drafts.createIndex('profile', 'profile');
        request.result.createObjectStore('selection', {keyPath:'profile'});
      };
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(Error('Feche as outras janelas para preparar a recuperação.'));
      request.onsuccess = () => resolve(request.result);
    });
    return database;
  }
  function transaction(database, stores, mode) {
    // A completed strict transaction is the local "saved" boundary. An abrupt
    // shutdown before this acknowledgement can still lose the newest edit.
    try { return database.transaction(stores, mode, {durability:'strict'}); }
    catch (error) { if (!(error instanceof TypeError)) throw error; return database.transaction(stores, mode); }
  }
  async function read(store, key, index) {
    const database = await db();
    return new Promise((resolve, reject) => {
      const tx = transaction(database, [store], 'readonly');
      const source = index ? tx.objectStore(store).index(index) : tx.objectStore(store);
      const request = index ? source.getAll(key) : source.get(key);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async function putSelection(selection) {
    const database = await db();
    return new Promise((resolve, reject) => {
      const tx = transaction(database, ['selection'], 'readwrite');tx.objectStore('selection').put(selection);
      tx.oncomplete = resolve;tx.onabort = () => reject(tx.error || Error('Seleção local não salva.'));
    });
  }
  async function putDraft(record, parent) {
    if (record.text.length > 100000) throw Error('Rascunho grande demais para a cópia local. Copie seu texto antes de fechar.');
    const database = await db();
    return new Promise((resolve, reject) => {
      const tx = transaction(database, ['drafts','selection'], 'readwrite');
      const drafts = tx.objectStore('drafts');
      const count = drafts.index('profile').getAll(record.profile);
      count.onsuccess = () => {
        const active=count.result.filter(row=>row.text||row.pending||row.dirty);
        if ((record.text||record.pending||record.dirty) && active.length >= 200 && !active.some(row=>row.key===record.key)) { tx.abort(); return; }
        if (parent && parent.key !== record.key) {
          const previous = drafts.get(parent.key);
          previous.onsuccess = () => { if (previous.result?.version === parent.version) drafts.delete(parent.key); };
        }
        // Keep a small empty tombstone too: it prevents an older conflict copy
        // from becoming the current draft after the latest message was sent.
        drafts.put(record);
        tx.objectStore('selection').put({profile:record.profile,project_id:record.project,conversation_id:record.conversation,updated:record.updated});
      };
      tx.oncomplete = resolve;
      tx.onabort = () => reject(tx.error || Error('Não foi possível salvar a cópia local. Libere espaço ou revise os rascunhos.'));
    });
  }
  const valid = row => row && typeof row.text==='string' && modes.has(row.mode) && typeof row.revision==='number';

  function create(deps) {
    let context = null, localChain = Promise.resolve(), syncChain = Promise.resolve(), timer, opening = false;
    let lastError = '', localError = '', phase = '', alternatives = [];
    const strip = document.createElement('div');strip.id='chat-recovery';strip.className='chat-recovery';strip.hidden=true;
    const label = document.createElement('span');label.id='draft-status';label.setAttribute('role','status');strip.append(label);
    deps.input.closest('form').after(strip);
    const controls = document.createElement('span');controls.className='recovery-actions';strip.append(controls);
    const profile = () => window.LocalAuthorIdentity?.user?.id || 'local';
    const api = (path, body) => deps.api(path, body, {signal:AbortSignal.timeout(8000)});
    function button(text, action) {
      const node=document.createElement('button');node.type='button';node.textContent=text;
      node.onclick=async()=>{node.disabled=true;try{await action();}catch(error){deps.notice(error.message);}finally{node.disabled=false;}};
      controls.append(node);
    }
    function render() {
      strip.hidden=!context;controls.replaceChildren();if(!context)return;
      label.textContent=phase || (localError ? 'Cópia local indisponível. '+(context.dirty?'Salvamento no servidor pendente.':'Rascunho salvo no servidor.') : lastError ? 'Salvo neste computador; sincronização pendente.' : context.dirty ? 'Salvando rascunho…' : context.text ? 'Rascunho salvo.' : 'Salvamento automático ativo.');
      if (context.conflict) label.textContent='Há outro rascunho. Suas versões foram preservadas; compare antes de substituir.';
      if (context.pending) {
        label.textContent=phase || 'Pedido pendente. Consulte o servidor antes de enviar novamente.';
        button('Consultar pedido',()=>deps.inspect());
        if(context.requestState==='unknown'&&!deps.readOnly())button('Reenviar com segurança',()=>deps.retry());
        if(['failed','cancelled','interrupted'].includes(context.requestState)&&!deps.readOnly())button('Preparar nova tentativa',async()=>{context.pending=null;phase='Pedido anterior não será repetido. Revise a mensagem e clique em Enviar.';capture(true);await flushRemote();deps.changed();});
        if(['queued','running'].includes(context.requestState)&&!deps.readOnly())button('Parar tarefa',()=>deps.cancel());
      }
      if(context.conflict || alternatives.length)button('Ver versões',versions);
      if(context.text && !context.pending && !context.conflict)button('Descartar rascunho',async()=>{
        if(!window.confirm('Descartar este rascunho? As mensagens já enviadas continuam no histórico.'))return;
        deps.write('',context.mode);capture(true);await flushRemote();
      });
      strip.dataset.saved=(!context.dirty&&!lastError&&!localError).toString();
    }
    const snapshot = ctx => ({key:ctx.key,profile:ctx.profile,project:ctx.project,conversation:ctx.conversation,
      text:ctx.text,mode:ctx.mode,pending:ctx.pending,revision:ctx.revision,dirty:ctx.dirty,version:ctx.version,updated:Date.now()});
    function persist(ctx) {
      const row=snapshot(ctx),parent=ctx.parent;
      localChain=localChain.catch(()=>{}).then(()=>putDraft(row,parent)).then(()=>{if(context===ctx){localError='';render();}}).catch(error=>{if(context===ctx){localError=error.message;render();}});
      return localChain;
    }
    function capture(force=false) {
      if(!context || opening || context.profile!==profile() || deps.readOnly())return;
      const text=deps.input.value,mode=deps.mode.value;
      if(!force && text===context.text && mode===context.mode)return;
      context.text=text;context.mode=mode;context.version++;context.dirty=true;phase='';persist(context);render();
      clearTimeout(timer);timer=setTimeout(()=>sync().catch(()=>{}),400);
    }
    async function sync() {
      const ctx=context;
      syncChain=syncChain.catch(()=>{}).then(async()=>{
        if(!ctx || !ctx.dirty || ctx.conflict || deps.readOnly() || ctx.profile!==profile())return;
        const version=ctx.version;
        try {
          const result=await api('/api/chat-draft',{project_id:ctx.project,conversation_id:ctx.conversation,text:ctx.text,mode:ctx.mode,revision:ctx.revision,pending:ctx.pending});
          ctx.revision=result.revision;ctx.dirty=version!==ctx.version;
          if(context===ctx){lastError='';persist(ctx);render();}
        } catch(error) {
          if(context===ctx){lastError=error.message;if(error.status===409){ctx.conflict=true;ctx.remote=await api('/api/chat-draft?project_id='+ctx.project+'&conversation_id='+ctx.conversation).catch(()=>null);}render();}
          throw error;
        }
      });
      return syncChain;
    }
    async function flushLocal() { capture();await localChain; }
    async function flushRemote() {
      await flushLocal();await sync();await localChain;
      if(context?.conflict)throw Error('Compare as versões do rascunho antes de enviar.');
      if(context?.dirty)throw Error('Ainda não foi possível salvar o rascunho no servidor. Seu texto foi mantido.');
    }
    async function selection() {
      const id=profile();let local,remote;
      try{local=await read('selection',id);}catch(error){localError=error.message;}
      try{remote=(await api('/api/chat-workspace')).selection;}catch(error){lastError=error.message;}
      return local && (!remote || local.updated>Date.parse(remote.updated_at)) ? local : remote;
    }
    async function open(project,conversation='') {
      await flushLocal();clearTimeout(timer);opening=true;phase='';lastError='';alternatives=[];
      const id=profile();let rows=[],remote={text:'',mode:'guide',pending:null,revision:0};
      try{rows=(await read('drafts',id,'profile')).filter(row=>row.project===project&&row.conversation===conversation&&valid(row)).sort((a,b)=>b.updated-a.updated);}catch(error){localError=error.message;}
      try{remote=await api('/api/chat-draft?project_id='+project+'&conversation_id='+conversation);}catch(error){lastError=error.message;}
      const local=rows[0];
      const same=!!local&&local.text===remote.text&&local.mode===remote.mode&&JSON.stringify(local.pending)===JSON.stringify(remote.pending);
      const chosen=local?.dirty ? local : !lastError ? remote : local || remote;
      const writer=uuid();context={profile:id,project,conversation,key:id+'|'+project+'|'+conversation+'|'+writer,version:0,parent:local||null,
        text:chosen.text,mode:chosen.mode,pending:chosen.pending||null,revision:local?.dirty&&!same?local.revision:remote.revision,
        dirty:!!chosen.dirty&&!same,conflict:!!(local?.dirty&&!lastError&&local.revision!==remote.revision&&!same),remote};
      alternatives=rows.filter(row=>row.text!==chosen.text || JSON.stringify(row.pending)!==JSON.stringify(chosen.pending));
      if(context.conflict)alternatives.push({...remote,source:'Servidor'});
      deps.write(context.text,context.mode);opening=false;
      const pointer={profile:id,project_id:project,conversation_id:conversation,updated:Date.now()};
      putSelection(pointer).catch(error=>{localError=error.message;render();});
      api('/api/chat-workspace',{project_id:project,conversation_id:conversation}).catch(error=>{lastError=error.message;render();});
      phase=context.pending?'Conferindo o último pedido…':context.text?'Rascunho recuperado.':'';render();deps.changed();
      if(context.dirty&&!context.conflict)sync().catch(()=>{});
      return context.pending;
    }
    async function prepare(pending) {
      context.pending=pending;context.requestState='unknown';capture(true);await flushRemote();render();return pending;
    }
    function requestState(state,message) { if(!context)return;context.requestState=state;phase=message;render();deps.changed(); }
    async function complete(result) {
      if(!context)return;
      const pending=context.pending;
      if(!pending)return;
      context.pending=null;context.requestState=null;
      if(deps.input.value===pending.message && deps.mode.value===pending.mode)deps.write('',context.mode);
      capture(true);await flushLocal();
      try{await sync();}catch{/* A newer server draft is kept; completed messages remain authoritative. */}
      phase='Resposta salva no histórico.';render();
      if(result.id!==context.conversation)await open(context.project,result.id);
      deps.changed();
    }
    async function versions() {
      if(!context)return;
      await flushLocal();await persist(context);
      const ctx=context,dialog=document.createElement('dialog');dialog.className='recovery-dialog';dialog.id='draft-versions';
      const heading=document.createElement('h2');heading.textContent='Versões do rascunho';dialog.append(heading);
      const explanation=document.createElement('p');explanation.textContent='Compare o texto antes de escolher. Usar uma versão não envia nenhuma mensagem. As outras cópias locais são preservadas.';dialog.append(explanation);
      const candidates=[{...snapshot(ctx),source:'Neste computador'},...alternatives];
      if(ctx.remote && !candidates.some(row=>row.text===ctx.remote.text&&row.mode===ctx.remote.mode))candidates.push({...ctx.remote,source:'Servidor'});
      for(const [index,row] of candidates.entries()){
        const title=document.createElement('h3');title.textContent=row.source||'Cópia local '+index;const text=document.createElement('textarea');text.readOnly=true;text.rows=6;text.value=row.text;
        const choose=document.createElement('button');choose.type='button';choose.textContent='Usar esta versão';
        choose.disabled=deps.readOnly();
        choose.onclick=async()=>{choose.disabled=true;try{
          const fresh=await api('/api/chat-draft?project_id='+ctx.project+'&conversation_id='+ctx.conversation);
          ctx.key=ctx.profile+'|'+ctx.project+'|'+ctx.conversation+'|'+uuid();ctx.parent=null;ctx.revision=fresh.revision;ctx.conflict=false;ctx.pending=row.pending||null;alternatives=[];
          deps.write(row.text,row.mode);capture(true);await flushRemote();dialog.close();dialog.remove();if(ctx.pending)await deps.inspect();
        }catch(error){explanation.textContent=error.message;}finally{choose.disabled=false;}};
        dialog.append(title,text,choose);
      }
      const close=document.createElement('button');close.type='button';close.textContent='Fechar';close.onclick=()=>{dialog.close();dialog.remove();};dialog.append(close);document.body.append(dialog);dialog.showModal();
    }
    window.addEventListener('online',()=>sync().catch(()=>{}));
    document.addEventListener('visibilitychange',()=>{if(document.hidden)capture();});
    window.addEventListener('beforeunload',event=>{if(context?.dirty&&localError){event.preventDefault();event.returnValue='';}});
    return {open,selection,capture,flushLocal,flushRemote,prepare,complete,requestState,
      get pending(){return context?.pending||null;},get ready(){return !opening;},get current(){return context;}};
  }
  return {create,uuid};
})();
