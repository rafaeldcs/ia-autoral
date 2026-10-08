"""Local arithmetic on supplied counts; no inference, publication or training."""
from decimal import Decimal, ROUND_HALF_UP
from ..errors import PolicyError

FIELDS = {
    'campaign': {'impressions', 'clicks', 'leads', 'new_clients', 'spend_cents'},
    'funnel': {'registrations', 'started', 'completed'},
    'cash': {'opening_cents', 'incoming_cents', 'outgoing_cents'}
}

def _validate(payload):
    if not isinstance(payload, dict):
        raise PolicyError("Payload não é um dicionário")
    keys = set(payload.keys())
    if keys != {'kind', 'data'}:
        raise PolicyError("Chaves inválidas")
    kind = payload['kind']
    if not isinstance(kind, str):
        raise PolicyError("kind não é uma string")
    if kind not in FIELDS:
        raise PolicyError(f"Tipo '{kind}' não reconhecido")
    data = payload['data']
    if not isinstance(data, dict):
        raise PolicyError("Dados não são um dicionário")
    if set(data.keys()) != FIELDS[kind]:
        raise PolicyError("Campos inválidos")
    for k, v in data.items():
        if not (type(v) is int) or v < 0 or v > 10**12:
            raise PolicyError(f"Valor {k} inválido")
    if kind == 'campaign':
        if not (data['new_clients'] <= data['leads'] <= data['clicks'] <= data['impressions']):
            raise PolicyError("Ordem de métricas inválida")
    elif kind == 'funnel':
        if not (data['completed'] <= data['started'] <= data['registrations']):
            raise PolicyError("Ordem de etapas inválida")
    return kind, data


def _ratio(numerator, denominator, scale=1):
    if denominator == 0:
        return None
    valor = Decimal(numerator) * Decimal(scale) / Decimal(denominator)
    return format(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")

def _campaign(data):
    return {
        "ctr_percent": _ratio(data['clicks'], data['impressions'], 100),
        "cpl_brl": _ratio(data['spend_cents'], data['leads'], Decimal("0.01")),
        "media_per_client_brl": _ratio(data['spend_cents'], data['new_clients'], Decimal("0.01"))
    }

def _funnel(data):
    return {
        'start_percent': _ratio(data['started'], data['registrations'], 100),
        'completion_started_percent': _ratio(data['completed'], data['started'], 100),
        'activation_percent': _ratio(data['completed'], data['registrations'], 100),
        'not_started': data['registrations'] - data['started'],
        'started_not_completed': data['started'] - data['completed'],
        'not_completed': data['registrations'] - data['completed']
    }

def _cash(data):
    balance = data['opening_cents'] + data['incoming_cents'] - data['outgoing_cents']
    return {"balance_cents": balance, "balance_brl": _ratio(balance, 100)}

def analyze_business_metrics(payload):
    kind, data = _validate(payload)
    if kind == "campaign":
        metrics = _campaign(data)
        notice = "campanha mídia/cliente não CAC completo nem ROI ou prova causal"
    elif kind == "funnel":
        metrics = _funnel(data)
        notice = "funil coorte/período devem ser verificados"
    else:
        metrics = _cash(data)
        notice = "caixa saldo não lucro"
    return {
        "kind": kind,
        "inputs": data.copy(),
        "metrics": metrics,
        "data_origin": "user_supplied_unverified",
        "notice": notice,
        "published": False,
        "weights_trained": False
    }
