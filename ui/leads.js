"use strict";
const $ = (id) => document.getElementById(id);
const labels = {
  new: "Novo",
  research: "Em pesquisa",
  needs_information: "A esclarecer",
  qualified: "Qualificado",
  demonstration: "Demonstração",
  proposal: "Proposta",
  won: "Ganho",
  lost: "Sem encaixe / perdido",
  do_not_contact: "Não contatar",
};
const state = {
  token: "",
  project: "",
  context: null,
  items: [],
  item: null,
  busy: false,
  job: null,
};
const node = (tag, text) => {
  const n = document.createElement(tag);
  n.textContent = text;
  return n;
};
const notice = (text) => {
  $("message").textContent = text;
};
async function api(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: {
      Authorization: "Bearer " + state.token,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok)
    throw Error(
      data.error || "Não consegui concluir. Recarregue e confira o estado.",
    );
  return data;
}
function buttons() {
  document.querySelectorAll("button,input,select,textarea").forEach((e) => {
    e.disabled = state.busy;
  });
  const qualify = $("qualify");
  if (qualify)
    qualify.disabled =
      state.busy ||
      !!state.job ||
      !state.context ||
      state.item?.stage === "do_not_contact";
  const review = $("review");
  if (review)
    review.disabled =
      state.busy || !state.item?.analysis || state.item.analysis_stale;
  const cancel = $("cancel-job");
  if (cancel) cancel.disabled = !state.job;
}
function action(fn) {
  return async (e) => {
    e?.preventDefault();
    if (state.busy) return;
    state.busy = true;
    buttons();
    try {
      await fn(e);
    } catch (error) {
      notice(error.message);
    } finally {
      state.busy = false;
      buttons();
    }
  };
}
function tab(name) {
  for (const n of ["inbox", "context", "intake", "integration"])
    $(n).hidden = n !== name;
  document
    .querySelectorAll("[data-tab]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.tab === name)),
    );
}
const query = () => "?project_id=" + encodeURIComponent(state.project);
const snapshot = () => ({
  project_id: state.project,
  id: state.item.id,
  version: state.item.version,
  context_digest: state.context?.digest,
});
async function openLead(id) {
  state.item = await api(
    "/api/leads/item" + query() + "&id=" + encodeURIComponent(id),
  );
  renderDetail();
  renderList();
}
async function load() {
  const [context, list, relay] = await Promise.all([
    api("/api/leads/context" + query()),
    api("/api/leads" + query()),
    api("/api/leads/relay" + query()),
  ]);
  renderRelay(relay);
  state.context = context;
  state.items = list.items;
  $("metrics").replaceChildren();
  for (const [label, count] of [
    ["Contatos", list.items.length],
    ["A esclarecer", list.counts.needs_information],
    ["Em demonstração", list.counts.demonstration],
    ["Ganhos registrados", list.counts.won],
  ]) {
    const card = node("div", "");
    card.className = "metric";
    card.append(node("strong", count), node("span", label));
    $("metrics").append(card);
  }
  $("campaigns").replaceChildren();
  for (const [name, group] of Object.entries(list.campaigns)) {
    const row = node("div", "");
    row.className = "campaign-row";
    row.append(
      node("span", name),
      node(
        "span",
        `${group.leads} contatos · ${group.won} ganhos · ${group.research} pesquisas`,
      ),
    );
    $("campaigns").append(row);
  }
  fillContext();
  renderList();
  if (state.item) await openLead(state.item.id);
}
function renderList() {
  const term = $("search").value.toLocaleLowerCase();
  const stage = $("filter").value;
  $("lead-list").replaceChildren();
  const items = state.items.filter(
    (i) =>
      (!stage || i.stage === stage) &&
      [i.company, i.name, i.email, i.phone]
        .join(" ")
        .toLocaleLowerCase()
        .includes(term),
  );
  for (const item of items) {
    const row = node("button", "");
    row.type = "button";
    row.className = "lead-row";
    row.setAttribute("aria-current", String(state.item?.id === item.id));
    row.append(
      node("strong", item.company || item.name || "Contato sem nome"),
      node("small", labels[item.stage]),
      node("small", item.email || item.phone || "Sem contato informado"),
    );
    row.onclick = action(() => openLead(item.id));
    $("lead-list").append(row);
  }
  if (!items.length)
    $("lead-list").append(
      node(
        "p",
        "Nenhum interessado nesta seleção. Adicione uma entrada para começar.",
      ),
    );
  buttons();
}
function renderDetail() {
  const item = state.item;
  const box = $("detail");
  box.replaceChildren();
  if (!item) return;
  box.append(node("h2", item.company || item.name || "Contato sem nome"));
  const badge = node("span", labels[item.stage]);
  badge.className = "pill";
  box.append(
    badge,
    node("p", [item.name, item.email, item.phone].filter(Boolean).join(" · ")),
    node("h3", "Mensagem / observação"),
    node("p", item.last_message),
  );
  const actions = node("div", "");
  actions.className = "actions";
  const qualify = node("button", "Analisar com a IA local");
  qualify.id = "qualify";
  qualify.onclick = action(async () => {
    if (state.job)
      throw Error(
        "Retome a consulta da análise anterior antes de pedir outra.",
      );
    const result = await api("/api/leads/qualify", snapshot());
    state.job = result.job.id;
    renderDetail();
    await poll();
  });
  actions.append(qualify);
  if (state.job) {
    const resume = node("button", "Retomar consulta");
    resume.onclick = action(poll);
    const cancel = node("button", "Cancelar análise");
    cancel.id = "cancel-job";
    cancel.className = "secondary";
    cancel.onclick = async () => {
      try {
        await api("/api/jobs/" + state.job + "/cancel", {});
        notice("Cancelamento solicitado. Os dados permanecem preservados.");
      } catch (e) {
        notice(e.message);
      }
    };
    actions.append(resume, cancel);
  }
  box.append(actions);
  if (!state.context)
    box.append(node("p", "Configure o contexto da empresa antes de analisar."));
  if (item.stage === "do_not_contact")
    box.append(
      node(
        "p",
        "Este contato está bloqueado para campanhas. A IA não pode reativá-lo.",
      ),
    );
  const analysis = item.analysis;
  if (analysis) {
    box.append(
      node("h3", "Análise para sua revisão"),
      node("p", "Sugestão: " + labels[analysis.suggested_stage]),
    );
    if (item.analysis_stale)
      box.append(
        node(
          "p",
          "Contexto atualizado: esta análise está desatualizada. Solicite uma nova.",
        ),
      );
    for (const fact of analysis.facts) {
      const p = node("p", fact.text + " ");
      const a = node("a", "Fonte conferida em " + fact.checked_at);
      a.href = fact.url;
      a.target = "_blank";
      a.rel = "noreferrer noopener";
      p.append(a);
      box.append(p);
    }
    for (const question of analysis.questions)
      box.append(node("p", "Pergunta sugerida: " + question));
    box.append(
      node("h3", "Rascunho para atendimento"),
      node(
        "p",
        analysis.draft ||
          "Sem rascunho: não há preferência de contato registrada, é uma pesquisa, há recusa ou falta de encaixe.",
      ),
    );
    const review = node(
      "button",
      "Conferi as evidências e o rascunho — aplicar",
    );
    review.id = "review";
    review.onclick = action(async () => {
      state.item = await api("/api/leads/review", {
        ...snapshot(),
        analysis_digest: analysis.digest,
        reviewed: true,
      });
      await load();
      notice("Revisão registrada. Nenhuma mensagem foi enviada.");
    });
    box.append(review);
    const rejection = node("details", "");
    rejection.append(node("summary", "A análise precisa de correção?"));
    const rejectForm = node("form", "");
    const rejectLabel = node("label", "Explique o que a IA precisa corrigir");
    const rejectNote = document.createElement("textarea");
    rejectNote.required = true;
    rejectNote.maxLength = 500;
    rejectNote.rows = 2;
    rejectLabel.append(rejectNote);
    const rejectButton = node(
      "button",
      "Rejeitar análise e registrar orientação",
    );
    rejectButton.className = "secondary";
    rejectForm.append(rejectLabel, rejectButton);
    rejectForm.onsubmit = action(async () => {
      state.item = await api("/api/leads/reject", {
        project_id: state.project,
        id: item.id,
        version: item.version,
        note: rejectNote.value,
      });
      await load();
      notice(
        "Análise rejeitada e preservada no histórico. A próxima análise usará sua orientação como contexto, sem treinar os pesos.",
      );
    });
    rejection.append(rejectForm);
    box.append(rejection);
    if (
      item.draft_approved === analysis.digest &&
      !item.analysis_stale &&
      analysis.draft
    ) {
      const copy = node("button", "Copiar rascunho revisado");
      copy.className = "secondary";
      copy.onclick = action(async () => {
        await navigator.clipboard.writeText(analysis.draft);
        notice(
          "Rascunho copiado para atendimento manual. Nenhum envio automático.",
        );
      });
      box.append(copy);
    }
  }
  const move = node("form", "");
  move.id = "move-form";
  const label = node("label", "Atualizar etapa");
  const select = document.createElement("select");
  select.id = "move-stage";
  for (const [key, text] of Object.entries(labels))
    if (!["new", "research"].includes(key)) select.add(new Option(text, key));
  select.value = ["new", "research"].includes(item.stage)
    ? "needs_information"
    : item.stage;
  label.append(select);
  const noteLabel = node("label", "Motivo / resultado observado");
  const note = document.createElement("input");
  note.id = "move-note";
  note.maxLength = 500;
  note.required = true;
  noteLabel.append(note);
  const save = node("button", "Registrar etapa");
  move.append(label, noteLabel, save);
  move.onsubmit = action(async () => {
    state.item = await api("/api/leads/move", {
      project_id: state.project,
      id: item.id,
      version: item.version,
      stage: select.value,
      note: note.value,
    });
    await load();
    notice("Etapa registrada pela equipe.");
  });
  box.append(move);
  const history = node("details", "");
  history.append(node("summary", "Histórico desta oportunidade"));
  for (const event of item.events)
    history.append(
      node(
        "p",
        `${event.source} · ${event.campaign || "sem campanha"}\n${event.message}`,
      ),
    );
  for (const row of item.history) {
    history.append(
      node(
        "p",
        `${row.at} · ${{ received: "Entrada recebida", analysis_attempt: "Análise da IA", human_review: "Revisão da equipe", human_rejection: "Análise rejeitada pela equipe", stage_changed: "Etapa alterada" }[row.kind] || row.kind}${row.data.error ? " · " + row.data.error : ""}`,
      ),
    );
  }
  box.append(history);
  buttons();
}
async function poll() {
  const id = state.job;
  if (!id) return;
  notice(
    "A IA local está analisando este interessado. A tarefa fica salva na fila.",
  );
  const until = Date.now() + 240000;
  while (Date.now() < until) {
    const job = await api("/api/jobs/" + id);
    if (
      ["completed", "failed", "cancelled", "interrupted"].includes(job.state)
    ) {
      state.job = null;
      await load();
      renderDetail();
      if (job.state !== "completed")
        throw Error(
          job.error || "Análise encerrada sem aplicação. Confira o histórico.",
        );
      notice("Análise pronta. Confira evidências e rascunho antes de aplicar.");
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw Error(
    "A consulta ainda está pendente. Use Retomar consulta; não envie a análise novamente.",
  );
}
function fillContext() {
  const c = state.context;
  for (const key of ["brand", "audience", "intro", "handoff"])
    $(key).value = c?.[key] || "";
  $("facts").value = c?.facts.map((f) => f.text).join("\n") || "";
  $("questions").value = c?.questions.join("\n") || "";
  $("fact-url").value = c?.facts[0]?.url || "";
  $("fact-date").value =
    c?.facts[0]?.checked_at || new Date().toLocaleDateString("en-CA");
  $("context-version").textContent = c
    ? "Revisão " + c.version
    : "Ainda não configurado";
}
for (const [key, label] of Object.entries(labels))
  $("filter").add(new Option(label, key));
document
  .querySelectorAll("[data-tab]")
  .forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
$("search").oninput = renderList;
$("filter").onchange = renderList;
$("refresh").onclick = action(load);
$("login-form").onsubmit = action(async () => {
  state.token = $("token").value.trim();
  const projects = await api("/api/projects");
  if (!projects.length)
    throw Error("Cadastre um projeto na tela de conversas antes de começar.");
  for (const p of projects) $("project").add(new Option(p.name, p.id));
  state.project = projects[0].id;
  $("project-id").value = state.project;
  await load();
  $("login-form").hidden = true;
  $("workspace").hidden = false;
  if (!state.context) tab("context");
  notice(
    "Conectado ao servidor local. Nenhuma mensagem externa é enviada por este módulo.",
  );
});
$("project").onchange = action(async () => {
  state.project = $("project").value;
  state.context = null;
  state.item = null;
  state.items = [];
  state.job = null;
  $("project-id").value = state.project;
  $("detail").replaceChildren(
    node("p", "Selecione um interessado deste projeto."),
  );
  fillContext();
  await load();
  notice("Projeto alterado. Contexto e contatos são separados por projeto.");
});
$("context-form").onsubmit = action(async () => {
  const previous = state.context;
  const facts = $("facts")
    .value.split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((text, index) => {
      const old = previous?.facts[index];
      return {
        text,
        url:
          old?.text === text && $("fact-url").value === previous?.facts[0]?.url
            ? old.url
            : $("fact-url").value,
        checked_at: $("fact-date").value,
      };
    });
  const context = {
    brand: $("brand").value,
    audience: $("audience").value,
    intro: $("intro").value,
    handoff: $("handoff").value,
    facts,
    questions: $("questions")
      .value.split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean),
  };
  await api("/api/leads/context", {
    project_id: state.project,
    expected: previous?.digest || "",
    context,
  });
  await load();
  notice(
    "Contexto salvo. Análises anteriores precisam ser conferidas novamente.",
  );
});
$("shopair-example").onclick = () => {
  for (const [key, value] of Object.entries({
    brand: "ShopAir",
    audience: "Donos de lojas e restaurantes que querem vender online",
    intro: "Olá! A ShopAir oferece uma plataforma para sua operação de vendas.",
    handoff:
      "Se desejar, nossa equipe pode apresentar a plataforma para o seu negócio.",
    facts:
      "Loja online com catálogo, checkout, pagamentos e entregas.\nPara restaurantes: cardápio, preparo, delivery e retirada.\nEmissão fiscal, contabilidade oficial e folha de pagamento não fazem parte destes módulos.",
    questions:
      "Qual é o tipo do seu negócio?\nComo você recebe os pedidos hoje?\nVocê gostaria de conhecer uma demonstração?",
    "fact-url": "https://shopair.com.br/",
  }))
    $(key).value = value;
  $("fact-date").value = new Date().toLocaleDateString("en-CA");
  notice("Exemplo preenchido. Confira a fonte e os textos antes de salvar.");
};
let intakeId = crypto.randomUUID();
$("intake-form").onsubmit = action(async () => {
  const event = {
    source: $("source").value,
    event_id: intakeId,
    company: $("company").value,
    name: $("contact-name").value,
    email: $("email").value,
    phone: $("phone").value,
    message: $("lead-message").value,
    campaign: $("campaign").value,
    source_url: $("source-url").value,
    permission: $("permission").value,
    opt_out: $("opt-out").checked,
  };
  const result = await api("/api/leads/ingest", {
    project_id: state.project,
    event,
  });
  intakeId = crypto.randomUUID();
  $("intake-form").reset();
  await load();
  await openLead(result.id);
  tab("inbox");
  notice(
    result.deduplicated
      ? "Esta entrada já estava registrada; não foi duplicada."
      : "Entrada registrada. A preferência de contato foi preservada.",
  );
});

function renderRelay(data) {
  const connection = data.connection;
  $("relay-url").value = connection?.url || "";
  $("relay-queue").value = connection?.queue_id || "";
  $("relay-key").value = "";
  $("relay-enabled").checked = connection ? !!connection.enabled : true;
  const statuses = {
    waiting: "Aguardando primeira busca",
    ok: "Busca confirmada",
    error: "Busca não confirmada — confira serviço, endereço e chave",
    offline: "Rede desativada no servidor",
    disabled: "Coleta pausada",
  };
  $("relay-status").textContent = connection
    ? `${statuses[connection.state] || connection.state} · ${connection.received} recibos confirmados${connection.checked_at ? " · última consulta " + connection.checked_at : ""}`
    : "Nenhuma fila conectada. Configure a entrada no backend do site primeiro.";
  if (!data.network_allowed)
    $("relay-status").textContent +=
      " A configuração do servidor mantém a rede desativada.";
}
$("relay-form").onsubmit = action(async () => {
  const data = await api("/api/leads/relay", {
    project_id: state.project,
    url: $("relay-url").value,
    queue_id: $("relay-queue").value,
    read_key: $("relay-key").value,
    enabled: $("relay-enabled").checked,
  });
  $("relay-key").value = "";
  renderRelay(data);
  notice(
    "Conexão salva no servidor. A busca é automática enquanto o servidor estiver ligado; o sucesso aparece após um recibo real.",
  );
});
$("relay-disable").onclick = action(async () => {
  renderRelay(
    await api("/api/leads/relay/disable", { project_id: state.project }),
  );
  notice("Coleta pausada. Os eventos e históricos foram preservados.");
});
