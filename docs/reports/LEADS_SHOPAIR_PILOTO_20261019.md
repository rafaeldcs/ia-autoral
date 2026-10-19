# Leads ShopAir com contexto e revisão

## Resultado entregue

Implementados inbox por projeto, contexto comercial versionado com fontes/data, ingresso autenticado e deduplicado, histórico, recusa persistente de contato, fila de análise local, rascunho por seleção de textos aprovados, revisão/rejeição com feedback, movimentação de funil e contagens por campanha. A tela tem navegação, busca/filtros e layout móvel. Ela está disponível em `/leads` no servidor desta instalação, inclusive pelo gateway HTTPS atualizado.

A ponte opcional entre servidores inclui relay HTTP restrito a loopback para receber eventos atrás de proxy HTTPS, fila SQLite persistente, chaves de leitura/escrita distintas, consulta pelo servidor LAN, recibo por hash depois do commit, deduplicação de retries e vínculo de fila a projeto. A tela **Conectar site** salva a chave por DPAPI do usuário Windows e permite coleta periódica/pausa. O guia [LEADS_LOCAL.md](../LEADS_LOCAL.md) inclui comandos, contrato, proxy de exemplo e limites de armazenamento. Não acrescentamos dependência de IA remota ou biblioteca nova.

Ainda dependem da hospedagem/contas: domínio público, configuração HTTPS, instalação do relay e adaptação do formulário real da ShopAir. Não houve implantação pública, entrada real por Meta/WhatsApp, prospecção irrestrita ou envio de mensagens. A captura local/manual e a ponte testável não são esses conectores. A configuração da hospedagem foi solicitada ao proprietário sem pedir segredos no chat.

## Participação da LocalAuthor

O motor local Qwen3.5-4B gerou o rascunho do validador das propostas e depois três substituições corretivas. Quatro versões completas tinham defeitos e foram rejeitadas: booleanos aceitos como inteiros, exigência indevida de fato em todos os casos, detecção incorreta de repetição, tipagem/aliasing. O supervisor explicou contraexemplos, revisou as correções e removeu um bloco duplicado. A versão aplicada passou nos contratos adversariais em Docker offline, com root somente leitura, usuário sem privilégios, sem rede externa/mounts e limites de memória/CPU. Uma primeira coleta de sandbox deixou de incluir os arquivos da interface e falhou no teste de estáticos; corrigir o pacote produziu 27 testes aprovados, sem remover o teste.

O restante da integração, interface, controles, testes e implantação local foi feito pelo supervisor. Não foi trabalho autônomo completo do modelo. Não houve treinamento de pesos nem importação dos exemplos para corpus. As respostas rejeitadas, correções, fontes e hashes foram mantidos privados.

## Ensaio real de classificação

Usamos o manifesto GGUF já registrado: `unsloth/Qwen3.5-4B-GGUF`, revisão `e87f176479d0855a907a41277aca2f8ee7a09523`, em runtime CUDA Docker offline. Os registros privados identificam hashes dos módulos realmente executados. Modelos não foram baixados ou promovidos por esse teste.

No primeiro ensaio de seis cenários fictícios, a pergunta vaga de preço foi qualificada indevidamente. O supervisor aprimorou as definições do pedido, preservando essa tentativa. No segundo ensaio, com três casos adicionais, houve **sete classificações esperadas em oito inferências**; a nona entrada era recusa explícita, bloqueada antes do modelo. Os controles de separação de pesquisa, ausência de envio, rascunhos restritos e revisão pendente foram mantidos em todos os nove cenários.

O resultado não homologa marketing autônomo: o modelo ainda interpretou uma empresa pesquisada como sem encaixe por causa de conteúdo malicioso da página, escolheu fatos que não justificavam uma conclusão em um caso e repetiu perguntas já respondidas. A pesquisa permaneceu na etapa de pesquisa, sem rascunho de contato. A aplicação limita as ações, mas não transforma classificações semanticamente erradas em acertos. O conjunto foi de desenvolvimento interno, não um teste independente reservado.

Um projeto separado **ShopAir — Simulação de leads** foi criado na instalação ativa com cinco entradas fictícias. Três análises foram geradas pelo modelo real através da fila persistente; nenhuma foi aplicada como revisão humana. Pesquisa e bloqueio permanecem identificados. Não misturamos essas entradas com contatos reais de clientes.

## Validação de software e implantação local

- **628 testes locais executados: 625 aprovados, zero falhas/erros e três skips de symlink por privilégio indisponível no Windows.** A suite foi executada com UTF-8, preservando os relatórios anteriores com falhas. Atualizamos a fixture de fechamento para incluir o novo coletor e acrescentamos teste de que um coletor ativo impede descarte dos outros recursos.
- Nove fluxos no Edge com HTTP, fila e persistência reais: contexto, evidências/revisão, funil, pesquisa, bloqueio, invalidação de contexto, configuração/pausa da fila, celular e troca de projeto. Inferência e proteção do segredo da fixture de navegador são dublês, identificados nos relatórios; não provam qualidade do modelo. DPAPI também teve round trip separado real no Windows, com segredo descartável não impresso.
- Relay testado com HTTP real de loopback, incluindo falha depois do commit local e antes do recibo, repetição, conflito, chaves distintas e reinício. Isso não certifica o domínio HTTPS público ainda não configurado.
- Gateway .NET compilado e publicado sem restauração/download de dependências, sem avisos/erros. Cinco verificações com TLS real, certificado validado e dispositivo temporário: rotas estáticas, API, bloqueio de anônimo e status de conexão. Não houve teste em um segundo computador físico. O teste encontrou um reset de keep-alive durante encerramento do gateway; o backend passou a encerrar esse transporte sem traceback espúrio, mantendo as verificações HTTP existentes.
- Bancos e configuração de runtime foram preservados em backup privado antes da ativação. O backend foi encerrado por Ctrl+C com verificação de identidade/console e fila ociosa, sem término forçado ou remoção de lock ativo. O gateway novo foi instalado em outra pasta, preservando o anterior. Após reinício, a tela/API local e a página HTTPS LAN responderam; o navegador exibiu apenas dados do projeto de simulação.

Capturas, banco de laboratório, relatórios completos, backups e saídas de modelos ficam fora do Git. O CI remoto deve ser conferido pelo SHA do commit publicado; jobs em fila não constituem aprovação. A publicação do código não equivale a implantar a ponte no site ou treinar o checkpoint.

## Continuação necessária

Configurar o domínio/hospedagem informado pelo proprietário, instalar o relay atrás de HTTPS, integrar e verificar a preferência de contato no backend do formulário, preencher **Conectar site** e conferir um evento sintético ponta a ponta pelo domínio real. Adaptadores de contas Meta/WhatsApp e medição de conversões reais são etapas separadas. Antes de habilitar qualquer envio, ampliar a avaliação semântica com casos reservados e revisão humana; esta entrega continua assistida.
