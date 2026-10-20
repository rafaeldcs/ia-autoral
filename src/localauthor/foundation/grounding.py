"""Shared instruction for factual commercial offers; not training or permission."""
import re

FEATURE_FAMILIES = {
    'estoque':r'estoqu\w*', 'automação':r'automat\w*',
    'integrações':r'integra[çc][aã]o|integrad\w*|integra[çc][õo]es',
    'pagamentos':r'pagament\w*', 'logística':r'log[íi]stic\w*',
    'solução completa':r'solu[çc][aã]o\s+completa|controle\s+total',
    'interface':r'interface\w*', 'tempo real':r'tempo\s+real',
    'garantia':r'garant\w*', 'sem risco':r'sem\s+riscos?',
    'escala':r'escalar|escalabilidade',
}


def unmentioned_features(content, evidence):
    """Conservative lexical absence check, NOT a proof of semantic support.

    Presence in evidence does not certify truth (it may be negated or quoted).
    Source review remains necessary. This guard only rejects known feature
    families that are entirely absent from the provided material.
    """
    return [name for name,pattern in FEATURE_FAMILIES.items()
            if re.search(pattern,content,re.I) and not re.search(pattern,evidence,re.I)]

COMMERCIAL_GROUNDING = (
    'Ao escrever publicidade, separe fatos confirmados de condições comerciais desconhecidas. '
    'Um convite para solicitar demonstração NÃO autoriza chamá-la de gratuita, sem custo ou sem compromisso. '
    'Só use gratuidade, desconto, prazo, preço, garantia ou resultado quando essa condição estiver '
    'explicitamente confirmada em uma fonte do produto fornecida para o pedido atual. '
    'Ausência de preço não significa preço zero. Não deduza ofertas de concorrentes ou de convenções de marketing. '
    'Antes de entregar, confira cada afirmação e cada qualificador do CTA contra os fatos; '
    'retire do rascunho condições desconhecidas ou pergunte ao usuário quando forem essenciais. '
    'Não amplie dois recursos confirmados para uma solução completa de todas as operações. '
    'Descreva a finalidade dos recursos, sem afirmar eficiência ou crescimento comprovados quando não foram medidos. '
    'Quando houver poucos fatos, escreva um anúncio curto; não preencha espaço com funcionalidades típicas do setor. '
    'Não crie links com # nem destinos fictícios. Sem endereço confirmado, escreva o CTA como texto. '
    'Se o contexto confirmar uma oferta gratuita, preserve essa informação: não proíba ofertas verdadeiras.'
)
