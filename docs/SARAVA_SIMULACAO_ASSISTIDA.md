# Simulação assistida do saravaAPP pela IA local

## Escopo e autoria

Reexecução em 29/09/2026 do centro fictício com cinco médiuns, mensalidade de R$ 100 e sete perfis técnicos: Admin, Member, Coordinator, Treasury, Stock, Secretary e Reviewer. Contas auxiliares de aprovação não contam como médiuns. A aplicação não possui um cargo religioso distinto chamado Dirigente.

O código avaliado é o commit `f02754d` de MeuTerreiro. A simulação usa MongoDB em replica set, Next/React e .NET 10. Banco, anexos, credenciais e volumes desta execução são separados do centro anterior. Nenhum pagamento, envio de push ou dado pessoal real integra o cenário.

A rede do executor aponta exclusivamente para o gateway local da simulação. Os navegadores bloqueiam navegação fora da origem autorizada. Pacotes de compilação são obtidos pela rede em um executor separado. Todas as execuções de código do projeto acontecem em contêineres verificados, sem fallback no Windows.

- **IA neural local:** começou com `terreiro-qa-20260929/qa-policy.npz`; após o reforço usa `terreiro-qa-reinforced-20260929/qa-policy.npz` e propõe a próxima etapa a partir de observações booleanas normalizadas.
- **LocalAuthor executor:** executa os roteiros revisados e captura as telas com Playwright.
- **Codex:** escreveu os roteiros existentes, o adaptador de evidências e a preparação do laboratório; revisa os resultados e as propostas.
- **saravaAPP:** nenhum código de produto foi alterado nesta reexecução.

A IA não escreveu autonomamente esses testes, não interpretou os pixels das capturas e não gerou uma correção de produto nesta rodada. A execução inicial reutilizou pesos anteriores. Depois houve treinamento real de um novo checkpoint do classificador, descrito abaixo. A importação das lições como memória é uma operação separada, que não treina pesos automaticamente. O fluxo é de laboratório por CLI, não uma nova autonomia geral ativada no chat.

## O que a IA recebe e decide

`scripts/assess-terreiro-simulation.py` verifica o hash do checkpoint e a avaliação anterior, lê os recibos reais e registra tanto a decisão neural quanto a revisão determinística independente. Divergência reprova a proposta.

1. Sem compilação/testes: `CHECK_BUILD`.
2. Com falha observada: `INVESTIGATE_FAILURE`.
3. Depois da compilação/testes: `CHECK_AUTHENTICATION`, início do roteiro integrado de negócio.
4. Depois dos recibos de negócio: `CHECK_BROWSER`.
5. `REPORT` só é aceitável quando também existem verificações adicionais, navegador e interações aprovadas.

Os roteiros executam lotes: a IA não decide cada uma das centenas de asserções. O plano completo exigido pelo executor legado é identificado como hipotético e nunca serve como comprovante de execução.

## Lições de investigação

As primeiras tentativas falharam no laboratório, com `ModuleNotFoundError: PIL` e ausência do instalador `pip`. A IA classificou ambas como `INVESTIGATE_FAILURE`. O diagnóstico da dependência e a correção do ambiente foram feitos pelo tutor; não são atribuídos à compreensão neural do traceback.

Foi criada a imagem `localauthor-terreiro-simulation:1` com as versões declaradas no processador: Pillow 11.3.0 e pypdf 6.0.0. O executor verifica essas versões antes de testar. As tentativas anteriores ficam preservadas, inclusive a falha original; nenhum teste foi removido ou afrouxado.

Outro bloqueio de preparação aconteceu porque o Docker resolve o nome da rede compartilhada para o ID do contêiner. A inspeção passou a comparar o ID resolvido, mantendo a exigência de rede correta, usuário não privilegiado, raiz somente leitura e capacidades removidas.

Regras ensinadas:

- Separar erro do ambiente, falha do executor e defeito do produto.
- Não trocar o teste ou o resultado esperado para apagar uma falha.
- Não inferir teste unitário ou compilação de um relatório HTTP.
- Não aprovar relatório vazio, uma etapa ausente ou um caso falso sob um `success: true`.
- Exigir controle positivo junto à negação de acesso: uma URL inexistente não prova autorização correta.
- Não considerar comprovante como quitação, leitura como presença ou transferência como receita nova.
- Manter a autoria explícita; consultar uma lição e atualizar pesos são operações diferentes.

## Falha neural encontrada e reforço

O classificador anterior acertou **10/12** desafios derivados de cópias dos recibos desta rodada. Errou dois casos: autorização revogada ou sandbox não verificada depois de um histórico quase todo aprovado. Pediu `CHECK_EVIDENCE` quando deveria pedir `STOP_SCOPE`. A revisão rejeitou as duas propostas; nenhuma ação não autorizada foi executada.

O curso sintético anterior sub-representava esses históricos quase completos. O novo curso mistura históricos vazios, completos, quase completos e aleatórios, sempre subordinados à autorização. Contém 2.048 exemplos de treino, 512 de validação e 512 de teste, com IDs de estado disjuntos. Estados dos desafios observados e da validação/teste original foram excluídos do novo curso. O checkpoint foi selecionado por validação, sem selecionar pelo teste final.

Treinamento com pesos próprios desde a inicialização, sem API externa ou pesos pré-treinados: 10.000 passos. Resultado: baseline **32/512**, novo teste **512/512**, regressão do curso original **256/256** e reavaliação dos desafios **12/12**. Os 12 desafios já eram conhecidos após o diagnóstico; são uma regressão retrospectiva, não uma prova inédita de generalização. Não houve alteração do modelo geral de linguagem.

O checkpoint anterior, sua avaliação reprovada, as falhas de ambiente e os recibos originais foram preservados. O adaptador determinístico continua obrigatório mesmo depois do reforço: confiança neural não autoriza ações.

## Ferramentas e reprodução

Pré-requisitos: Docker, imagem base revisada `localauthor-code-repair-lab:1`, checkpoint privado qualificado, checkout saravaAPP e autorização para dados sintéticos.

1. Criar snapshot Git em diretório privado novo. Registrar commit e hash do arquivo. Não reutilizar o banco anterior: o roteiro troca a senha inicial e cria o centro.
2. Construir `qa/Dockerfile.terreiro-simulation`. Executar `scripts/init.mjs --port 3180` do snapshot somente em contêiner verificado. Guardar `.env` e `.secrets` fora do Git.
3. Criar outro projeto Compose, com volumes próprios de MongoDB/anexos e Pix/push desativados. Nesta rodada o gateway externo usa `127.0.0.1:3181`, enquanto os workers usam `http://localhost:3180` dentro da rede do gateway. A configuração não equivale a habilitar login humano pela porta 3181.
4. Inspecionar cada worker antes de iniciar: usuário `10001:10001`, raiz somente leitura, `cap-drop ALL`, `no-new-privileges`, limites de memória/processos e rede esperada. Montar somente as entradas necessárias e o diretório privado de resultados.
5. Salvar a inspeção em `sandbox.json`. Rodar `assess-terreiro-simulation.py --model /model --run /run --label initial`. Guardar `local-ai-plan.json` também em `artifacts` do snapshot.
6. Executar `verify-terreiro-simulation.py --source /project --output /run/builds` na imagem preparada. Ele verifica contagens não nulas e resultados Node/Python/TRX, além dos builds Next/.NET. A aplicação segue sem lockfile versionado; o lock resolvido é preservado como evidência, sem declarar reprodução de dependências de produção.
7. Após decisão aprovada, executar `simulate-five.mjs`. Copiar o recibo para `simulation/http-report.json` e consultar a política novamente. Respeitar a janela do limitador de login antes do follow-up; não desabilitá-lo.
8. Executar `simulate-five-followup.mjs`, `run-terreiro-browser.cjs` e `run-terreiro-interactions.cjs`, com credenciais fictícias montadas somente para leitura. Não capturar tela de login nem registrar senha, cookies, HAR ou traces autenticados.
9. Consultar a política com todos os recibos e executar `qualify-terreiro-receipts.py --model /model --run /run`. Os desafios alteram cópias em memória dos recibos; não alteram o banco nem as evidências originais.
10. Gerar a galeria com `terreiro-gallery.py /run/simulation`. Publicar somente esse diretório em loopback. Importar esta lição na memória do projeto e comprovar a consulta.

Layout privado esperado: `sandbox.json`, `builds/builds.json`, `simulation/{http,followup,browser,interaction}-report.json`, `decisions/*.json` e `receipt-challenges.json`. Falhas e tentativas anteriores ficam em diretórios separados. Uma execução interrompida não autoriza repetir o seed contra o mesmo banco.

Não usar `docker compose down -v`. Ao terminar, parar somente o laboratório desta rodada, preservando volumes, credenciais fictícias e provas para investigação. A instância anterior permanece disponível.

## Limites

Esta rodada verifica o catálogo executado, não todas as combinações possíveis do sistema. Não inclui carga de produção, pagamentos reais, dispositivos físicos/push, funcionalidades não implementadas ou investigação autônoma de qualquer site. O modelo geral continua sem qualificação como programadora autônoma.

O resultado quantitativo desta rodada fica em `SARAVA_SIMULACAO_RESULTADO.json`; as capturas e os logs permanecem privados, fora do Git.
