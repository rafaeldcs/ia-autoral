# ShopAir: postagens e calendário editorial

Entrega de 08/10/2026: 12 peças principais para quatro semanas, cinco carrosséis completos, três roteiros de vídeo, quatro artes estáticas, oito desdobramentos para Stories, respostas comerciais e critérios de medição. O PDF de 33 páginas está em `output/pdf/SHOPAIR_POSTAGENS_CALENDARIO_20261008.pdf`.

`postagens.json` contém textos revisados, público, argumento, direção de arte, métrica, fontes e autoria. `calendario.csv` usa semanas relativas, três peças por semana e horário de Brasília. O início é escolhido pela empresa; os horários são propostas, não melhores horários comprovados. Nada foi agendado/publicado em redes sociais nesta entrega.

## Pesquisa e identidade

A coleta foi executada pelo `ResearchService` da LocalAuthor em 11 URLs públicas explicitamente autorizadas. O próprio navegador da LocalAuthor capturou o site público; nenhuma credencial de cliente foi utilizada. Codex comparou as fontes oficiais, conferiu o escopo no material disponível e delimitou os argumentos. Referências do produto, concorrentes, Sebrae, Meta, TikTok e W3C aparecem no PDF com data/população e limites pertinentes.

A logo PNG veio do site oficial e foi comparada byte a byte com o asset do aplicativo. Paleta e tipografia foram conferidas em `BrandSystem.jsx`, `ShopAirMark.jsx` e `index.css` da cópia autorizada do app. `assets/proveniencia.json` registra revisão, origem e hashes. Fontes Outfit e Plus Jakarta Sans foram obtidas de revisão fixa da coleção Google Fonts, sob SIL OFL 1.1; licenças acompanham os arquivos. As artes do PDF são conceitos tipográficos de produção, não capturas inventadas de funcionalidades.

## Papel da IA e da revisão

A LocalAuthor gerou rascunhos e revisões reais com pesos locais existentes: Qwen3-8B e derivado Qwen3.5-9B, com origem, revisão e licença preservadas. Foram 63 respostas completas, incluindo estratégia, tentativas reprovadas e refinamentos; isso não significa 63 peças aprovadas. Houve também 12 falhas de execução numa cópia privada incompleta do pacote RPC; as evidências foram preservadas, o empacotamento corrigido e a execução seguinte terminou sem essas falhas.

As propostas iniciais inventaram métricas/recursos, fizeram comparações sem fonte, confundiram modalidades e descumpriram formato/duração. Codex devolveu feedback, fez seleção editorial e precisou editar textos e falas. `postagens.json` registra as edições. Não atribuir a entrega a autonomia ou saída intacta da IA: a correção estrutural por schema não garante correção semântica. O perfil experimental não foi promovido no servidor e os pesos não foram alterados.

A lição `knowledge/skills/POSTAGENS_COM_IDENTIDADE_E_CALENDARIO.md` foi importada oficialmente para consulta nos projetos ShopAir, Orbit e aprendizado, com backup verificado, hashes e `training_allowed=false`. A aplicação foi reiniciada cooperativamente. Consulta e feedback não equivalem a treinamento de pesos. Prompts, respostas brutas e diagnósticos permanecem privados e não são publicados neste pacote.

## Produção e medição

Antes do início, conferir escopo comercial, links, bio, conta, material de gravação, direitos de imagem/voz/música e disponibilidade de atendimento. A proposta do PDF não inclui exportação final de todas as artes nem gravação dos vídeos. Publicação exige ação/autorização específica nas contas; não há promessas de alcance, venda ou horário universal.

Medir tráfego, retenção, salvamentos e contatos com denominadores e origem. Clique não é contato qualificado. Atribuição por post não deve ser inventada a partir de link de bio compartilhado. Sem Insights/histórico de conversão da conta, os testes e as melhorias são hipóteses a avaliar. Cadência orgânica não equivale a experimento causal controlado.

## Regerar o PDF

Com Python e ReportLab, executar na raiz do repositório:

```powershell
python marketing/shopair-calendario/gerar_pdf.py
```

O gerador usa somente o JSON revisado e os assets locais; não chama IA, abre conta ou publica conteúdo. O preparo privado das fontes usou fontTools 4.66.1 para instanciar pesos; os TTF estáticos já estão incluídos, sem dependência de fontTools para regerar. Após alterações, renderizar o PDF com Poppler e conferir todas as páginas. A revisão desta versão inspecionou as 33 páginas, além de verificar texto, chamadas, formatos e duração dos roteiros.

Validação do projeto: `python scripts/run-tests.py` executado na sandbox Linux isolada, 537 testes aprovados, nenhum erro/falha/skip. Esse resultado verifica o software; não comprova desempenho de marketing nem autonomia neural. O CI da revisão publicada deve ser conferido separadamente.
