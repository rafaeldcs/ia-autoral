# Backlog de conclusão — o que realmente falta

Atualização: consulte [PROGRESS_WINDOWS.md](PROGRESS_WINDOWS.md) para o estado de todos
os 22 itens após a validação no notebook. Esta tabela preserva os critérios de aceite;
avanços parciais não foram convertidos em itens totalmente concluídos.

Esta lista não transforma documentação em implementação. Prioridade P0 = impede declarar o agente programador pronto; P1 = robustez/escala/experiência; P2 = expansão. Os itens não foram criados como issues remotas, pois não houve escrita no GitHub.

| ID | Prioridade | Entrega faltante | Critério de aceite |
|---|---|---|---|
| REM-001 | P0 | Publicação privada e CI real | Repo privado existente, SHA remoto verificável, Python Linux/Windows e .NET compilados |
| REM-002 | P0 | Validação do notebook | Diagnóstico real, abertura da UI, 119+ testes, backup/restauração e teste offline no Windows |
| REM-003 | P0 | Auditoria do executor isolado | Executar imagem local confiável, verificar bloqueio de rede/acesso externo/recursos/filhos, sem shell do host |
| REM-004 | P0 | Corpus de programação autorizado | Fontes/permissões reais, famílias disjuntas, dados limpos, teste final separado |
| REM-005 | P0 | Avaliador independente de tarefas | Conjunto inédito de tarefas, verificador que o agente não altera, métricas por caso e baseline |
| REM-006 | P0 | Modelo que demonstra capacidade | Resolver classe declarada de problemas inéditos sem professor; reportar falhas e não só loss |
| REM-007 | P0 | Agente generativo real | Converter evidências/pedido em proposta estruturada; schema/permite/limites validados fora do modelo; revisão final |
| REM-008 | P0 | Implementação CUDA e escala | Forward/backward corretos contra CPU, compatibilidade RTX 2060, VRAM e throughput medidos |
| REM-009 | P0 | Migrar arquitetura para C# se mantido o plano | Domínio/aplicação/infraestrutura compilados/testados em .NET, sem ocultar dependência do Python |
| REM-010 | P1 | Roslyn de verdade | Símbolos/referências/diagnósticos semânticos, seleção de contexto C# e testes específicos |
| REM-011 | P1 | Pacote offline/instalador | Runtimes/dependências licenciados, hashes, instalação sem rede e teste com saída bloqueada |
| REM-012 | P1 | Hardening Windows e ACLs | Usuário/ACL de dados/runner, junction/hardlink/race tests e revisão independente |
| REM-013 | P1 | Pesquisa real e atualização por versão | Testes live autorizados, domínios reais, regras de versões/contradições, fonte e motivo rastreáveis |
| REM-014 | P1 | Busca mais inteligente | Avaliação de relevância, expansão de conceitos verificada; encoder próprio separado se necessário |
| REM-015 | P1 | Navegação e acessibilidade da UI | Playwright completo, teclado/mobile/erros, renderização de conteúdo malicioso inerte |
| REM-016 | P1 | Treinamento com maior volume | Loader streaming, escalonamento/checkpoints/validação, métricas e profiling; sem corpus inteiro na RAM |
| REM-017 | P1 | Promoção/rollback de modelo | Candidato congelado, avaliação/regressão, aprovação explícita e restauração de versão anterior |
| REM-018 | P1 | Quotas e retenção totais | Disco/RAM/workspaces/histórico medidos e limitados, coleta de checkpoints, reação a disco cheio |
| REM-019 | P1 | Recuperação e backups robustos | Streaming, cópia externa, testes de queda entre escrita/fsync/rename, perda real/corrupção detectada |
| REM-020 | P1 | Evidência de testes confiável | Garantir que testes relevantes executaram; projetos não podem substituir o avaliador ou fabricar aprovação |
| REM-021 | P1 | Observabilidade e manutenção | Diagnóstico sem segredos, migrações de esquema, telemetria apenas local e documentação de incidentes |
| REM-022 | P2 | Expansão de linguagens/contexto | TypeScript e múltiplos arquivos apenas após avaliação separada |

## Ordem de execução sugerida

Publicação/diagnóstico/CI/UI → isolamento/eval/corpus → motor GPU e treinamento medido → integração generativa controlada → consolidação C# e empacotamento. A migração para C# pode acontecer em paralelo, mas não substitui criar capacidade no modelo.

## Mapeamento do plano original

| Fase | Cobertura real nesta entrega |
|---|---|
| 0 diagnóstico | Comando implementado; notebook não medido |
| 1 aplicação | Núcleo/UI/API reais; Python em vez de domínio C#; host .NET não validado |
| 2 memória | Fontes/versões/FTS5/relações; símbolos apenas lexicais; inteligência semântica pendente |
| 3 pesquisa | Coleta/cache/políticas implementadas com testes simulados; descoberta e compreensão gerais não implementadas |
| 4 motor CPU | Autodiff/tokenizadores/Transformer/otimizador/checkpoints reais e numericamente testados |
| 5 GPU | Não implementada |
| 6 corpus | Validador/manifesto implementados; corpus real e benchmark final ausentes |
| 7 treinamento | Loop/resume reais, testes minúsculos; modelo competente não treinado |
| 8 agente | Revisão manual/importada e executor opt-in; geração/autocorreção por modelo não liberadas |
| 9 melhoria | Feedback registrado; seleção/promoção/retraining governados ainda não implementados |
| 10 distribuição | Fonte/documentação/testes; sem binário offline, sem CI remoto, sem validação no notebook |
