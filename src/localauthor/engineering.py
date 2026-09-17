"""Human-authored project guidance, distinct from neural model output."""
SOURCES = [
    {"title": "Botões e ações — W3C", "url": "https://www.w3.org/WAI/ARIA/apg/patterns/button/"},
    {"title": "Links e navegação — W3C", "url": "https://www.w3.org/WAI/ARIA/apg/patterns/link/"},
    {"title": "Convenções de C# — Microsoft", "url": "https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions"},
    {"title": "Scrum Guide", "url": "https://scrumguides.org/scrum-guide.html"},
    {"title": "The Kanban Guide", "url": "https://kanbanguides.org/the-kanban-guide/"},
]
QUALITY = [
    "Projetar para a tarefa da pessoa: ação com botão e verbo claro; navegação com link e destino; informação sem aparência clicável.",
    "Prever primeiro acesso, carregamento, erro e sucesso; preservar o que foi digitado e explicar o próximo passo.",
    "Verificar teclado, foco visível, nomes acessíveis, contraste e tela pequena; validar compreensão com pessoas leigas.",
    "Responder em português claro, revisar concordância e acentos e informar o que foi ou não verificado.",
    "Preservar nomes, strings, indentação e comentários do código; mudar somente o que foi solicitado.",
    "Escapar valores conforme o destino (JSON, HTML, C#), sem substituir aspas ou aplicar escape globalmente ao código.",
    "Nomes que expliquem a intenção e funções com responsabilidade clara.",
    "Solução simples para o requisito atual; abstrações quando houver necessidade demonstrada.",
    "Validação nas fronteiras, erros explícitos e autorização verificada no servidor.",
    "Testes do comportamento e dos casos de erro; executar e registrar o resultado.",
    "Revisar diferenças, preservar dados e explicar mudanças, decisões e limitações.",
    "Consultar documentação oficial da versão usada; registrar fonte e data, sem inventar pesquisa.",
]
DONE = "Critérios de aceite atendidos; testes relevantes executados; revisão concluída; documentação e riscos atualizados."


def guidance(message, method, project_name):
    text = message.casefold()
    if any(word in text for word in ("usabilidade", "intuitiv", "interface", "leig", "botão", "botões", "botao", "botoes", "hiperlink", "acessibilidade")):
        answer = ("Comece pela tarefa de quem vai usar: a pessoa deve reconhecer o próximo passo sem treinamento. "
                  "Use botão nativo para executar uma ação, com texto como Salvar ou Nova conversa. Use link com href "
                  "para navegar a um destino; sublinhe os links para que sejam reconhecíveis. Evite ícones isolados "
                  "e aparência de botão em informação sem ação. O rótulo deve descrever o efeito real: preencher uma "
                  "mensagem não é enviá-la. No primeiro acesso, explique como começar. Durante uma operação, mostre "
                  "o estado; se falhar, preserve o texto e explique como tentar novamente. Verifique Tab, Enter, Espaço, "
                  "Escape, foco visível, leitura dos controles e uso no celular. Exemplo de ação: "
                  '<button type="button">Salvar</button>. Exemplo de navegação: <a href="/projetos">Ver projetos</a>. '
                  "Antes de concluir, peça a pessoas leigas que realizem uma tarefa sem dicas e observe onde hesitam. "
                  "Testes automáticos passando não provam que a interface é intuitiva. Este é um guia escrito e revisado, "
                  "não evidência de aprendizado neural. Referências consultadas em 17/09/2026.")
    elif any(word in text for word in ("comentário", "comentario", "aspas", "português", "portugues", "ortografia", "input text", "quebrar", "acentos")):
        answer = ("Separe explicação e código. Na explicação, use português claro, concordância correta e descreva o resultado "
                  "e o que ainda falta verificar. No código, preserve identificadores, strings, espaços e quebras de linha; "
                  "não troque aspas retas por aspas tipográficas. Só altere o trecho solicitado. Valores devem ser escapados "
                  "conforme o contexto: um atributo HTML, uma string C# e JSON têm regras diferentes. Não aplique escape ao "
                  "arquivo inteiro. Para comentários com delimitadores ou múltiplas linhas, escolha uma forma que não feche "
                  "o comentário antes da hora. Confira a sintaxe e os testes antes de dizer que está pronto. No chat, o modo "
                  "Código preserva a apresentação e desliga correção ortográfica; Copiar mensagem copia o texto armazenado.")
    elif any(word in text for word in ("pesquis", "documenta", "versão", "versao")):
        answer = ("Para pesquisar: identifique a versão da tecnologia e a dúvida concreta, consulte a documentação oficial, "
                  "registre URL e data e verifique a recomendação em um exemplo testável. Esta resposta é um guia local: "
                  "não fiz uma nova pesquisa na internet. As referências abaixo foram conferidas em 17/09/2026. "
                  "A coleta de URLs autorizadas está disponível nas ferramentas avançadas e respeita o modo offline.")
    elif "kanban" in text or ("fluxo" in text and method == "kanban"):
        answer = ("No Kanban, torne o fluxo visível, explicite quando um item começa e termina e limite trabalho em andamento. "
                  "Antes de iniciar outro item, ajude a concluir ou desbloquear os atuais. Acompanhe WIP, throughput, idade "
                  "dos itens e tempo de ciclo. Um quadro com colunas, sozinho, não garante gestão de fluxo.")
    elif any(word in text for word in ("scrum", "sprint", "backlog")):
        answer = ("No Scrum, conecte o trabalho a um objetivo de produto e defina uma meta para a Sprint. Refine itens com "
                  "critérios de aceite, planeje uma entrega verificável e inspecione o resultado. A Definition of Done "
                  "expressa a qualidade exigida para o incremento. A retrospectiva gera melhorias. Scrum não é apenas "
                  "um quadro de tarefas nem torna um código automaticamente bem escrito.")
    elif any(word in text for word in ("teste", "testar", "pronto", "done")):
        answer = ("Antes de considerar pronto, descreva o comportamento esperado, os limites e os erros. Combine testes "
                  "unitários de regras, integração dos componentes e testes funcionais dos fluxos relevantes. Confirme "
                  "que os testes realmente executaram e detectam defeitos. " + DONE)
    elif any(word in text for word in ("clean", "código", "codigo", "legível", "legivel", "qualidade", "refator")):
        answer = "Para revisar a qualidade, use estes critérios e explique o motivo de cada mudança:\n\n" + "\n".join("• " + rule for rule in QUALITY)
    else:
        answer = (f"Vamos organizar o pedido no projeto {project_name}. Descreva quem usará a funcionalidade, o problema "
                  "e como vamos verificar que ela funciona. Depois, divida em pequenas entregas, identifique riscos e "
                  f"planeje os testes. Método escolhido: {method.upper()}. Posso consultar a memória deste projeto "
                  "ou apresentar os guias de qualidade, testes, pesquisa, Scrum e Kanban. Este modo é orientação "
                  "estruturada, não uma resposta gerada pelo modelo neural.")
    return {"content": answer, "origin": "project_guide", "sources": SOURCES, "researched_now": False}
