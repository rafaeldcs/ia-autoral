# Entrega de marketing e QA — ShopAir, Orbit e LocalAuthor

Data: 7/10/2026. Resultado: quatro propostas de posts, oito imagens e um painel de planejamento local; correções do navegador e da seleção de fatos da LocalAuthor verificadas. Não representa certificação de todos os fluxos, campanha publicada ou treinamento de pesos.

## Autoria e revisão

A LocalAuthor usou inferência real de Qwen/Qwen3-8B-GGUF, revisão `7c41481f57cb95916b40956ab2f0b139b296d974`, pesos SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`, já presentes no servidor. Foram 29 solicitações delimitadas, incluindo propostas rejeitadas e revisões. O supervisor forneceu contexto, apontou erros, escreveu testes independentes e aplicou mecanicamente as propostas revisadas. Nemotron Nano 4B foi consultado como professor local; suas propostas inadequadas foram rejeitadas. Não foi usado Nemotron Ultra nem serviço externo de IA.

A IA escreveu a ampliação do vocabulário comercial para fatos de software, a limpeza de identificadores DOM, a verificação de controles ocultos/recortados, a permissão delimitada de preflight de leitura, os textos e as alterações do painel/layouts. Precisou de orientação sobre plurais, guardas, escaping, citações e HTML inseguro. O supervisor ajustou apenas âncoras de aplicação e formatação quando necessário; originais e feedback foram conservados. Isso é desenvolvimento assistido e avaliado, não programação autônoma demonstrada.

## Marketing entregue

[README do kit](../../marketing/shopair-orbit/README.md), [posts e hipóteses](../../marketing/shopair-orbit/posts.json), [painel](../../marketing/shopair-orbit/gestao.html), [artes](../../marketing/shopair-orbit/assets/).

Duas peças da ShopAir (Instagram/Facebook) e duas do Orbit (Instagram/LinkedIn), cada uma em feed 1080 × 1350 e story 1080 × 1920. A ShopAir usa ilustração conceitual. Orbit reutiliza logo/layout anteriores da IA e captura de QA com dados fictícios. As capturas autenticadas da ShopAir não foram usadas em anúncios nem versionadas.

Fonte pública de recursos ShopAir: https://shopair.com.br/, consultada nesta execução. Recursos anunciados não provam integrações funcionando ou resultados comerciais. Não há promessa de preços, gratuidade, porcentagens ou eficácia. Formatos exportados são escolhas deste laboratório, não uma alegação de formatos publicitários ótimos pesquisados.

O painel filtra marcas, mostra legendas e permite salvar datas/notas. Persistência é localStorage deste navegador: não é banco central de equipe, integração de redes ou agendador. Precisa de HTTP com posts.json ao lado. Direção original é provisória, aguardando escolha humana entre original/referências. CTA proposto: solicitar demonstração. Destino comercial do Orbit, contas, aprovação, datas e instrumentação de conversão ainda precisam de definição. Nenhum post foi publicado e nenhuma verba foi consumida.

## Verificações executadas

| Componente / revisão | Execução e resultado | Limite |
| --- | --- | --- |
| LocalAuthor, fontes desta entrega | `python3 scripts/run-tests.py`: 519 aprovados, zero falhas/erros/ignorados, em Linux isolado | Software; não qualificação geral do modelo |
| LocalAuthor no Windows, antes do último ajuste CORS | 516 aprovados e 3 testes de symlink indisponíveis; flag explícita allow-unavailable-symlinks | Complete=false; Linux executou os três |
| Workflow e BrowserWorkspace | 41 testes direcionados aprovados | Parte usa dublês; não substitui inferência/browser reais |
| Navegador próprio, Chromium real | Identificadores únicos, remoção de marcadores ocultos, snapshot obsoleto rejeitado, menu recortado excluído, sobreposição parcial preservada; matriz de requisições/CORS aprovada | Sem liberação de POST/DELETE; não teste de todo site |
| Marketing, Chromium real | 8 exportações; filtro, salvar/reabrir, móvel sem overflow, armazenamento corrompido/bloqueado, JSON ausente e HTML malicioso literal aprovados | Funcionamento, não desempenho de campanha |
| Orbit, fonte `05ae27aa47545d1ab731bd9638ab0815d58a61db` | Builds .NET/Next; 96 unitários; 9 API; 12 testes Git HTTP reais; navegador admin/manager/member/viewer, celular, teclado, saída e reset de projeto aprovados | Laboratório com dados sintéticos; não deploy HML nem ACL isolada por projeto |
| ShopAir frontend `160ebeb4b06956f0e553332def3ad2b48e220e83` + API baseline `beef88b` | Node unit: 152 aprovados; regressões estáticas: 472 aprovadas | Não são jornadas E2E de todas as telas |
| ShopAir.AI, API baseline `beef88b` | 9 testes aprovados | Software, não qualidade geral da Aira |
| ShopAir backend dev `908b9a4d872fed114fbbd3ad1297c50e5c1e104b` | `dotnet test tests/ECApi.Tests/ECApi.Tests.csproj -c Release --filter FullyQualifiedName!~.Integration.&FullyQualifiedName!~.Architecture.`: 1.495 aprovados, zero falhas/ignorados | Integração e arquitetura excluídas explicitamente |
| ShopAir HML, navegador da própria LocalAuthor | Login protegido e leitura de dashboard/Super/central de marketing; capturas privadas da própria IA | Planos/resultados/execuções tiveram capturas de carregamento; não aprovados como fluxos completos |

Linux/Docker foi inspecionado antes e depois do início: imagem por SHA, usuário 10001, rede desativada nos testes de código/artes, raiz somente leitura, sem privilégios/capacidades, no-new-privileges e limites. A investigação HML usou conexão de leitura restrita a hosts aprovados; autenticação explícita separada. Não houve execução de código gerado no host.

## Falhas encontradas e tratadas

- Marketing ignorava fatos de projetos/Git e aceitava correspondências parciais. A proposta final mantém limites, preços/promessas/brackets rejeitados e linhas originais; testes novos verificam software e comércio.
- Identificadores de controles DOM ficavam duplicados após ocultar menus. Marcadores anteriores são removidos a cada observação. Menus com opacity zero ou totalmente recortados não são clicados.
- Preflight de GET/HEAD autenticado entre origens não estava autorizado. A proposta final permite apenas OPTIONS com método de leitura explícito e caminho seguro, preservando HTTPS/443, hosts, origem, janela de login e bloqueio de mutações. Propostas com ReferenceError/escapes incorretos foram rejeitadas. Isso não resolveu ou qualificou todas as telas dinâmicas.
- Três regressões da Aira perderam parâmetros de rotas relativas no Linux: UriKind.Absolute as interpretava como file:. A IA local propôs restringir conversão a http/https. Os três testes passaram no overlay isolado. Ao atualizar dev, uma solução equivalente já estava incorporada; preservada, sem alteração duplicada ou commit vazio na ShopAir.
- A branch original do frontend estava 731 commits atrás de dev e tinha alterações do usuário. As nove falhas nessa combinação não se reproduziram nos checkouts limpos testados. Os arquivos do usuário foram preservados.
- Na API baseline, faltas de fixtures e cache Mongo2Go RO causaram falhas do laboratório. Depois das correções do operador, overlay passou 1.303/1.304; falhou certificação SA451 ainda planned. Não se apagou teste nem se marcou passed artificialmente. Dev avançou durante o trabalho e sua seleção atual passou 1.495 testes. Esses resultados pertencem a revisões distintas.
- A tentativa inicial da suíte completa de backend teve falhas de ambiente e outra abortou por memória/processos/timeout. Não é evidência de integração completa aprovada; não se removeu isolamento nem se usou base real para fazer passar.

## Ensino no servidor

[Lição durável](../../knowledge/skills/MARKETING_QA_COM_EVIDENCIAS.md), escrita pelo supervisor após rejeitar resumos didáticos imprecisos da IA, importada oficialmente para consulta nos três projetos (ShopAir, Orbit e Aprendizado). Backup, CRC e hashes conferidos; servidor encerrado cooperativamente e reiniciado. Cinco experiências/feedbacks foram registrados na base privada. Aceitação humana, revisão de direitos e autorização de treino continuam false; verificações técnicas são registradas separadamente.

A resposta final da IA a um exercício supervisionado não alegou publicação ou pesos treinados e manteve casos incompletos pendentes. Ainda confundiu conexão/publicação com autenticação externa em uma justificativa; feedback registrado. Não equivale a avaliação independente nem demonstração de entendimento universal.

A lição aborda fatos/hipóteses/métricas, escolha de referências, CTA, segurança de texto/JSON, limites do localStorage, falhas de armazenamento, XSS, testes por camada, versões, capturas de carregamento, CORS, rotas e proibição de fabricar resultados. Consulta central ajuda novas solicitações; não transforma automaticamente o modelo em especialista nem altera pesos. Os oito exemplos anteriores para LoRA continuam sujeitos à revisão humana; não foram promovidos e nenhuma limpeza de currículo foi feita.

## Pendências reais

1. ShopAir: suíte completa de integração/arquitetura e jornadas com todos os cargos/tenants/fluxos críticos não foram concluídas nesta execução. Não há declaração de QA 100%.
2. Navegador da IA: confirmar conteúdo estável e dados carregados nas subáreas de marketing, investigar navegações não confirmadas e APIs bloqueadas, sem liberar mutações indiscriminadamente. Não está qualificado para investigar todo e qualquer site.
3. Marketing: validar direção/editorial, destino e aprovação; integrar armazenamento de equipe/agendamento/redes se desejado; instrumentar e executar campanha autorizada para medir eficácia. As peças atuais são rascunhos revisáveis.
4. Orbit: testes locais não representam atualização de HML; deploy exige seus gates de capacidade, execução e health. Nenhuma publicação de aplicação foi feita por esta entrega.

Evidências completas, propostas rejeitadas, capturas e recibos ficam privados no servidor em `C:/Users/rafae/AppData/Local/LocalAuthor-Delivery/shopair-orbit-qa-marketing-20261007`; evidências Orbit em `apps/orbit/artifacts/` (ignoradas). Segredos, contas, dados de clientes e imagens autenticadas ficam fora do Git.
