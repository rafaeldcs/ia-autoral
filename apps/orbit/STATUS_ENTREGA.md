# Orbit — integração de projetos, Git e homologação

## Estado da entrega

Implementação em andamento. O núcleo inicial de validação e execução Git passou
em 60 testes reais no Linux (40 novos casos de Git e 20 casos anteriores de fluxo).
Isso **não** comprova pull/push autenticado, interface integrada ou deploy completo.
O servidor ShopAir ainda não foi alterado por esta entrega.

O Orbit original foi preservado em `apps/orbit`, no repositório `ia-autoral`,
para manter o histórico sem alterar a pasta original do experimento.

## Autoria e verificação

O código original de setembro foi escrito majoritariamente pelo Codex. Os novos
arquivos `GitPolicy`, `GitUrlPolicy`, `GitBranchPolicy`, `GitProcess`, `GitStart` e
`GitReadOutput` foram escritos pelo modelo local Qwen3-8B Q4_K_M, com revisão do
Codex. Um método emitido sem classe foi reunido com o cabeçalho de classe de outra
resposta da própria IA. Os testes e os controles do laboratório são do Codex.

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
