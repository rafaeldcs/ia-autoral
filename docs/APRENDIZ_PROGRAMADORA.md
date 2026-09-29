# Aprendiz de programação: primeira correção nova e guiada

Atualização posterior: a investigação restrita por ferramentas foi avaliada a partir de relatos, sem indicação de arquivo/função durante os episódios. Resultados e limites em [Investigação de código](INVESTIGACAO_PROGRAMACAO.md). Isso não transforma a primeira rodada abaixo em investigação autônoma retroativamente.

Rodada de 29/09/2026. **O LocalAuthor ainda não é uma programadora autônoma geral.** Esta entrega acrescenta uma família de código e um fluxo auditável de investigação guiada, geração, testes e revisão. O alvo real é o saravaAPP/MeuTerreiro.

## Problema e autoria

`formatDate(null)` interpretava ausência de data como o timestamp zero; no fuso de São Paulo, aparecia uma data de 1969. Codex identificou o problema e forneceu a hipótese e o nome da função. A busca determinística do LocalAuthor localizou o módulo, leu o trecho e seu hash e montou um contexto curto. O modelo não descobriu a causa sozinho.

O modelo geral anterior foi consultado primeiro. Sua resposta foi preservada e reprovada, sem aplicação. Um novo Transformer original foi treinado do zero: 103.936 parâmetros, 63 exemplos de treino e quatro de validação. O checkpoint foi selecionado após 1.000 passos usando somente validação. Doze combinações e o alvo exato do saravaAPP ficaram reservados. São combinações novas de uma família ensinada, não tipos inéditos de problemas.

Saída original dos pesos locais:

```javascript
if (value == null) return "Data indisponível";
assert.equal(formatDate(null), "Data indisponível");
```

A primeira linha é a correção; a segunda é a asserção de regressão. Codex escreveu o invólucro `node:test`, os exemplos didáticos, os verificadores e a infraestrutura. A inferência não procura uma resposta no corpus nem seleciona um template. O verificador só aceita ou rejeita: não conserta a saída do modelo. A inserção no projeto foi mecânica, depois da revisão do diff e dos testes, conferindo hashes de origem e destino.

## Evidência e limites

- 12 combinações reservadas + 1 alvo do projeto: 13/13 gerações corretas.
- 14 pares vermelho/verde: os testes falharam no código defeituoso e passaram após a proposta.
- 113 verificações de comportamento, incluindo ausência, entradas inválidas, datas válidas e preservação do timestamp zero.
- 13 controles negativos: uma guarda incorreta baseada em valor verdadeiro/falso foi detectada porque rejeitava zero.
- 196 testes JavaScript no saravaAPP, incluindo a nova regressão.
- 234 testes do LocalAuthor, sem pulos.
- 10 verificações navegador → chat → pesos, mantendo Caddy/C# e acrescentando data ausente, com visualização móvel.
- Build Next.js e publish .NET 10 concluídos; 138 testes C# aprovados, sem pulos.
- Nove verificações funcionais na interface Next real: login de coordenação, dados da API/MongoDB da simulação, ausência de data injetada somente na resposta ao navegador, desktop/celular e restauração da resposta original. Duas capturas foram produzidas pelo worker do LocalAuthor. Esse roteiro funcional foi escrito por Codex.
- Inferência confirmada no servidor Windows em uso, com o mesmo hash e resposta. A interface da simulação foi reconstruída e reiniciada preservando o banco; o serviço LocalAuthor foi recarregado pelo supervisor instalado.

Os grupos se sobrepõem; não representam percentual de cobertura total. O certificado contém os resultados da avaliação restrita. Builds e verificações adicionais ficam registrados separadamente em `reports/date-repair-builds-*`. Falhas anteriores não são apagadas.

Capturas desta rodada: `reports/date-repair-functional/date-missing-desktop.png`, `date-missing-mobile.png` e `reports/date-repair-chat/date-chat-mobile.png`. Nenhuma tela com senha foi capturada. As evidências da simulação anterior permanecem na galeria da porta 3190; esta rodada tem seu relatório e capturas próprios.

Checkpoint: `date-repair-20260929/best-validation.npz`. SHA-256: `2aaff29ed2570eaa6d93b85f71cc987675cff75eb26d2dcaad3209ebf29e9ba0`.

## Lições para a IA e para o executor

1. Reproduzir o erro antes da alteração. Um teste que também passa no código original não comprova a correção.
2. Não confundir ausência com falsidade. O número zero é um timestamp válido; uma guarda `!value` perderia esse caso.
3. Consultar o contexto e preservar intenção, identificadores, mensagem, formato e arquivos não relacionados. Esta rodada só entende um padrão de função; fonte ambígua ou diferente exige revisão.
4. Distinguir defeito do modelo, do produto e do executor. A primeira investigação parou porque a política de arquivos não incluía `.mjs`. Foi acrescentado suporte a `.mjs` e `.jsx`, mantendo bloqueios de segredos, caminhos externos, links e mudanças em testes sem autorização.
5. O primeiro build tentou `npm ci` sem lockfile no Git e falhou. A resolução de dependências seguiu o comportamento documentado no Dockerfile do projeto; o lock produzido foi preservado como evidência e reutilizado. Não foi silenciosamente adicionado ao produto.
6. O segundo build encontrou `next: Permission denied` no temporário sem execução. O laboratório de build usa temporário executável para o compilador e suas bibliotecas, sem capabilities, com usuário não root, raiz somente leitura e limites de recursos. Não houve execução do projeto no Windows.
7. Acerto restrito não autoriza tarefas desconhecidas. Não anunciar autonomia geral nem usar este mesmo conjunto como avaliação inédita na próxima rodada.

## Uso e reprodução

No chat do LocalAuthor, abra **Exercitar correção de código → Testar data ausente e regressão → Enviar**. O botão fornece o problema; a resposta vem dos pesos no servidor. Os arquivos não são alterados pelo chat.

Para repetir o experimento em uma sandbox revisada, use `scripts/Invoke-DateRepairLesson.ps1` com `-Project` apontando ao checkout do MeuTerreiro, `-Revision 15665ba523a6955f8c6044adb7fb463c0cb843ee` e `-BaselineCheckpoint` apontando ao checkpoint privado do modelo geral anterior. A imagem local `localauthor-code-repair-lab:1` deve existir. O script cria pastas novas, verifica o isolamento, treina e avalia sem rede. Não ativa pesos nem aplica propostas. O commit atual já corrigido não deve ser apresentado como o caso original defeituoso.

Pesos, corpus, respostas brutas e evidências permanecem no servidor, fora do Git. O certificado ativo fica em `%LOCALAPPDATA%/LocalAuthor/exports/date-repair-qualification.json`. Os outros computadores clientes consultam o mesmo servidor e usam esses mesmos pesos. Git transporta o software e a documentação, não os checkpoints privados.

Consultar estas lições é recuperação de conhecimento. Somente o treino descrito acima alterou os pesos deste novo especialista; importar o documento não treina automaticamente nenhum modelo.

## Próximas qualificações — ainda pendentes

| Capacidade | Estado comprovado |
|---|---|
| Gerar uma correção e asserção em família conhecida | Aprovada neste escopo |
| Ler o módulo certo a partir de símbolo e hipótese fornecidos | Busca guiada implementada |
| Executar teste antigo, novo, regressão e preservar evidências | Fluxo determinístico implementado |
| Descobrir causa e arquivos apenas com relato do usuário | Não qualificada |
| Criar o plano de testes e testes completos sem estrutura pronta | Não qualificada |
| Interpretar falhas e decidir novas edições por conta própria | Não qualificada |
| Implementar funcionalidade em vários arquivos e camadas | Não qualificada |
| Aprender continuamente sem regressões nas habilidades anteriores | Treinos e certificados separados; promoção geral não implementada |

A próxima prova de autonomia precisa reduzir a ajuda do professor e conter problemas fora das famílias atuais, com critérios congelados antes do treino. Falha deve continuar visível e nenhuma solução escrita por Codex deve ser atribuída ao modelo.
