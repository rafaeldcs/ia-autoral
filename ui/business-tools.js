'use strict';

function businessFields(kind) {
  const mappings = {
    campaign: [["impressions","Impressões"],["clicks","Cliques"],["leads","Leads"],["new_clients","Novos clientes"],["spend_cents","Mídia (centavos)"]],
    funnel: [["registrations","Cadastros"],["started","Iniciaram configuração"],["completed","Concluíram configuração"]],
    cash: [["opening_cents","Saldo inicial (centavos)"],["incoming_cents","Entradas (centavos)"],["outgoing_cents","Saídas (centavos)"]]
  };
  return mappings[kind] || [];
}


function businessMoneyCents(value) {
  const trimmed = value.trim();
  const regex = /^(0|[1-9]\d{0,10})([,.]\d{1,2})?$/;
  if (!regex.test(trimmed)) {
    throw new Error("Valor inválido");
  }
  const parts = trimmed.split(/[,.]/);
  const integerPart = parts[0];
  let fractionalPart = parts[1] || "";
  if (fractionalPart.length < 2) {
    fractionalPart += "0".repeat(2 - fractionalPart.length);
  }
  const cents = Number(integerPart) * 100 + Number(fractionalPart);
  if (!Number.isSafeInteger(cents) || cents < 0 || cents > 1000000000000) {
    throw new Error("Valor excede limite máximo");
  }
  return cents;
}


function businessCreateInputs(kind, target) { const fields = businessFields(kind); const labels = fields.map(f => document.createElement('label')); target.replaceChildren(...labels); fields.forEach((f, i) => { const input = document.createElement('input'); input.id = `business-${f[0]}`; input.dataset.metric = f[0]; input.required = true; if (f[1].includes('(centavos)')) { input.type = 'text'; input.inputMode = 'decimal'; input.placeholder = '0,00'; } else { input.type = 'number'; input.min = '0'; input.max = '1000000000000'; input.step = '1'; } labels[i].textContent = f[1].replace('(centavos)', '(R$)'); labels[i].appendChild(input); }); }

function businessReadInputs(kind,target){const fields=businessFields(kind);const result={};for(const[name,label]of fields){const input=target.querySelector(`[data-metric="${name}"]`);if(!input||!input.value.trim()){throw new Error("Preencha todos os campos.");}if(name.endsWith("_cents")){result[name]=businessMoneyCents(input.value);}else{const value=Number(input.value);if(!Number.isSafeInteger(value)||value<0||value>1e12){throw new Error("Valor inválido.");}result[name]=value}}return result;}

function renderBusinessMetrics(report, target) {
  const nodes = [];
  for (const [key, value] of Object.entries(report.metrics)) {
    const p = document.createElement("p");
    let text = "";
    switch (key) {
      case "ctr_percent": text = `CTR (%): ${value ?? "indisponível"}`; break;
      case "cpl_brl": text = `Custo por lead (R$): ${value ?? "indisponível"}`; break;
      case "media_per_client_brl": text = `Custo de mídia por cliente (R$): ${value ?? "indisponível"}`; break;
      case "start_percent": text = `Início/cadastros (%): ${value ?? "indisponível"}`; break;
      case "completion_started_percent": text = `Conclusão/início (%): ${value ?? "indisponível"}`; break;
      case "activation_percent": text = `Conclusão/cadastros (%): ${value ?? "indisponível"}`; break;
      case "not_started": text = `Não iniciaram: ${value ?? "indisponível"}`; break;
      case "started_not_completed": text = `Iniciaram e não concluíram: ${value ?? "indisponível"}`; break;
      case "not_completed": text = `Total sem concluir: ${value ?? "indisponível"}`; break;
      case "balance_cents": text = `Saldo (centavos): ${value ?? "indisponível"}`; break;
      case "balance_brl": text = `Saldo de caixa (R$): ${value ?? "indisponível"}`; break;
    }
    p.textContent = text;
    nodes.push(p);
  }
  const noticeP = document.createElement("p");
  noticeP.textContent = report.notice;
  nodes.push(noticeP);
  target.replaceChildren(...nodes);
}


async function businessSubmit(event,state,els,deps){event.preventDefault();if(!els.form.reportValidity()||!deps.isConnected())return;let project; let stamp=++state.version; project = deps.getProject(); state.report=null; state.reportProject=null; els.use.hidden=true;if(!project){els.result.textContent="Selecione um projeto.";return;}els.button.disabled=true;try{const data=businessReadInputs(els.kind.value,els.fields);const next=await deps.api("/api/foundation/business-metrics",{project_id:project,payload:{kind:els.kind.value,data}});if(stamp!==state.version||project!==deps.getProject()||!deps.isConnected())return;renderBusinessMetrics(next,els.result);state.report=next;state.reportProject=project;els.use.hidden=false;}catch(error){if(stamp===state.version&&deps.isConnected()&&project===deps.getProject())els.result.textContent=error.message;}finally{els.button.disabled=false;}}

function installBusinessTools(deps) {
  const form = document.getElementById("business-form");
  const els = {
    form,
    kind: document.getElementById("business-kind"),
    fields: document.getElementById("business-fields"),
    result: document.getElementById("business-result"),
    use: document.getElementById("business-use"),
    button: form.querySelector("button")
  };
  const state = { version: 0, report: null, reportProject: null };

  function clear() {
    state.version++;
    state.report = null;
    state.reportProject = null;
    els.use.hidden = true;
    els.result.replaceChildren();
  }

  function rebuild() {
    clear();
    form.reset();
    businessCreateInputs(els.kind.value, els.fields);
  }

  els.kind.addEventListener("change", () => {
    clear();
    businessCreateInputs(els.kind.value, els.fields);
  });

  form.addEventListener("input", clear);
  document.getElementById("project").addEventListener("change", rebuild);
  document.getElementById("logout").addEventListener("click", rebuild);
  form.addEventListener("submit", (event) => businessSubmit(event, state, els, deps));
  els.use.addEventListener("click", () => {
    if (!deps.isBusy() && state.report && state.reportProject === deps.getProject() && deps.isConnected()) {
      deps.useReport(state.report);
    }
  });

  rebuild();
}
