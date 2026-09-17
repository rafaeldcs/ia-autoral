# Usabilidade: interface, ensino e evidência

Data: 17/09/2026. Escopo desta rodada: chat principal do LocalAuthor. Não constitui auditoria do Orbit, das ferramentas avançadas ou certificação de acessibilidade.

## O que foi corrigido

- Nova conversa ganhou texto visível; o avatar decorativo com aparência de controle foi removido.
- Links de navegação têm href e sublinhado. Ações como orientações, copiar e sair têm aparência de botão.
- Primeiro acesso oferece Adicionar meu primeiro projeto. Envio e ações dependentes de projeto ficam indisponíveis, com explicação no campo.
- A lista de conversas vazia explica como começar. Projeto/conversa selecionados usam aria-current.
- Exemplos explicam que preenchem o rascunho, sem enviar. O campo recebe foco para edição.
- Progresso usa aria-busy e status; envio duplicado fica bloqueado. Erros preservam a entrada.
- Diálogos têm nomes acessíveis. Botões têm alvos maiores; links e textos auxiliares ganharam contraste. Os alvos visíveis foram medidos no celular, sem alegar conformidade integral WCAG.
- O guia de qualidade passou a incluir usabilidade e uma resposta específica, identificada como orientação escrita, com exemplos de ação e navegação.

HTML/CSS/JS são servidos do disco: recarregar a página carrega a interface. O guia Python novo foi testado em servidor temporário; sua ativação no serviço 8765 depende de reinício. Não houve reinício nesta rodada. A tentativa da rodada anterior foi rejeitada pela revisão automática, com apenas “blocked by policy”; não foi contornada.

## Critérios para ensinar e revisar

| Situação | Critério | Como observar |
| --- | --- | --- |
| Executar uma operação | Botão nativo, verbo e objeto claros | Salvar funciona com clique, Enter e Espaço |
| Ir a outra página | Link nativo com destino e texto descritivo | Navegação e abrir em nova aba funcionam |
| Informação sem ação | Sem cursor, borda ou destaque que prometa clique | A pessoa não tenta acioná-la repetidamente |
| Primeiro acesso | Explicar o próximo passo e oferecer ação principal | Pessoa encontra como começar sem dicas |
| Exemplos e sugestões | Rótulo e explicação correspondem ao efeito | Pessoa sabe se vai preencher ou enviar |
| Carregamento | Estado visível, sem duplicar operação | Clique repetido não repete o envio |
| Erro | Explicar recuperação e preservar rascunho | Pessoa consegue corrigir e tentar novamente |
| Teclado e celular | Foco visível, nomes acessíveis e alvos utilizáveis | Tarefa completa sem mouse, sem perda de controles |
| Conclusão | Resultado perceptível e evidência de teste | Sucesso só é informado após confirmação |

Referências consultadas, não copiadas para treino:

- https://www.w3.org/WAI/ARIA/apg/patterns/button/
- https://www.w3.org/WAI/ARIA/apg/patterns/link/
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

## Treino neural realizado

Script: `C:\Users\rafae\OneDrive\Desktop\jira-local-experimental\scripts\train-usability.py`.

Continuação dos pesos próprios do candidato de engenharia. Nenhum modelo externo, API de IA, texto de site ou conversa privada entrou no corpus. Sem nova dependência ou mudança de arquitetura. O modelo continua textual: não foi treinado para enxergar telas.

Foram criadas oito tarefas: gerar botão, link, rótulo explícito, status e decidir correções para decoração enganosa, erros, estados vazios e validação com pessoas. São 24 situações de treino, oito de validação e oito de teste, com reformulações reservadas dentro das mesmas famílias, mais 1.002 exemplos anteriores somente de treino como revisão. Manifesto, proveniência e hashes foram verificados pelo validador existente.

Após 1.200 passos:

- Validação: 0/8 em todas as quatro medições. Pelo desempate que preserva o primeiro melhor resultado, selecionou-se o passo 300.
- Teste reservado: **0/8**, contra 0/8 antes do treino.
- Reprodução de exemplos de treino pelo candidato selecionado: **16/24**. Isso não mede generalização.
- Regressão de respostas anteriores: **42/68**. Nenhum programa gerado foi executado nesta rodada.
- `chatEnabled=false`: candidato não ativado e modelo anterior preservado.

A comparação é textual exata e pode rejeitar HTML equivalente. Nesta execução, as oito respostas foram também inspecionadas: eram vazias, incompletas ou malformadas; não eram soluções equivalentes. Queda de loss e reprodução de exemplos não estabelecem capacidade de criar interfaces intuitivas.

Evidências privadas em `%LOCALAPPDATA%\LocalAuthor`:

- `exports/usability-report.json` e `exports/usability-20260917T180622Z/report.json`.
- `models/usability-20260917T180622Z/best-validation.npz`.
- `corpus/usability-20260917T180622Z/manifest.json`.
- SHA-256 do checkpoint: `cf6d7e7b20df6d242d8c88986346c858a02365c71a5026430073031e5cf5659d`.

Os novos casos de teste já observados não devem orientar outra rodada apresentada como avaliação independente. Antes de novo treino, criar outras situações reservadas; selecionar por validação, avaliar regressões e submeter qualquer ativação aos controles existentes.

## Verificação do produto

- `scripts/run-tests.py --allow-unavailable-symlinks --report reports/usability-tests.json`: **150 aprovados**, zero falhas/erros, três testes de symlink indisponíveis por privilégio do Windows (153 no total; cobertura incompleta explicitamente registrada).
- `scripts/chat-smoke.py`: **27 verificações aprovadas** em Edge, incluindo teclado, estados vazios, links, rascunho, progresso, celular, isolamento e geração real pelo modelo anterior.
- Capturas inspecionadas: `reports/chat-welcome.png` e `reports/chat-mobile.png`.
- A primeira execução do teste de captura usou espera com avaliação de string, bloqueada pela CSP. O teste foi corrigido para aguardar o estado do elemento; nenhuma política foi relaxada.
- Ao fechar o navegador, o servidor temporário registrou reset de conexão HTTP 10054; isso não falhou os testes. Nenhuma exceção JavaScript foi observada.

## Avaliação com pessoas ainda necessária

Com participantes que não conhecem o produto, pedir sem explicar os botões: cadastrar um projeto de laboratório, iniciar conversa, usar e editar uma sugestão, consultar referência, recuperar um envio recusado e voltar à conversa anterior. Utilizar somente dados fictícios e registrar observações com consentimento.

Observar conclusão sem ajuda, primeiro clique, hesitações, interpretações erradas, perda de entrada e necessidade de intervenção. Perguntar ao final o que a pessoa esperava de cada controle confuso. Transformar os problemas observados em novos exemplos autorizados e casos de regressão. Uma execução automatizada não substitui essa avaliação; nenhum estudo com pessoas foi realizado nesta rodada.
