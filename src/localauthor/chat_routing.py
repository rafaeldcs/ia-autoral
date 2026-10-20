"""Automatic local orchestration; rules choose tools, never grant extra rights."""
import re
import unicodedata


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if not unicodedata.combining(c))


def urls(text):
    return list(dict.fromkeys(url.rstrip('.,;!?') for url in re.findall(r'https://[^\s<>"\)]+',text)))


def choose(message,history=()):
    # Code/quoted material is data, not permission to browse or install.
    from .message_format import resolve_message_format
    text=plain(message)
    if resolve_message_format(message,'auto')=='code':return 'foundation','conversation'
    if re.search(r'\bnao\s+(abra|acesse|investigue|pesquise|gere|crie)\b',text):return 'foundation','conversation'
    previous=history[-1].get('metadata',{}).get('routing',{}).get('intent') if history else None
    if previous=='installer' and re.fullmatch(r'(?:chat[, ]+)?(?:me manda o arquivo|mande o arquivo|onde baixo|quero baixar|envie o arquivo)[.!?]*',text):return 'support','installer'
    if re.search(r'\b(instalador|installer)\b',text) or ('localauthor' in text and re.search(r'\b(instalar|baixar|download|arquivo de instalacao)\b',text)):
        creating=re.search(r'\b(crie|criar|construa|construir|desenvolva|implemente|gerar|gere)\b',text)
        own=('localauthor' in text or re.search(r'\b(seu|seus|teu|sua)\b',text))
        standalone=re.search(r'\b(instalador|installer)(?:\s+(?:atualizado|atual|novo))?[.!?]*$',text)
        if not creating and (own or standalone):
            return 'support','installer'
    links=urls(message)
    if previous=='research_scope' and 1<=len(links)<=5 and message.strip() in links:return 'research','research'
    if links and re.search(r'\b(abra|abrir|acesse|navegue|investigue|investigar|telas|navegar)\b',text):
        return ('browser','browser') if len(links)==1 else ('support','research_scope')
    if re.search(r'\b(consulte|consultar|busque|buscar)\b.*\b(memoria|fontes locais|documentos locais)\b',text):return 'knowledge','local_sources'
    if re.search(r'\b(pesquise|pesquisar|busque|buscar|procure|consulte o site|pesquisa na internet)\b',text):
        return ('research','research') if 1<=len(links)<=5 else ('support','research_scope')
    if links and (message.strip()==links[0] or re.search(r'\b(analise|analisar|site|pagina)\b',text)):
        return ('browser','browser') if len(links)==1 else ('support','research_scope')
    if not re.search(r'\b(como|explique|exemplo de codigo)\b',text) and re.search(r'\b(crie|gere)\b.*\b(imagem|ilustracao|foto)\b',text):return 'image','image'
    return 'foundation','conversation'


def support(catalog, intent):
    if intent=='installer':
        package=catalog.status()
        if package['available']:
            return {'origin':'application_support','content':f"Aqui está meu instalador para Windows, versão {package['version']}. Clique em Baixar instalador, salve o arquivo e execute-o no outro computador conectado à mesma rede do servidor. A conexão já vem configurada; projetos, conversas e modelos continuam neste servidor.",
                    'actions':[{'kind':'download_installer','label':'Baixar instalador','url':package['download'],'version':package['version'],'sha256':package['sha256']}],
                    'sources':[],'researched_now':False}
        return {'origin':'application_support','content':package['message']+' Não vou indicar um arquivo inexistente. O administrador precisa publicar o pacote conectado nas configurações do servidor.','sources':[],'researched_now':False}
    if intent=='research_scope':
        return {'origin':'application_support','content':'Qual site ou endereço HTTPS você quer que eu pesquise? Pode enviar o link da empresa, loja ou perfil. Eu escolho a leitura de fontes ou a navegação conforme o pedido; não é preciso selecionar um modo. Só vou afirmar que pesquisei depois de obter evidências.','sources':[],'researched_now':False}
    return {'origin':'application_support','content':'O modelo de conversa local ainda não está configurado neste servidor. Abra Ferramentas → Modelos locais para conferir a configuração. Não usei um roteiro de projeto como se fosse uma resposta da IA. Posso consultar o instalador e as fontes locais disponíveis.','sources':[],'researched_now':False}
