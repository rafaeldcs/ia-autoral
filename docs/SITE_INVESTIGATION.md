# Investigação assistida de sistemas

O LocalAuthor agora guarda mapas de telas por projeto e permite consultá-los no modo **Consultar sistema investigado**. O mapa distingue telas observadas, pendentes e bloqueadas. Cada observação contém origem HTTPS, data, observador, hash da captura, descrição e rótulos dos controles. As respostas indicam suas fontes e avisam quando a observação está antiga ou quando falta evidência.

Essa capacidade é memória estruturada com busca textual. Não é treinamento dos pesos nem navegação neural autônoma. Nesta versão, um navegador/operador autorizado coleta e revisa as observações. O servidor não recebe senhas, não abre sites, não executa instruções das páginas e não transforma botões encontrados em ações automáticas. A navegação assistida e os resultados do modelo devem continuar sendo atribuídos separadamente.

## Fluxo de investigação

1. Definir o projeto, a origem autorizada, o perfil de acesso e o objetivo de leitura.
2. Autenticar no navegador com credencial protegida, fora do chat e do corpus. Não copiar cookies, cabeçalhos ou valores de campos para as observações.
3. Descobrir menus e abas a partir da interface visível, sem inventar rotas. A presença de um botão não comprova que a funcionalidade funciona.
4. Abrir telas de leitura e esperar o carregamento terminar. Registrar estrutura, limitações, origem e data. Não interpretar dados em cache como dados atuais.
5. Registrar separadamente telas não visitadas, erros, restrições de perfil, estados vazios e fluxos que exigem alterações.
6. Revisar o mapa antes da importação. Excluir dados de clientes, valores de registros, credenciais e instruções não confiáveis. Nunca confundir uma regra descrita na tela com uma regra funcionalmente testada.
7. Consultar pelo chat e conferir a fonte. Uma consulta sem evidência pede nova investigação; não inventa comportamento.

Nenhuma exploração genérica deve clicar em pagar, cobrar, reembolsar, excluir, enviar mensagem, salvar configuração ou conceder acesso só porque o elemento aparece no navegador. Controles que abrem formulários e controles que enviam alterações precisam ser distinguidos pelo contexto. O coletor desta versão não possui executor de ações remotas.

## Arquitetura e API

A implementação usa SQLite já existente, duas tabelas de acompanhamento e fontes versionadas do projeto. Não adiciona serviço externo, API de IA, modelo pré-treinado ou dependência de navegador ao servidor. O coletor externo é responsável pela navegação e pela proteção de credenciais. O núcleo preserva as observações no servidor central para os clientes da rede consultarem.

- `POST /api/investigations`: cria o mapa com `project_id`, `name` e `origin`.
- `GET /api/investigations?project_id=...`: retorna telas e cobertura declarada.
- `POST /api/investigations/observe`: recebe `project_id`, `investigation_id` e `screen`.
- `POST /api/chat` com `mode=investigation`: consulta as observações do mapa mais recente do projeto.

Todas as rotas exigem a autenticação local já existente. As observações aceitam apenas o esquema declarado. Campos como senha, cookies, estado de sessão e valores dos formulários são rejeitados. A origem deve coincidir exatamente; endereços com credenciais, parâmetros sensíveis e outros domínios são rejeitados. Não há requisição de rede durante a importação ou consulta. O hash identifica a captura declarada pelo observador; não é assinatura nem prova independente de que o coletor é confiável.

Os controles de armazenamento complementam a revisão, mas não são um detector universal de dados sensíveis. A coleta deve minimizar os dados na origem. Nenhuma fonte importada autoriza automaticamente treinamento: `training_allowed=false`.

## Importação de uma coleta revisada

O arquivo de trabalho fica em pasta privada fora do Git. O usuário final consulta pelo chat, sem precisar abrir o arquivo de coleta.

```powershell
python scripts/import-screen-map.py --screens C:\privado\screens.json --project-root C:\Projetos\SistemaQA --name "Sistema QA" --origin https://qa.example.com --reviewed
```

O comando cria um mapa novo, preservando mapas anteriores. O relatório de importação é atualizado a cada tela; uma interrupção não se transforma em conclusão. O mapa mais recente pode estar parcial. A cobertura se refere somente às telas descobertas e nunca afirma que todas as telas do sistema são conhecidas.

No aplicativo, selecione o projeto e **Consultar sistema investigado**. Exemplos:

- “Mostre o mapa e as pendências da investigação.”
- “Onde vejo o estoque externo?”
- “Como funciona a precificação?”

A busca é textual e não compreende todo sinônimo ou pergunta complexa. Para números atuais, ações reais ou investigação de telas novas, é necessária nova coleta autorizada. O modelo neural permanece disponível separadamente, com suas limitações já documentadas.
