# Estado privado de execução — preencher em uma cópia

**Status inicial:** PENDENTE. Nenhum teste ou treinamento foi executado por este template.  
**Regra:** manter este registro fora do Git, do RAG e do dataset. Nunca registrar tokens, senhas ou dados privados desnecessários.

## Identificação

| Campo | Valor inicial |
|---|---|
| Instalação | NAO_IDENTIFICADA |
| Data/hora e fuso local | NAO_REGISTRADOS |
| Executor e permissões reais | NAO_VERIFICADOS |
| Caminho do pacote | NAO_REGISTRADO |
| Repositório e branch locais | NAO_VERIFICADOS |
| Commit local e alterações humanas | NAO_VERIFICADOS |
| Diretório de dados ativo | NAO_CONFIRMADO |
| Área privada de experimentos | NAO_CONFIGURADA |
| Interpretador e ambiente | NAO_HOMOLOGADOS |
| Modelo textual e revisão | NAO_REGISTRADOS |
| Modelo visual e revisão | NAO_REGISTRADOS |
| Nível-alvo N1/N2/N3/N4 | NAO_APROVADO |
| Autorizações pendentes | NAO_REVISADAS |

## Progresso por etapa

| ID | Etapa | Estado | Evidência/hash | Bloqueio/próxima ação |
|---|---|---|---|---|
| SET-01 | Inventário e preservação das mudanças locais | PENDENTE | NENHUMA | Inspecionar ambiente |
| SET-02 | Backup e restauração em laboratório | PENDENTE | NENHUMA | Confirmar dados ativos |
| SET-03 | Dependências e suíte de código | PENDENTE | NENHUMA | Preparar ambiente dedicado |
| MOD-01 | Homologação textual real | PENDENTE | NENHUMA | Checkpoint/licença/recursos |
| MOD-02 | Homologação visual real | PENDENTE | NENHUMA | Pipeline/licença/recursos |
| KNO-01 | Importação e validação das sete notas | PENDENTE | NENHUMA | Projeto/servidor parado |
| ENG-01-06 | Manifesto, dados, avaliador, trainer e promoção | PENDENTE | NENHUMA | Inspecionar/implementar lacunas |
| ENG-07-11 | Memória, pipeline visual e retomada | PENDENTE | NENHUMA | Conforme escopo aprovado |
| ENG-12 | Agente geral com ferramentas | PENDENTE | NENHUMA | Executor isolado e testes |
| DAT-01 | Dataset autorizado e partições | PENDENTE | NENHUMA | Curadoria e direitos |
| TXT-TRAIN | Piloto e treinamento textual | PENDENTE | NENHUMA | Pré-requisitos bloqueantes |
| VIS-TRAIN | Decisão e eventual treino visual | PENDENTE | NENHUMA | Necessidade/dados/revisão |
| EVAL-01 | Avaliação final separada | PENDENTE | NENHUMA | Manifesto/candidato |
| REL-01 | Aprovação, promoção e rollback | PENDENTE | NENHUMA | Evidência e decisão humana |
| REP-01 | Relatório final da instalação | PENDENTE | NENHUMA | Consolidar resultados reais |

## Sessão atual

Objetivo delimitado: NAO_DEFINIDO.  
Limites de tempo/passos/disco/memória/tentativas: NAO_APROVADOS.  
Processos e jobs ativos: NAO_CONFERIDOS.  
Última operação confirmada e recibo: NENHUMA.  
Próxima ação exata: inspecionar código, estado da instalação e permissões.

## Registro de transições — acrescentar, não apagar histórico

| Horário | Etapa/tentativa | Estado anterior → novo | Comando/procedimento real | Artefato/hash | Autor da decisão |
|---|---|---|---|---|---|
| NAO_EXECUTADO | NENHUMA | PENDENTE | NENHUM | NENHUM | NENHUM |

## Regras de retomada

Verificar se há job/processo ainda ativo antes de repetir. Conferir revisão e hashes. Não repetir download/importação/treino com recibo válido. Não marcar erro como concluído para liberar a próxima etapa. Se o escopo mudou, criar decisão registrada; não alterar retroativamente a definição de sucesso.

## Encerramento e limpeza — não preencher antecipadamente

| ID | Verificação | Estado | Evidência/hash |
|---|---|---|---|
| CLOSE-01 | Todos os requisitos aplicáveis conferidos; nenhum bloqueio obrigatório | PENDENTE | NENHUMA |
| CLOSE-02 | Aceite final real e critérios atendidos | PENDENTE | NENHUMA |
| KEEP-01 | Sete notas preservadas e recuperação retestada | PENDENTE | NENHUMA |
| KEEP-02 | Relatórios, modelos, datasets, backups e diário preservados | PENDENTE | NENHUMA |
| CLEAN-01 | Inventário restrito de remoção revisado | PENDENTE | NENHUMA |
| CLEAN-02 | Commit de limpeza, testes/CI e push confirmados | PENDENTE | NENHUMA |

A limpeza permanece BLOQUEADA enquanto CLOSE-01, CLOSE-02, KEEP-01 ou KEEP-02 não estiverem concluídos com evidência. Atualize esta tabela somente na cópia privada, que não será apagada.
