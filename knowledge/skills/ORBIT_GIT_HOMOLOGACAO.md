# Aprendizado de implementação e validação: Orbit, Git e homologação

Material de consulta do laboratório LocalAuthor. Consulta não altera pesos nem
autoriza treino. Propostas locais, revisão e testes não comprovam autonomia geral.

## Investigar e escrever

Leia interfaces, SQL, cliente HTTP e permissões antes de editar. Não invente APIs:
Store usa Query/Execute, não métodos de ORM. Account usa role com admin, manager,
member e viewer. Accepted retorna identificador de job, não o estado da tela.

Divida arquivos que falharam em métodos pequenos com contratos explícitos. Devolva
diagnósticos de compilação e comportamento esperado ao modelo. Preserve resposta,
hash, rejeição e correção. Compilar não substitui testar. Exemplos fictícios,
placeholders e JSON inválido não são implementação. Registre montagem de trechos.

## Git e entrega

Valide URL/branch; rejeite credenciais na URL, caracteres de controle e protocolos
alternativos. Git usa ArgumentList sem shell, hooks e redirects desabilitados,
ambiente mínimo e saída limitada. Credencial só no ambiente do processo, nunca
argumento, log ou resposta. Pull exige árvore limpa e avanço direto; push confirma
SHA e nunca força. Revalide papel do usuário quando o job começar: permissões
podem ser revogadas após enfileirar. Apenas admin configura; admin/gestor executa.

Fila aceita não é deploy concluído. Valide SHA imutável, execute testes, publique
apenas a receita permitida, confira saúde e prepare rollback. Execute código
gerado somente no Linux isolado e verificado; dependências em etapa separada.

Ao atualizar o próprio servidor, persista a fase de entrega ANTES de esperar o
pipeline. Após reinício, acompanhe a mesma revisão sem novo push/rerun. Git
interrompido exige revisão. Cancelamento de desligamento difere de timeout. Nunca
declare sucesso para pipeline em falha ou somente iniciado.

## Interface e testes

Rótulos claros: Atualizar código, Enviar commits, Publicar homologação. Labels
associados, erros visíveis e credenciais ocultas. Await em try/catch/finally;
onSaved somente após sucesso. Confirme escrita, mostre revisão, impeça duplicações.
Defina CSS efetivo; relacione chaves de tarefas a commits com limites de palavra.
Teste quatro papéis, links, confirmação/cancelamento, desktop e celular reais.
Capturas ajudam revisão visual; não substituem asserções.

## Falhas concretas deste laboratório

- Regex com `$` aceitou newline final: validação ASCII/limites explícitos corrigiu.
- Comparação http/https após estreitamento de tipo falhou no TypeScript: retirar
  comparação redundante preservando protocolo, host, porta e URL sem credenciais.
- Finally declarou sucesso após erro HTTP: await e onSaved somente no sucesso.
- Método sem classe não é arquivo completo: montar cabeçalho compatível e validar.
- Captura tmpfs por docker cp falhou: tar dentro do sandbox, isolamento revalidado
  e caminhos da extração conferidos antes de exportar evidências.
- Encoding padrão Windows corrompeu português: ler/escrever com UTF-8 explícito.
- Teste confundiu aba e menu equivalentes: selecionar o controle pelo contexto.

Referências: [Git pull](https://git-scm.com/docs/git-pull),
[deploys GitHub](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments),
[Next.js em servidor próprio](https://nextjs.org/docs/app/guides/self-hosting).
