"""Small same-origin identity API; sessions are HttpOnly cookies, never JSON."""
from http.cookies import SimpleCookie, CookieError
import re

from .errors import AuthenticationError, AccessDeniedError, PolicyError
from .identity import COOKIE_NAME, SESSION_SECONDS


def cookie_token(headers):
    raw=headers.get('Cookie','')
    if len(raw)>4096 or len(re.findall(r'(?:^|;)\s*'+COOKIE_NAME+r'=',raw))>1:
        raise AuthenticationError('Sessão inválida. Entre novamente.')
    try:
        cookie=SimpleCookie();cookie.load(raw)
        return cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else None
    except CookieError as exc:raise AuthenticationError('Sessão inválida. Entre novamente.') from exc


def transport(headers):
    gateway=headers.get('X-LocalAuthor-Gateway','')
    if gateway not in ('','server','lan'):raise AccessDeniedError('Origem do dispositivo inválida.')
    device=headers.get('X-LocalAuthor-Device','local')
    if gateway and not re.fullmatch('[0-9a-f]{32}',device):raise AccessDeniedError('Dispositivo inválido.')
    return gateway,device


def session_cookie(token, headers):
    gateway=headers.get('X-LocalAuthor-Gateway','')
    return f'{COOKIE_NAME}={token or ""}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS if token else 0}'+('; Secure' if gateway else '')


def require_user(app, headers):
    user=app.identity.current(cookie_token(headers))
    if user is None:raise AuthenticationError('Entre no seu perfil para continuar.')
    expected=headers.get('X-LocalAuthor-Profile')
    if expected is not None and expected!=user['id']:
        raise AuthenticationError('O perfil mudou em outra janela. Recarregue para continuar.')
    return user


def route(app, method, path, q, body, headers):
    if not path.startswith('/api/identity/') and path!='/api/project-members':return False,None,None
    identity=app.identity;gateway,device=transport(headers)
    token=cookie_token(headers)
    def fields(required,optional=()):
        if not set(required)<=set(body) or set(body)-set(required)-set(optional):raise PolicyError('Campos de perfil inválidos.')
    if method=='GET' and path=='/api/identity/status':
        user=identity.current(token)
        return True,{'configured':identity.enabled,'can_setup':gateway!='lan',
                     'user':identity.public_user(user) if user else None},None
    if method=='POST' and path=='/api/identity/setup':
        fields({'username','name','password'})
        user,session=identity.bootstrap(body['username'],body['name'],body['password'],local=gateway!='lan')
        return True,{'user':identity.public_user(user)},session_cookie(session,headers)
    if method=='POST' and path=='/api/identity/login':
        fields({'username','password'})
        user,session=identity.login(body['username'],body['password'],gateway+':'+device)
        identity.logout(token)
        return True,{'user':identity.public_user(user)},session_cookie(session,headers)
    if method=='POST' and path=='/api/identity/logout':
        fields(set());identity.logout(token)
        return True,{'logged_out':True},session_cookie(None,headers)
    actor=require_user(app,headers)
    if method=='GET' and path=='/api/identity/directory':return True,identity.users(actor,directory=True),None
    if method=='GET' and path=='/api/identity/users':return True,identity.users(actor),None
    if method=='POST' and path=='/api/identity/users':
        fields({'username','name','password','role'})
        return True,identity.create_user(actor,body['username'],body['name'],body['password'],body['role']),None
    if method=='POST' and path=='/api/identity/users/update':
        fields({'id','name','role','active'},{'password'})
        return True,identity.update_user(actor,body['id'],body['name'],body['role'],body['active'],body.get('password')),None
    if method=='POST' and path=='/api/identity/password':
        fields({'current_password','new_password'})
        result=identity.change_password(actor,body['current_password'],body['new_password'])
        return True,result,session_cookie(None,headers)
    if method=='GET' and path=='/api/project-members':return True,identity.members(actor,q['project_id']),None
    if method=='POST' and path=='/api/project-members':
        fields({'project_id','user_id','role'})
        return True,identity.share(actor,body['project_id'],body['user_id'],body['role']),None
    from .errors import NotFoundError
    raise NotFoundError('Rota de perfil não encontrada.')
