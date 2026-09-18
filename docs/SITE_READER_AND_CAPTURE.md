# Leitor de finalidade e captura própria — experimental

O LocalAuthor agora tem dois recursos separados: classificar a finalidade de
evidências estruturais fornecidas e fotografar páginas públicas pelo seu próprio
navegador. Isso não qualifica investigação autônoma de qualquer site.

## Arquitetura e dependências

- `site_reader.py`: duas redes autorais NumPy, cada uma com 4.096 entradas,
  camada de 64 unidades GELU e saída para 7 finalidades de site ou 38 de tela.
  Título e elementos visíveis ocupam canais separados. Nome da marca e URL não
  escolhem a resposta. A representação perde ordem e relações entre elementos.
- `qa/site_reader_course.py`: exemplos fictícios escritos para este curso.
  Nenhum registro privado de site foi incorporado ao treino. Treinar requer
  o NumPy já declarado no extra `training`; o roteiro usa `LOCALAPPDATA` no Windows.
- A resposta é uma descrição fixa da categoria escolhida pelos pesos. Não é
  texto livre gerado nem compreensão visual dos pixels. Escores não são calibrados.
- `capture_decision.py`: usa a política neural autoral de investigação já
  existente. Um adaptador fornece estados observáveis; a política propõe `RECORD`.
  Controles determinísticos verificam origem, acesso, carregamento e senha
  preenchida. Outras propostas não são substituídas por uma captura.
- `capture_browser.cjs`: ferramenta revisada do LocalAuthor, com Playwright e
  Chromium da imagem existente `localauthor-functional-lab:1`. Não executa
  JavaScript gerado pelo modelo, não usa navegador do Codex nem API externa de IA.
- `browser_capture.py`: exige Docker disponível e imagem instalada. Verifica
  usuário sem privilégios, raiz somente leitura, capabilities removidas, seccomp,
  limites de memória/CPU/processos e mounts antes de executar. Falha sem alternativa
  de execução no host. O único diretório gravável montado é a saída da execução.

## Executar captura no Windows

Na distribuição-fonte, com o ambiente Python ativado e `PYTHONPATH=src`:

```powershell
python -m localauthor capture https://example.org/ --allow-network --policy-report C:\dados\investigation-lab\report.json
```

O relatório deve apontar para uma política aprovada no laboratório, com hash
correspondente ao checkpoint. `scripts/capture-with-local-ai.py` chama o mesmo
comando. O usuário fornece de 1 a 12 URLs; o modelo não descobre esses destinos.
Use `--asset-host dominio.exemplo` para autorizar explicitamente um domínio de
recursos necessário. `--allow-network` vale apenas para esta execução e não muda
a configuração offline persistida.

São aceitos destinos HTTPS públicos, sem credenciais ou parâmetros sensíveis.
O DNS é validado e fixado no container; o navegador permite GET/HEAD dos hosts
explicitamente autorizados e bloqueia service workers. Trata-se de filtro da
ferramenta, não de firewall completo de saída. Recursos bloqueados podem resultar
em páginas parcialmente carregadas. Cada URL abre uma sessão limpa, sem login,
cookies importados, uploads ou downloads. Não use esta versão para fluxos com
segredos ou operações de negócio.

As saídas ficam em `LocalAuthor/investigations/own-browser-<data>` no diretório
local de dados: PNG por página, `captures.json` com decisão e hash do artefato e
`runtime.json` com evidência do executor. Captura recusada ou falha fica registrada
e o comando retorna erro. Sucesso exige evidência para todas as URLs solicitadas.

Este recurso está disponível por comando experimental. Não foi adicionado um
botão ao chat nem regenerado o instalador de desktop nesta entrega.

## Treino, respostas e auditoria

```powershell
python scripts/teach-site-reader.py --corrective
python scripts/describe-site.py --report C:\dados\curso\report.json --observations C:\dados\observations.json --output C:\dados\response.json
python scripts/audit-site-responses.py --response C:\dados\response.json --expected C:\dados\expected.json --output C:\dados\audit.json
```

O treino preserva checkpoints anteriores e registra hashes das fontes, do
manifesto e das avaliações. Seleciona o checkpoint pela validação, sem gradiente
nos exemplos de teste. As correções foram orientadas por erros vistos durante o
desenvolvimento: esta avaliação repetida não é um teste independente de novos
sites. O candidato não substitui automaticamente o modelo ativo do chat.

`describe-site.py` produz JSON e Markdown com todas as escolhas, inclusive erros.
Telas pendentes ou bloqueadas permanecem sem previsão. A auditoria compara a saída
com categorias congeladas antes das previsões e rejeita omissões ou mudança na
evidência. Não se deve editar respostas para fazê-las coincidir com o gabarito.

## Evidência e limites

Em 18/09/2026, duas páginas públicas reais foram capturadas pelo navegador do
LocalAuthor: ShopAir e YouTube, ambas com proposta `RECORD`, PNG e hash verificados.
As imagens e recibos ficam fora do Git. Isso comprova a execução da ferramenta,
não navegação autônoma, login, compreensão de layout ou validação de regras de negócio.

O conjunto ShopAir contém 71 observações estruturais anteriores, uma bloqueada e
cinco pendentes. A coleta original foi feita pelo Codex; não foi refeita pelo
modelo local. O conjunto YouTube contém duas observações ao vivo e dez entradas
derivadas da [documentação oficial](https://support.google.com/youtube/answer/2398242?co=GENIE.Platform%3DDesktop&hl=pt-BR),
além de duas áreas bloqueadas por login. Acertos nesse conjunto não significam
doze telas reais operadas pela IA.

O primeiro leitor acertou 52/71 categorias ShopAir e 10/12 YouTube. A versão com
canais separados e lições contextuais chegou a 70/71 e 12/12, com 128/128 casos de
validação e 128/128 de auditoria sintética. Todas as tentativas foram preservadas.
Na última execução desta entrega, os números permaneceram 70/71 e 12/12; houve
uma confusão entre configuração e estruturação de formulários. Correções de
lições também causaram regressões em outras categorias durante as tentativas.
Nenhum desses erros foi removido do histórico ou corrigido manualmente na saída.
Os relatórios privados de cada execução são a fonte dos resultados detalhados.

A suíte obrigatória é `python scripts/run-tests.py`. Além dela, validar a captura
exige executar o comando com Docker real e verificar os PNGs/recibos. Testes de
software aprovados não certificam todos os sites ou todos os comportamentos da IA.

Validação desta entrega: 210 testes de software passaram em Linux no container,
sem falhas nem testes pulados. A execução real de captura produziu 2/2 PNGs
verificados. Esses totais são separados dos acertos do classificador acima.
