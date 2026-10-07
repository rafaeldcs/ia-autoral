"""Deterministic campaign arithmetic. Supplied numbers are not verified real data."""
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from ..errors import PolicyError


def compare_campaigns(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise PolicyError("Informe de 1 a 20 campanhas.")
    results, rates, names = [], [], set()
    def ratio(numerator, denominator, scale=1):
        if not denominator: return None
        return format((Decimal(numerator) * scale / Decimal(denominator)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 'f')
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'impressions', 'clicks', 'conversions', 'spend_cents'}:
            raise PolicyError("Campos de campanha inválidos.")
        name = row['name']
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or name.strip() in names:
            raise PolicyError("Nomes de campanha devem ser únicos, de 1 a 100 caracteres.")
        name = name.strip(); names.add(name)
        values = [row[k] for k in ('impressions', 'clicks', 'conversions', 'spend_cents')]
        if any(type(v) is not int or not 0 <= v <= 10**12 for v in values):
            raise PolicyError("Use contagens e centavos inteiros, não negativos, até um trilhão.")
        impressions, clicks, conversions, spend = values
        if clicks > impressions or conversions > clicks:
            raise PolicyError("Este relatório usa conversões por clique: conversões ≤ cliques ≤ impressões.")
        results.append({'name': name, 'ctr_percent': ratio(clicks, impressions, 100),
            'click_conversion_percent': ratio(conversions, clicks, 100),
            'cpc_brl': ratio(spend, clicks, Decimal('0.01')),
            'cpa_brl': ratio(spend, conversions, Decimal('0.01'))})
        rates.append(Fraction(clicks, impressions) if impressions else None)
    eligible = [r for r in rates if r is not None]
    best = max(eligible) if eligible else None
    return {'campaigns': results, 'best_ctr': [r['name'] for r, rate in zip(results, rates) if best is not None and rate == best],
        'data_origin': 'user_supplied_unverified', 'published': False, 'real_spend_verified': False,
        'notice': 'Cálculos locais sobre dados fornecidos. CTR maior não comprova mais vendas. Sem denominador, a métrica fica indisponível.'}
