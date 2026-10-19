class LocalAIError(Exception):
    """Erro operacional que pode ser exibido ao usuário."""

class PolicyError(LocalAIError):
    pass

class ConflictError(LocalAIError):
    pass

class NotFoundError(LocalAIError):
    pass

class AuthenticationError(LocalAIError):
    pass

class AccessDeniedError(LocalAIError):
    pass

class RateLimitError(LocalAIError):
    pass
