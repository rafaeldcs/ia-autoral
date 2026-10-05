---
id: la-criacao-visual
version: 1
kind: knowledge
status: material_didatico_nao_homologado
training_allowed: false
reviewed_by: null
---
# Criação visual: brief, composição e avaliação

Este documento é conhecimento consultável, não autorização de execução nem comprovação de competência. A aprovação de uso em treinamento é separada.

## Transformar o pedido em um brief verificável

Extrair finalidade, assunto principal, quantidade de objetos, ação, enquadramento, fundo, iluminação, cores, estilo, dimensões e restrições. Separar requisitos obrigatórios de preferências. Não acrescentar um elemento importante que contradiga o pedido apenas porque melhora a aparência.

Exemplo de brief didático: “um único vaso amarelo, centralizado, fundo azul-claro uniforme, sombra suave, imagem quadrada, sem texto”. Os requisitos verificáveis são quantidade, objeto, cor, fundo, enquadramento e ausência de texto. O resultado precisa ser inspecionado para confirmar isso.

## Composição e clareza

Definir o ponto de atenção principal e o espaço disponível. Evitar excesso de elementos quando o uso exige leitura em tamanho pequeno. Para ícones, priorizar silhueta reconhecível e consistência entre itens; para produto, preservar forma, proporção e detalhes relevantes.

Descrever iluminação, ângulo e material somente quando contribuírem ao resultado. Um prompt longo e contraditório pode ser menos útil que um brief curto e coerente. Se exceder o tokenizador do pipeline, resumir conscientemente preservando requisitos, sem truncamento silencioso.

## Cores, texto e formatos

Conferir as cores no resultado; o texto do prompt não prova que a cor foi respeitada. Texto legível dentro de imagem é um requisito de qualidade, não garantia do gerador. Quando o objetivo admite composição tipográfica por uma ferramenta gráfica local autorizada, registrar essa operação como composição separada, não como pixel gerado pelo modelo.

Uma imagem PNG pode ter ou não canal alpha/transparência. Não prometer fundo transparente ou resolução diferente sem suporte e verificação. O perfil atual do LocalAuthor é quadrado 512 × 512; novos formatos exigem implementação e teste.

## Consistência visual

Séries de ícones ou personagens precisam manter convenções de proporção, materiais, iluminação e paleta. Uma seed fixa pode ajudar no controle experimental, mas não garante identidade visual ou reprodução idêntica em qualquer ambiente. Registrar modelo, pipeline, parâmetros e versões, e avaliar a série inteira.

Especialização de estilo pode exigir dados e treinamento visual próprios. Melhorar o texto do brief não é retreinar os pesos do gerador.

## Visualizar, revisar e registrar

Avaliar aderência ao brief, composição, formas, artefatos, texto e adequação ao uso. Um sistema só textual não deve afirmar que viu a imagem. Usar visualização real por humano ou módulo visual explicitamente identificado. Salvar PNG, hash, prompt efetivo, modelo e decisões.

Geração, compreensão e edição são capacidades diferentes. Não dizer que editou uma imagem original se criou outra a partir de texto. Edição futura deve receber o original autorizado e preservar uma cópia.

## Dados e pessoas

Usar imagens de treinamento com origem e direitos revisados. Quando houver pessoas identificáveis ou material privado, conferir consentimento e finalidade. Não transformar automaticamente fotos pessoais ou arquivos de clientes em corpus. Não contornar os controles de conteúdo do pipeline para obter um resultado bloqueado.
