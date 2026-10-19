# LocalAuthor proposal reviewed and tested in verified offline sandbox.
def can_access_project(role, action):
    # Verificação estrita de tipo antes de qualquer comparação
    if type(role) is not str or type(action) is not str:
        return False

    valid_roles = ['owner', 'editor', 'reader']
    valid_actions = ['read', 'write', 'share']

    if role not in valid_roles or action not in valid_actions:
        return False

    if role == 'owner':
        return True
    elif role == 'editor':
        return action in ['read', 'write']
    elif role == 'reader':
        return action == 'read'

    return False
