class LocalAIError(Exception):
    """Erro operacional que pode ser exibido ao usuário."""

class PolicyError(LocalAIError):
    pass

class ConflictError(LocalAIError):
    pass

class NotFoundError(LocalAIError):
    pass
