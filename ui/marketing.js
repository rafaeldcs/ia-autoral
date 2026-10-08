"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  token: "",
  project: "",
  campaign: null,
  busy: false,
  preview: null,
  plan: null,
  modelAvailable: false,
  browser: null,
};
function node(tag, content) {
  const n = document.createElement(tag);
  n.textContent = content;
  return n;
}
function notice(message) {
  $("message").textContent = message;
}
async function api(path, body) {
  const r = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: {
      Authorization: "Bearer " + state.token,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const result = await r.json();
  if (!r.ok) throw Error(result.error || "Não foi possível concluir.");
  return result;
}
function action(fn) {
  return async (e) => {
    e?.preventDefault();
    if (state.busy) return;
    state.busy = true;
    document
      .querySelectorAll("button,input,select,textarea")
      .forEach((b) => (b.disabled = true));
    try {
      await fn(e);
    } catch (error) {
      notice(error.message);
    } finally {
      state.busy = false;
      document
        .querySelectorAll("button,input,select,textarea")
        .forEach((b) => (b.disabled = false));
      render();
    }
  };
}
function payload() {
  return {
    project_id: state.project,
    id: state.campaign.id,
    digest: state.campaign.digest,
  };
}
async function campaigns() {
  const list = await api(
    "/api/marketing/campaigns?project_id=" + state.project,
  );
  $("campaigns").replaceChildren(new Option("Nova campanha", ""));
  for (const c of list)
    $("campaigns").add(
      new Option(c.brief.brand + " · " + c.brief.objective, c.id),
    );
  if (state.campaign) $("campaigns").value = state.campaign.id;
}
async function job(endpoint, body) {
  const submitted = await api(endpoint, body);
  notice("Trabalho em andamento. Você pode acompanhar e cancelar.");
  const cancel = node("button", "Cancelar trabalho");
  cancel.type = "button";
  cancel.disabled = false;
  cancel.onclick = async () => {
    try {
      await api("/api/jobs/" + submitted.job.id + "/cancel", {});
      notice("Cancelamento solicitado; aguarde o encerramento.");
    } catch (error) {
      notice(error.message);
    }
  };
  $("message").append(cancel);
  const deadline = Date.now() + 20 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 750));
    const current = await api("/api/jobs/" + submitted.job.id);
    if (current.state === "completed") {
      notice("Etapa concluída. Confira os resultados.");
      if (!endpoint.endsWith("/plan")) {
        state.campaign = current.result;
        await campaigns();
      }
      return current.result;
    }
    if (["failed", "cancelled", "interrupted"].includes(current.state))
      throw Error(current.error || "Trabalho " + current.state + ".");
  }
  throw Error(
    "O acompanhamento excedeu20 minutos. Confira o trabalho na fila antes de iniciar outro.",
  );
}
function researchCandidates() {
  return [
    ["product", "product-url"],
    ["reference", "reference-url"],
    ["measurement", "measurement-url"],
    ["audience", "audience-url"],
    ["competitor", "competitor-url"],
    ["channel", "channel-url"],
    ["brand", "brand-url"],
  ]
    .filter(([, id]) => $(id).value.trim())
    .map(([role, id]) => ({ role, url: $(id).value.trim() }));
}
function loadBrandForm() {
  const profile = state.campaign?.brand_profile;
  $("instagram-handle").value = profile?.instagram || "";
  $("no-instagram").checked = profile?.no_instagram || false;
  for (const key of ["moment", "identity", "likes", "avoid", "history"])
    $("brand-" + key).value = profile?.[key] || "";
  $("style-feedback").value = state.campaign?.style_approval?.feedback || "";
  $("style-direction").value = state.campaign?.style_approval?.direction || "improve";
  $("brand-url").value = profile?.instagram ? "https://www.instagram.com/" + profile.instagram + "/" : "";
  $("brand-screen").hidden = true;
  $("brand-screen").removeAttribute("src");
  $("brand-browser-status").textContent = "";
  $("brand-session").replaceChildren(new Option("Sem investigação: usar relatos e fontes coletadas", ""));
  state.browser = null;
}
function renderBrand() {
  const c = state.campaign;
  $("instagram-handle").disabled = state.busy || $("no-instagram").checked;
  $("analyze-brand").disabled = !c.brand_profile || !state.modelAvailable || state.busy;
  $("brand-browse").disabled = !c.brand_profile?.instagram || state.busy || ["starting", "ready", "busy"].includes(state.browser?.state);
  for (const id of ["brand-capture", "brand-scroll"])
    $(id).disabled = state.busy || state.browser?.state !== "ready";
  $("brand-stop").disabled = state.busy || !["starting", "ready", "busy"].includes(state.browser?.state);
  $("brand-analysis").replaceChildren();
  const analysis = c.brand_analysis?.content;
  const labels = {observed:"O que a IA local identificou", preserve:"O que preservar", improve:"Melhorias propostas", questions:"Perguntas e lacunas"};
  for (const [key, label] of Object.entries(labels)) {
    if (!analysis) break;
    const card = node("div", ""); card.className = "card";
    card.append(node("h3", label));
    for (const value of analysis[key]) card.append(node("p", value));
    $("brand-analysis").append(card);
  }
  if (c.brand_analysis && !analysis)
    $("brand-analysis").append(node("p", "A IA não produziu uma análise verificável. Tentativas preservadas; revise a entrada e tente novamente."));
  $("brand-style").hidden = !analysis;
  $("brand-style-status").textContent = c.style_approval ? "Direção confirmada por você: " + {preserve:"manter a linha", improve:"aprimorar mantendo a identidade", reinvent:"propor nova direção"}[c.style_approval.direction] : "A geração aguarda sua confirmação do estilo.";
}
async function brandSessions() {
  const profile = state.campaign?.brand_profile;
  const rows = await api("/api/browser/sessions?project_id=" + state.project);
  $("brand-session").replaceChildren(new Option("Sem investigação: usar relatos e fontes coletadas", ""));
  for (const row of rows.filter((r) => r.url === "https://www.instagram.com/" + profile?.instagram + "/"))
    $("brand-session").add(new Option(row.created_at + " · " + row.state, row.id));
  const selected = state.browser?.id || state.campaign?.brand_analysis?.browser_session;
  if (selected && rows.some((r) => r.id === selected)) $("brand-session").value = selected;
}
async function showBrandBrowser(row) {
  state.browser = row;
  const frame = row.frames.at(-1);
  $("brand-browser-status").textContent = row.error || "Navegador da LocalAuthor: " + row.state + (frame ? " · " + frame.title : "");
  if (frame?.file) {
    const capture = await api("/api/browser/image?project_id=" + state.project + "&id=" + row.id + "&frame=" + frame.number);
    $("brand-screen").src = capture.data;
    $("brand-screen").hidden = false;
  }
}
async function waitBrandBrowser(row) {
  state.browser = row;
  const cancel = node("button", "Cancelar investigação"); cancel.type = "button";
  cancel.onclick = async () => { try { await stopBrandBrowser(); } catch (e) { notice(e.message); } };
  $("brand-browser-status").replaceChildren(node("span", "A LocalAuthor está observando o perfil. "), cancel);
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    const current = await api("/api/browser/session?project_id=" + state.project + "&id=" + row.id);
    state.browser = current;
    if (current.state === "ready") { await showBrandBrowser(current); await brandSessions(); return; }
    if (["failed", "stopped", "interrupted"].includes(current.state)) throw Error(current.error || "Investigação encerrada.");
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  throw Error("O navegador ainda está ocupado. Encerre a investigação ou confira a sessão nas ferramentas avançadas.");
}
async function stopBrandBrowser() {
  if (state.browser && ["starting", "ready", "busy"].includes(state.browser.state))
    state.browser = await api("/api/browser/action", {project_id:state.project, id:state.browser.id, command:{action:"stop"}});
}
function render() {
  $("plan-research").disabled = !state.modelAvailable || state.busy;
  const c = state.campaign;
  for (const id of ["brand-section", "research-section", "choice-section", "draft-section"])
    $(id).hidden = !c;
  if (!c) return;
  renderBrand();
  $("choice-section").hidden = c.stage === "brief";
  $("draft-section").hidden = !c.draft;
  $("sources").replaceChildren();
  for (const source of c.research) {
    const card = node("div", "");
    card.className = "card";
    const link = node("a", source.url);
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    card.append(
      link,
      node(
        "p",
        source.status === "collected"
          ? "Fonte coletada · " + source.role
          : "Leitura bloqueada: " + source.reason,
      ),
    );
    $("sources").append(card);
  }
  $("reference-id").replaceChildren();
  for (const source of c.research.filter(
    (r) => r.role === "reference" && r.status === "collected",
  ))
    $("reference-id").add(new Option(source.title, source.source_id));
  $("generate").disabled = !c.choice || !c.style_approval || !state.modelAvailable || state.busy;
  $("choice-description").textContent = c.choice
    ? "Sua escolha: " +
      (c.choice.mode === "original"
        ? "proposta original"
        : "adaptar a referência selecionada")
    : "Aguardando sua escolha.";
  $("assets").replaceChildren();
  for (const asset of c.draft?.assets || []) {
    const card = node("article", "");
    card.className = "card";
    card.append(
      node("h3", asset.channel + " · dia sugerido " + asset.day),
      node("p", asset.caption),
      node("small", asset.alt_text),
    );
    for (const claim of asset.claims)
      card.append(
        node(
          "p",
          "Fato citado: " +
            claim.text +
            " · linhas" +
            claim.start_line +
            "–" +
            claim.end_line,
        ),
      );
    const a = node("a", "Conferir destino com identificação da campanha");
    a.href = asset.tracking_url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    card.append(node("p", ""), a);
    if (
      c.stage === "approved" &&
      ["facebook", "instagram"].includes(asset.channel)
    ) {
      const button = node("button", "Preparar publicação desta peça");
      button.type = "button";
      button.disabled = state.busy;
      button.onclick = action(async () => {
        let media;
        if (asset.channel === "instagram") {
          media = prompt(
            "URL HTTPS pública do JPEG real já revisado (não um arquivo local):",
          );
          if (!media) return;
        }
        state.preview = await api("/api/marketing/preview", {
          ...payload(),
          piece_id: asset.id,
          ...(media ? { media_url: media } : {}),
        });
        const p = state.preview.payload;
        $("send-preview").textContent =
          `Canal: ${p.channel}\nConta: ${p.account}\n\n${p.caption}\n\nDestino: ${p.link}` +
          (p.media_url ? `\nJPEG: ${p.media_url}` : "");
        $("send-authorized").checked = false;
        $("send-dialog").showModal();
      });
      card.append(button);
    }
    $("assets").append(card);
  }
  $("draft-status").textContent =
    c.stage === "rejected"
      ? "A IA ainda não passou nos critérios. Tentativas e erros foram preservados."
      : c.stage === "approved"
        ? "Versão aprovada para preparação. Ainda não publicada."
        : "Propostas da IA local. A conferência automática não substitui sua revisão.";
  $("review").hidden = c.stage !== "review";
  $("export").disabled = c.stage !== "approved" || state.busy;
  if (c.stage !== "approved") {
    $("export-result").hidden = true;
    $("export-json").value = "";
  }
}
async function channels() {
  const list = await api("/api/marketing/channels?project_id=" + state.project);
  $("channels-state").replaceChildren();
  if (!list.length)
    $("channels-state").textContent = "Nenhuma conta confirmada.";
  for (const c of list) {
    const p = node(
      "p",
      c.channel + " · ID" + c.account + " · identidade conferida",
    );
    const button = node("button", "Desconectar");
    button.type = "button";
    button.onclick = action(async () => {
      await api("/api/marketing/disconnect", {
        project_id: state.project,
        channel: c.channel,
      });
      await channels();
    });
    p.append(button);
    $("channels-state").append(p);
  }
  const deliveries = await api(
    "/api/marketing/deliveries?project_id=" + state.project,
  );
  $("deliveries").replaceChildren();
  for (const d of deliveries)
    $("deliveries").append(
      node(
        "p",
        "Entrega " +
          d.piece_id +
          ": " +
          d.state +
          (d.remote_id ? " · recibo" + d.remote_id : ""),
      ),
    );
}
$("login-form").onsubmit = action(async () => {
  state.token = $("token").value.trim();
  const health = await api("/api/health");
  const foundation = await api("/api/foundation/status");
  state.modelAvailable = foundation.capabilities.text.registered;
  const projects = await api("/api/projects");
  if (!projects.length)
    throw Error("Adicione um projeto na página de conversas primeiro.");
  $("token").value = "";
  for (const p of projects) $("project").add(new Option(p.name, p.id));
  state.project = projects[0].id;
  $("login-form").hidden = true;
  $("workspace").hidden = false;
  $("availability").textContent = health.offline
    ? "Coleta externa desativada nas configurações do servidor."
    : "Pesquisa habilitada nos domínios: " + health.allowed_domains.join(", ");
  if (!state.modelAvailable)
    $("availability").textContent +=
      " Modelo textual ainda não registrado nesta instalação. A coleta funciona; planejamento e geração aguardam configuração do modelo.";
  await campaigns();
  await channels();
});
$("project").onchange = action(async () => {
  await stopBrandBrowser();
  state.project = $("project").value;
  state.campaign = null;
  state.preview = null;
  $("export-result").hidden = true;
  $("export-json").value = "";
  await campaigns();
  await channels();
  loadBrandForm();
});
$("campaigns").onchange = action(async () => {
  await stopBrandBrowser();
  $("export-result").hidden = true;
  $("export-json").value = "";
  state.campaign = $("campaigns").value
    ? await api(
        "/api/marketing/campaign?project_id=" +
          state.project +
          "&id=" +
          $("campaigns").value,
      )
    : null;
  $("reviewed").checked = false;
  loadBrandForm();
  await brandSessions();
});
$("brief").onsubmit = action(async () => {
  await stopBrandBrowser();
  state.campaign = await api("/api/marketing/campaigns", {
    project_id: state.project,
    brief: {
      brand: $("brand").value,
      audience: $("audience").value,
      objective: $("objective").value,
      destination: $("destination").value,
      channels: Array.from(
        document.querySelectorAll("[name=channel]:checked"),
        (e) => e.value,
      ),
    },
  });
  await campaigns();
  loadBrandForm();
  await brandSessions();
  notice("Briefing salvo. Informe o Instagram e as preferências antes de criar as peças.");
});
$("no-instagram").onchange = () => {
  if ($("no-instagram").checked) $("instagram-handle").value = "";
  if (state.campaign) renderBrand();
};
$("brand-profile").onsubmit = action(async () => {
  await stopBrandBrowser();
  state.campaign = await api("/api/marketing/brand", {...payload(), profile:{
    instagram:$("instagram-handle").value, no_instagram:$("no-instagram").checked,
    ...Object.fromEntries(["moment", "identity", "likes", "avoid", "history"].map((k) => [k, $("brand-" + k).value]))
  }});
  state.plan = null;
  loadBrandForm(); await brandSessions();
  notice("Preferências salvas. Investigue o perfil e colete fontes do mercado antes de pedir a análise.");
});
$("brand-browse").onclick = action(async () => {
  const row = await api("/api/browser/start", {project_id:state.project, url:"https://www.instagram.com/" + state.campaign.brand_profile.instagram + "/", allow_network:true});
  await waitBrandBrowser(row);
});
$("brand-session").onchange = action(async () => {
  await stopBrandBrowser();
  state.browser = null;
  $("brand-screen").hidden = true;
  if ($("brand-session").value)
    await showBrandBrowser(await api("/api/browser/session?project_id=" + state.project + "&id=" + $("brand-session").value));
});
for (const [id, command] of [["brand-capture", "capture"], ["brand-scroll", "scroll"]])
  $(id).onclick = action(async () => {
    const row = await api("/api/browser/action", {project_id:state.project, id:state.browser.id,
      command:{action:command, snapshot:state.browser.frames.at(-1).snapshot}});
    await waitBrandBrowser(row);
  });
$("brand-stop").onclick = action(async () => { await stopBrandBrowser(); await showBrandBrowser(state.browser); });
$("analyze-brand").onclick = action(async () => {
  await job("/api/marketing/brand-analysis", {...payload(), browser_session:$("brand-session").value || null});
  notice("A IA local apresentou sua análise. Confira as lacunas e confirme a direção que prefere.");
});
$("brand-style").onsubmit = action(async () => {
  state.campaign = await api("/api/marketing/style", {...payload(), direction:$("style-direction").value, feedback:$("style-feedback").value});
  notice("Sua direção foi registrada. A IA deve segui-la na criação e na revisão das peças.");
});
$("plan-research").onclick = action(async () => {
  const candidates = researchCandidates();
  const result = await job("/api/marketing/plan", { ...payload(), candidates });
  state.plan = {
    result,
    digest: state.campaign.digest,
    candidates: JSON.stringify(candidates),
  };
  $("research-proposal").replaceChildren(node("h3", "Plano proposto pela IA"));
  for (const row of result.proposal.plan)
    $("research-proposal").append(node("p", row.url + " · " + row.purpose));
  for (const gap of result.proposal.missing)
    $("research-proposal").append(node("p", "Ainda falta: " + gap));
  $("research-proposal").append(node("p", result.proposal.reference_question));
  notice(
    "Confira o plano antes de confirmar a coleta. A IA ainda não leu as fontes nesta etapa.",
  );
});
$("research").onsubmit = action(async () => {
  const candidates = researchCandidates();
  const validPlan =
    state.plan &&
    state.plan.digest === state.campaign.digest &&
    state.plan.candidates === JSON.stringify(candidates);
  await job("/api/marketing/research", {
    ...payload(),
    plan: validPlan ? state.plan.result.plan : candidates,
  });
  state.plan = null;
});
$("choice-mode").onchange = () => {
  $("reference-label").hidden = $("choice-mode").value !== "adapt";
};
$("choice").onsubmit = action(async () => {
  state.campaign = await api("/api/marketing/choice", {
    ...payload(),
    choice: $("choice-mode").value,
    ...($("choice-mode").value === "adapt"
      ? { source_id: $("reference-id").value }
      : {}),
  });
  notice("Escolha registrada. Agora você pode gerar propostas.");
});
$("generate").onclick = action(async () => {
  await job("/api/marketing/generate", payload());
  $("reviewed").checked = false;
});
$("review").onsubmit = action(async () => {
  state.campaign = await api("/api/marketing/approve", {
    ...payload(),
    reviewed: $("reviewed").checked,
  });
  notice("Esta versão foi aprovada. Publicação continua separada.");
});
$("export").onclick = action(async () => {
  const data = await api(
    "/api/marketing/export?project_id=" +
      state.project +
      "&id=" +
      state.campaign.id,
  );
  $("export-json").value = JSON.stringify(data, null, 2);
  $("export-result").hidden = false;
  $("download-export").hidden = Boolean(window.chrome?.webview);
  notice("Pacote preparado abaixo. Você pode copiá-lo. Nada foi publicado.");
});
$("copy-export").onclick = action(async () => {
  await navigator.clipboard.writeText($("export-json").value);
  notice("Pacote copiado. Nenhuma publicação foi feita.");
});
$("download-export").onclick = action(async () => {
  const url = URL.createObjectURL(
    new Blob([$("export-json").value], {
      type: "application/json;charset=utf-8",
    }),
  );
  const a = node("a", "");
  a.href = url;
  a.download = "campanha-" + state.campaign.id + ".json";
  a.click();
  URL.revokeObjectURL(url);
  notice("Pacote preparado. Nada foi publicado.");
});
$("connect-channel").onsubmit = action(async () => {
  const token = $("channel-token").value;
  $("channel-token").value = "";
  await api("/api/marketing/connect", {
    project_id: state.project,
    channel: $("connect-kind").value,
    account: $("account").value,
    api_version: $("api-version").value,
    token,
  });
  await channels();
  notice(
    "Identidade da conta confirmada. Permissão de publicar depende da configuração Meta.",
  );
});
$("close-send").onclick = () => {
  $("send-dialog").close();
  state.preview = null;
};
$("send").onsubmit = action(async () => {
  const p = state.preview;
  if (!p) throw Error("Prepare novamente a prévia.");
  const result = await api("/api/marketing/publish", {
    project_id: p.payload.project_id,
    id: p.payload.campaign_id,
    piece_id: p.payload.piece_id,
    payload_hash: p.payload_hash,
    authorized: $("send-authorized").checked,
    media_url: p.payload.media_url,
  });
  $("send-dialog").close();
  state.preview = null;
  await channels();
  notice(
    "Meta confirmou o ID da publicação: " +
      result.remote_id +
      ". Alcance e conversões ainda não foram medidos.",
  );
});
