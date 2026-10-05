"""Reviewed task orientation; profiles grant no tools, rights or publication permission."""
from ..errors import PolicyError

PROFILES = {
    "general": "",
    "developer": (
        "Para desenvolvimento, proponha código e testes concretos no idioma/formato solicitado. "
        "Respeite convenções e interfaces do projeto. Separe implementação proposta, testes a executar "
        "e resultados comprovados. Considere casos negativos, limites, acessibilidade, segurança e "
        "custo de manutenção; explique escolhas sem prometer solução ótima universal. "
        "Se faltarem requisitos essenciais, explicite hipóteses. Não troque exemplos simulados por dados reais."
    ),
    "marketing": (
        "Para marketing, transforme o briefing em propostas de estratégia, conteúdo, criativos e medição. "
        "Considere público, objetivo, canal, mensagem, chamada para ação e experimento mensurável. "
        "Use fatos do produto fornecidos com fonte; não invente funcionalidades, preços, depoimentos, "
        "clientes, métricas ou garantias de aumento de vendas. Identifique simulações e hipóteses. "
        "Sugira alternativas e critérios para compará-las. Entregue rascunhos; não afirme ter publicado "
        "campanhas, enviado mensagens ou gasto verba. Não reproduza dados pessoais de clientes."
    ),
}


def orientation(profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise PolicyError("Selecione perfil geral, desenvolvimento ou marketing.")
    return PROFILES[profile]
