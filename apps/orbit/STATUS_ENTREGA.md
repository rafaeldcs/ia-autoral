# Orbit — integração de projetos, Git e homologação

## Estado da entrega

Implementação integrada e validada no laboratório Linux: 73 testes unitários,
9 cenários de API com PostgreSQL, retomada após reinício, bloqueio de setup,
5 testes da política de pacotes e navegador real nos quatro papéis, desktop e
celular. Compilações .NET Release e Next.js/TypeScript aprovadas.
Esta revisão aguarda primeiro workflow e entrega real em HML; esses testes
**não** comprovam push autenticado ou deploy completo.

Infraestrutura isolada preparada em HML: configuração privada, chave CI restrita
e volume Git de 512 MiB. A rota pública ainda não foi ativada.

O Orbit original foi preservado em `apps/orbit`, no repositório `ia-autoral`,
para manter o histórico sem alterar a pasta original do experimento.

## Autoria e verificação

O código original de setembro foi escrito majoritariamente pelo Codex. Os novos
módulos de Git, fila, entrega, proxy e interface foram propostos pelo Qwen3-8B
local, com revisão do Codex. Métodos/cabeçalhos de respostas locais foram montados
quando o arquivo completo falhou. Testes, controladores e infraestrutura são do
Codex. Hashes UTF-8/LF e tentativas estão em `LOCAL_AI_PROVENANCE.json`; respostas
originais permanecem privadas. Não houve treino de pesos ou qualificação universal.

As primeiras propostas falharam em compilação, APIs, permissões e regras de Git.
Foram preservadas em evidências privadas e não publicadas como implementação.
A divisão em módulos menores e os resultados dos testes foram devolvidos ao
modelo. Registrar essas experiências não significa que os pesos foram treinados.

O laboratório verificou a identidade da imagem Docker, usuário sem privilégios,
sistema de arquivos somente leitura, código montado somente para leitura, ausência
de rede/portas/socket Docker, limites de memória/CPU/processos e área temporária.
Código gerado não foi executado diretamente no Windows.

## Comportamento previsto para a entrega completa

- Projeto Scrum/Kanban ligado a um repositório GitHub e branch explícita.
- Administradores configuram conexão; administradores/gestores executam operações.
- Pull exige árvore limpa e avanço direto; push não usa força e confirma a revisão.
- Commits relacionados às tarefas, fila persistente, auditoria e erros visíveis.
- Deploy separado no servidor HML da ShopAir, por revisão imutável, com testes,
  verificação de saúde e recuperação da versão anterior.

O endereço candidato `orbit.hml-app.shopair.com.br` aponta para o servidor HML e
está coberto pelo certificado existente. A criação da rota depende da validação
da aplicação completa. Os demais sites, bancos e containers devem ser preservados.

Referências: [Git pull](https://git-scm.com/docs/git-pull),
[controle de deploys no GitHub](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
e [Next.js em servidor próprio](https://nextjs.org/docs/app/guides/self-hosting).
