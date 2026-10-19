"use strict";
// Shared by every workspace. Device transport and personal sessions stay separate.
(() => {
  const originalFetch = window.fetch.bind(window);
  const channel = typeof BroadcastChannel === "function" ? new BroadcastChannel("localauthor-profile") : null;
  let user = null, initialized = false, gatePromise = null, auth = {}, gate = null;
  const node = (tag, text, cls) => { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; };
  function field(form,label,id,type="text",required=true) {
    const wrap=node("label",label), input=node("input");input.id=id;input.type=type;input.required=required;
    input.maxLength=type==="password"?256:80;wrap.append(input);form.append(wrap);return input;
  }
  function select(form,label,values,value) {
    const wrap=node("label",label), input=node("select");
    for(const [key,text] of values)input.append(new Option(text,key));input.value=value;wrap.append(input);form.append(wrap);return input;
  }
  function button(parent,text,fn) { const b=node("button",text);b.type="button";b.onclick=fn;parent.append(b);return b; }
  function message(parent) { const n=node("p",null,"identity-status");n.setAttribute("role","status");parent.append(n);return n; }
  function dialog(title,id) {
    const old=document.getElementById(id);if(old)old.remove();
    const d=node("dialog",null,"identity-dialog");d.id=id;const h=node("h2",title);h.id=id+"-title";d.setAttribute("aria-labelledby",h.id);d.append(h);document.body.append(d);return d;
  }
  async function request(path,body) {
    const response=await originalFetch(path,{method:body===undefined?"GET":"POST",credentials:"same-origin",cache:"no-store",
      headers:{...auth,...(user?{"X-LocalAuthor-Profile":user.id}:{}),...(body===undefined?{}:{"Content-Type":"application/json"})},
      ...(body===undefined?{}:{body:JSON.stringify(body)})});
    const data=await response.json();if(!response.ok){
      if(data.identity_required&&!['/api/identity/status','/api/identity/login','/api/identity/setup','/api/identity/identify'].includes(path)){lock();changed();location.reload();}
      const error=Error(data.error||"Não foi possível concluir.");error.status=response.status;error.identity=data.identity_required;throw error;
    }return data;
  }
  function lock() { document.body.classList.add("identity-locked"); }
  function changed(id=null) { channel?.postMessage({type:"changed",id}); }
  function mount() {
    let control=document.getElementById("identity-menu");
    if(!control){control=node("button",null,"identity-menu");control.id="identity-menu";control.type="button";
      (document.querySelector(".sidebar-bottom")||document.querySelector("header")||document.body).prepend(control);
      control.onclick=()=>account().catch(error=>window.alert(error.message));}
    control.textContent=user.name+" · Meu perfil";control.title="Trocar ou organizar seu perfil";
    document.dispatchEvent(new CustomEvent("localauthor-profile",{detail:user}));
  }
  async function promptIdentity(status) {
    const previousDirty=Boolean(window.__localAuthorUpdateDirty);
    lock();document.querySelectorAll("dialog[open]").forEach(d=>d.close());
    gate=dialog("Quem está usando a LocalAuthor?","identity-gate");
    gate.addEventListener("cancel",e=>e.preventDefault());
    if(!status.configured&&!status.can_setup){
      gate.append(node("p","Crie o primeiro perfil no aplicativo da máquina servidor. Depois, cada pessoa poderá escolher ou informar seu nome aqui."));
      button(gate,"Verificar novamente",()=>location.reload());gate.showModal();return new Promise(()=>{});
    }
    const setup=!status.configured;
    gate.append(node("p",setup?"Informe seu nome para organizar seus projetos. Os projetos e históricos existentes ficarão no primeiro perfil.":"Escolha seu nome ou informe um novo para criar seu espaço de projetos e conversas."));
    gate.append(node("p","Sem senha: os perfis organizam o trabalho. Quem usa este aplicativo pode escolher outro perfil.","identity-hint"));
    const form=node("form");gate.append(form);
    const profiles=status.profiles||[];
    let selected=null;
    if(profiles.length){selected=select(form,"Perfis deste servidor",[["","Escolher meu nome"],...profiles.map(p=>[p.id,p.name])],"");selected.id="identity-profile";}
    const name=field(form,"Seu nome","identity-name");name.autocomplete="name";name.placeholder="Use nome e sobrenome para evitar confusão";
    if(selected)selected.onchange=()=>{name.value=profiles.find(p=>p.id===selected.value)?.name||"";name.focus();};
    const submit=node("button",setup?"Criar meu perfil":"Continuar","primary");submit.id="identity-submit";form.append(submit);const notice=message(form);
    gate.dataset.setup=String(setup);gate.showModal();(selected||name).focus();
    return new Promise(resolve=>{
      form.onsubmit=async event=>{
        event.preventDefault();if(submit.disabled)return;
        submit.disabled=true;notice.textContent=setup?"Criando perfil e preservando seus projetos…":"Abrindo seu perfil…";
        try{
          const result=await request("/api/identity/identify",{name:name.value});
          gate.close();gate.remove();gate=null;document.body.classList.remove("identity-locked");
          // Older native clients mark profile selection as an edited form.
          window.__localAuthorUpdateDirty=previousDirty;
          changed(result.user.id);resolve(result.user);
        }catch(error){notice.textContent=error.message;}
        finally{submit.disabled=false;}
      };
    });
  }
  async function ensure(headers={}) {
    const bearer=new Headers(headers).get("Authorization");if(bearer)auth={Authorization:bearer};
    if(initialized)return user;
    if(!gatePromise)gatePromise=(async()=>{
      let status;
      try{status=await request("/api/identity/status");}catch(error){if(error.status===401&&!error.identity)return null;throw error;}
      user=status.user||await promptIdentity(status);initialized=true;mount();return user;
    })().finally(()=>{gatePromise=null;});
    return gatePromise;
  }
  async function logout() { await request("/api/identity/logout",{});user=null;initialized=false;lock();changed();location.reload(); }
  function formAction(form,notice,fn) {
    form.onsubmit=async event=>{event.preventDefault();const b=form.querySelector('button[type="submit"]')||form.querySelector("button");b.disabled=true;
      try{notice.textContent="Salvando…";await fn();}catch(error){notice.textContent=error.message;}finally{b.disabled=false;}};
  }
  async function account() {
    const d=dialog("Meu perfil","identity-account");button(d,"Fechar",()=>d.close());
    d.append(node("p",user.name));
    const folder=node("details");folder.append(node("summary","Minha pasta no servidor"),node("p",user.workspace));d.append(folder);
    button(d,"Trocar perfil",()=>logout().catch(error=>window.alert(error.message)));
    d.append(node("p","Os perfis organizam projetos e conversas por nome. Eles não têm senha nem impedem que outra pessoa escolha seu perfil.","identity-hint"));
    if(user.role==="admin"){
      const section=node("section");section.id="identity-admin";section.append(node("h3","Pessoas da equipe"),node("p","Você pode preparar os perfis da equipe aqui. Cada pessoa também pode informar seu nome na entrada e criar o próprio espaço."));d.append(section);
      const create=node("form");create.id="identity-create-user";section.append(create);
      const name=field(create,"Nome da pessoa","identity-user-name");
      const role=select(create,"Permissão no servidor",[["user","Pessoa da equipe"],["admin","Administrador"]],"user");
      create.append(node("button","Adicionar pessoa"));const state=message(create),list=node("div");list.id="identity-users";section.append(list);
      async function renderUsers(){
        const users=await request("/api/identity/users");list.replaceChildren();
        for(const person of users){
          const row=node("form",null,"identity-user-row");row.dataset.userId=person.id;
          row.append(node("strong",person.name));const name=field(row,"Nome","profile-name-"+person.id);name.value=person.name;
          const role=select(row,"Permissão",[["user","Pessoa da equipe"],["admin","Administrador"]],person.role);
          const enabled=field(row,"Perfil ativo","profile-active-"+person.id,"checkbox",false);enabled.checked=Boolean(person.active);
          row.append(node("button","Salvar perfil"));const status=message(row);list.append(row);
          formAction(row,status,async()=>{await request("/api/identity/users/update",{id:person.id,name:name.value,role:role.value,active:enabled.checked});status.textContent="Perfil atualizado.";});
        }
      }
      formAction(create,state,async()=>{await request("/api/identity/users",{name:name.value,role:role.value});create.reset();state.textContent="Pessoa cadastrada. Ela já pode escolher seu nome ao abrir a LocalAuthor.";await renderUsers();});
      await renderUsers();
    }
    d.showModal();
  }
  async function openSharing(project) {
    const d=dialog("Compartilhar projeto","identity-sharing");button(d,"Fechar",()=>d.close());
    d.append(node("h3",project.name),node("p","Compartilhar dá acesso ao histórico e às fontes deste projeto. Leitura permite consultar; edição também permite conversar e alterar o conteúdo. Somente o proprietário gerencia os acessos."));
    const form=node("form");d.append(form);const people=await request("/api/identity/directory");
    const who=select(form,"Pessoa",people.filter(p=>p.id!==user.id).map(p=>[p.id,p.name]),"");who.id="identity-share-user";who.required=true;
    const role=select(form,"Acesso",[["reader","Somente leitura"],["editor","Pode editar"]],"reader");role.id="identity-share-role";
    form.append(node("button","Compartilhar"));const status=message(form),list=node("div");list.id="identity-members";d.append(list);
    async function members(){
      const rows=await request("/api/project-members?project_id="+encodeURIComponent(project.id));list.replaceChildren();
      for(const person of rows){const row=node("div",null,"identity-member");row.dataset.userId=person.id;row.append(node("span",person.name+" · "+(person.access==="owner"?"Proprietário":person.access==="editor"?"Pode editar":"Somente leitura")));
        if(person.access!=="owner")button(row,"Remover acesso",async()=>{try{await request("/api/project-members",{project_id:project.id,user_id:person.id,role:"none"});await members();}catch(error){status.textContent=error.message;}});list.append(row);}
    }
    formAction(form,status,async()=>{await request("/api/project-members",{project_id:project.id,user_id:who.value,role:role.value});status.textContent="Acesso compartilhado.";await members();});
    await members();d.showModal();
  }
  window.LocalAuthorIdentity={ensure,logout,openSharing,get user(){return user;}};
  window.fetch=async(input,init={})=>{
    const url=new URL(typeof input==="string"?input:input.url,location.href);
    if(url.origin!==location.origin||!url.pathname.startsWith("/api/")||url.pathname.startsWith("/api/identity/")||url.pathname==="/api/project-members")return originalFetch(input,init);
    // Native update endpoints have their own device/publication credentials.
    if(url.pathname.startsWith('/api/client-update')||url.pathname==='/api/device'||url.pathname==='/api/publication-password')return originalFetch(input,init);
    await ensure(init.headers);
    const headers=new Headers(init.headers);if(user)headers.set("X-LocalAuthor-Profile",user.id);
    const response=await originalFetch(input,{...init,headers});
    if(response.status===401){const data=await response.clone().json().catch(()=>({}));if(data.identity_required){
      const previous=user?.id;lock();user=null;initialized=false;
      const restored=await ensure(init.headers);
      if(restored?.id===previous){headers.set('X-LocalAuthor-Profile',restored.id);return originalFetch(input,{...init,headers});}
      lock();location.reload();throw Error('O perfil mudou. A solicitação anterior não foi reenviada.');
    }}
    return response;
  };
  channel?.addEventListener("message",e=>{if(e.data?.type==="changed"&&initialized&&e.data.id!==user?.id){lock();location.reload();}});
  document.addEventListener("click",event=>{if(user&&event.target.closest?.("#logout")){event.preventDefault();event.stopImmediatePropagation();logout().catch(error=>window.alert(error.message));}},true);
})();
