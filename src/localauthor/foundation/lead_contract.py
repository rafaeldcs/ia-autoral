"""Locally drafted contract, repaired by the local model and reviewed by the supervisor."""
from ..errors import PolicyError

FITS = ("candidate", "needs_information", "not_fit", "do_not_contact")

def validate_proposal(payload, fact_count, message_count, question_count):
    if not isinstance(payload, dict):
        raise PolicyError("payload deve ser um dicionário")
    if set(payload.keys()) != {"fit", "fact_indices", "message_indices", "question_indices"}:
        raise PolicyError("payload deve conter exatamente as chaves: fit, fact_indices, message_indices, question_indices")
    if type(fact_count) is not int or type(message_count) is not int or type(question_count) is not int:
        raise PolicyError("fact_count, message_count e question_count devem ser inteiros")
    if not (0 <= fact_count <= 20) or not (0 <= message_count <= 20) or not (0 <= question_count <= 20):
        raise PolicyError("contagens devem estar entre 0 e 20")
    if not isinstance(payload["fit"], str) or payload["fit"] not in FITS:
        raise PolicyError("fit deve ser uma string válida da constante FITS")
    if not isinstance(payload["fact_indices"], list) or not isinstance(payload["message_indices"], list) or not isinstance(payload["question_indices"], list):
        raise PolicyError("todos os índices devem ser listas")
    if len(payload["message_indices"]) == 0:
        raise PolicyError("message_indices não pode estar vazio")
    if payload["fit"] == "candidate" and len(payload["fact_indices"]) == 0:
        raise PolicyError("candidate exige fact_indices não vazio")

    def validate_indices(indices, count, name):
        if not isinstance(indices, list):
            raise PolicyError(f"{name} deve ser uma lista")
        if len(indices) > 3:
            raise PolicyError(f"{name} deve ter no máximo 3 itens")
        for i, x in enumerate(indices):
            if type(x) is not int:
                raise PolicyError(f"Elemento {i} de {name} não é inteiro")
            if not (1 <= x <= count):
                raise PolicyError(f"Elemento {i} de {name} fora da faixa 1..{count}")
        if len(indices) != len(set(indices)):
            raise PolicyError(f"{name} contém duplicatas")
        return list(indices)

    fact_indices = validate_indices(payload["fact_indices"], fact_count, "fact_indices")
    message_indices = validate_indices(payload["message_indices"], message_count, "message_indices")
    question_indices = validate_indices(payload["question_indices"], question_count, "question_indices")

    return {
        "fit": payload["fit"],
        "fact_indices": fact_indices,
        "message_indices": message_indices,
        "question_indices": question_indices
    }
