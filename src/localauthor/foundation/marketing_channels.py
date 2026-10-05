"""Narrow Meta organic connectors; credentials encrypted with Windows-user DPAPI.

No ads, automatic DMs, email, retries, broad Graph paths or AI-selected accounts.
Unknown delivery outcomes stay unknown until an operator reconciles them.
"""
from __future__ import annotations
import base64
import ctypes
import http.client
import json
import os
import re
import ssl
import uuid
from urllib.parse import urlencode, urlsplit

from ..errors import ConflictError, PolicyError
from ..util import utcnow
from .marketing_workflow import fingerprint, text


class WindowsVault:
    def _crypt(self, raw, decrypt=False):
        if os.name!='nt':raise PolicyError('Conexões reais usam DPAPI do usuário Windows do servidor; não há fallback em texto.')
        if not isinstance(raw,bytes) or not 1<=len(raw)<=16000:raise PolicyError('Credencial inválida.')
        from ctypes import wintypes
        class Blob(ctypes.Structure):
            _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
        buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
        lib=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        if decrypt:
            operation=lib.CryptUnprotectData
            operation.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
            ok=operation(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out))
        else:
            operation=lib.CryptProtectData
            operation.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
            ok=operation(ctypes.byref(source),'LocalAuthor marketing',None,None,None,1,ctypes.byref(out))
        if not ok:raise PolicyError('DPAPI não conseguiu proteger/abrir a credencial deste usuário Windows.')
        try:return ctypes.string_at(out.data,out.size)
        finally:
            ctypes.memset(out.data,0,out.size)
            kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
            kernel.LocalFree(out.data)
    def seal(self, token):return base64.b64encode(self._crypt(token.encode('utf-8'))).decode('ascii')
    def open(self, sealed):return self._crypt(base64.b64decode(sealed,validate=True),True).decode('utf-8')


class MetaTransport:
    def __init__(self, settings):self.settings=settings
    def call(self, version, account, edge, method, params, token):
        if self.settings.offline:raise PolicyError('Rede desativada; nenhuma chamada Meta foi feita.')
        if not re.fullmatch(r'v[1-9][0-9]{0,2}\.0',version) or not re.fullmatch(r'[0-9]{1,40}',account) or edge not in {'','feed','media','media_publish'} or method not in {'GET','POST'}:
            raise PolicyError('Operação Meta não permitida.')
        if not isinstance(token,str) or not 10<=len(token)<=8000 or re.search(r'\s',token):raise PolicyError('Token de canal inválido.')
        raw=urlencode(params).encode('utf-8')
        if len(raw)>12000:raise PolicyError('Requisição de canal muito longa.')
        conn=http.client.HTTPSConnection('graph.facebook.com',timeout=20,context=ssl.create_default_context())
        path=f'/{version}/{account}'+('/'+edge if edge else '')
        if method=='GET':path+='?'+raw.decode('ascii')
        try:
            conn.request(method,path,body=raw if method=='POST' else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'})
            response=conn.getresponse();body=response.read(2_000_001)
            if len(body)>2_000_000:raise PolicyError('Resposta Meta excessiva.')
            data=json.loads(body)
            if not 200<=response.status<300 or not isinstance(data,dict) or 'error' in data:
                raise PolicyError(f'Meta recusou a operação (HTTP{response.status}). Confira permissão, validade do token e versão da API no painel Meta.')
            return data
        except (OSError,ValueError,http.client.HTTPException) as exc:
            raise PolicyError('Não foi possível confirmar a resposta da Meta; nenhuma repetição automática.') from None
        finally:conn.close()


class MarketingChannels:
    def __init__(self, store, workflow, settings, *, vault=None, transport=None):
        self.store,self.workflow,self.settings=store,workflow,settings
        self.vault=vault or WindowsVault();self.transport=transport or MetaTransport(settings)
        with store.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS marketing_channels(project_id TEXT NOT NULL REFERENCES projects(id), channel TEXT NOT NULL, account TEXT NOT NULL, api_version TEXT NOT NULL, sealed_token TEXT NOT NULL, verified_at TEXT NOT NULL, PRIMARY KEY(project_id,channel));
            CREATE TABLE IF NOT EXISTS marketing_deliveries(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, campaign_id TEXT NOT NULL, piece_id TEXT NOT NULL, payload_hash TEXT NOT NULL UNIQUE, state TEXT NOT NULL, remote_id TEXT, created_at TEXT NOT NULL);
            ''')

    def list(self, project):
        self.store.project(project)
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT channel,account,api_version,verified_at FROM marketing_channels WHERE project_id=?',(project,))]

    def connect(self, project, channel, account, version, token):
        self.store.project(project)
        if channel not in {'facebook','instagram'} or not isinstance(account,str) or not re.fullmatch(r'[0-9]{1,40}',account) or not isinstance(version,str) or not re.fullmatch(r'v[1-9][0-9]{0,2}\.0',version):
            raise PolicyError('Selecione Facebook Page ou Instagram profissional com ID e versão explícitos.')
        if not isinstance(token,str) or not 10<=len(token)<=8000 or re.search(r'\s',token):raise PolicyError('Token de canal inválido.')
        sealed=self.vault.seal(token)
        fields='id,name,can_post' if channel=='facebook' else 'id,username'
        data=self.transport.call(version,account,'','GET',{'fields':fields},token)
        if data.get('id')!=account:raise PolicyError('O token não confirmou o ID da conta selecionada.')
        if channel=='facebook' and data.get('can_post') is not True:
            raise PolicyError('A Meta não confirmou uma Page com capacidade de publicar para este token.')
        if channel=='instagram' and not isinstance(data.get('username'),str):
            raise PolicyError('A Meta não confirmou a identidade Instagram deste ID.')
        with self.store.connect() as db:
            db.execute('INSERT INTO marketing_channels VALUES(?,?,?,?,?,?) ON CONFLICT(project_id,channel) DO UPDATE SET account=excluded.account,api_version=excluded.api_version,sealed_token=excluded.sealed_token,verified_at=excluded.verified_at',(project,channel,account,version,sealed,utcnow()))
        return {'channel':channel,'account':account,'identity_verified':True,'publish_permission_verified':False,
            'notice':'Identidade confirmada. Permissão de publicação e aprovação do aplicativo dependem da Meta; só uma publicação autorizada pode confirmar entrega.'}

    def disconnect(self, project, channel):
        self.store.project(project)
        with self.store.connect() as db:db.execute('DELETE FROM marketing_channels WHERE project_id=? AND channel=?',(project,channel))
        return {'disconnected':True}

    def _connection(self, project, channel):
        with self.store.connect() as db:row=db.execute('SELECT * FROM marketing_channels WHERE project_id=? AND channel=?',(project,channel)).fetchone()
        if not row:raise PolicyError('Conecte a conta deste canal no projeto antes de preparar envio.')
        return dict(row)

    def preview(self, project, campaign, piece, media_url=None):
        exported=self.workflow.export(project,campaign)
        asset=next((a for a in exported['assets'] if a['id']==piece),None)
        if not asset or asset['channel'] not in {'facebook','instagram'}:raise PolicyError('Este conector envia texto de Page ou imagem de Instagram; outros canais usam exportação manual.')
        connection=self._connection(project,asset['channel'])
        if asset['channel']=='instagram':
            parsed=urlsplit(text(media_url,'URL pública do JPEG'))
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.query or parsed.fragment or not parsed.path.lower().endswith(('.jpg','.jpeg')):
                raise PolicyError('Instagram requer URL pública HTTPS de um JPEG real aprovado, sem query ou credenciais; arquivos locais não são acessíveis à Meta.')
            from ..research import validate_url
            validate_url(media_url,[parsed.hostname])
            if parsed.hostname.endswith(('.local','.internal')):raise PolicyError('A Meta não acessa uma mídia da rede local.')
        elif media_url is not None:raise PolicyError('Esta versão de Facebook publica texto e link; mídia não é enviada.')
        payload={'project_id':project,'campaign_id':campaign,'piece_id':piece,'channel':asset['channel'],'account':connection['account'],
            'api_version':connection['api_version'],'caption':asset['caption'],'link':asset['tracking_url'],'media_url':media_url,
            'draft_sha256':self.workflow.get(project,campaign)['approval']['draft_sha256']}
        return {'payload':payload,'payload_hash':fingerprint(payload),'published':False,'notice':'Confira conta, texto, link e imagem. Publicar é uma ação externa separada. Não envia anúncios ou mensagens privadas.'}

    def publish(self, project, campaign, piece, payload_hash, authorized, media_url=None):
        if authorized is not True:raise PolicyError('A publicação precisa de autorização explícita para esta peça e conta.')
        preview=self.preview(project,campaign,piece,media_url);payload=preview['payload']
        if payload_hash!=preview['payload_hash']:raise ConflictError('Peça, conta ou destino mudou; confira a nova prévia antes de publicar.')
        connection=self._connection(project,payload['channel'])
        if connection['account']!=payload['account'] or connection['api_version']!=payload['api_version']:
            raise ConflictError('A conexão mudou; confirme a nova prévia.')
        if self.settings.offline:raise PolicyError('Rede desativada; envio bloqueado.')
        token=self.vault.open(connection['sealed_token'])
        ident=uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM marketing_deliveries WHERE project_id=? AND campaign_id=? AND piece_id=?',(project,campaign,piece)).fetchone():
                raise ConflictError('Esta entrega já foi solicitada. Confira o recibo; não repetir automaticamente.')
            db.execute('INSERT INTO marketing_deliveries VALUES(?,?,?,?,?,\'sending\',NULL,?)',(ident,project,campaign,piece,payload_hash,utcnow()))
        try:
            if payload['channel']=='facebook':
                response=self.transport.call(connection['api_version'],connection['account'],'feed','POST',{'message':payload['caption'],'link':payload['link']},token)
            else:
                container=self.transport.call(connection['api_version'],connection['account'],'media','POST',{'image_url':media_url,'caption':payload['caption']+'\n'+payload['link']},token)
                container_id=container.get('id')
                if not isinstance(container_id,str) or not re.fullmatch(r'\d{1,40}',container_id):raise PolicyError('Meta não confirmou o container de mídia.')
                response=self.transport.call(connection['api_version'],connection['account'],'media_publish','POST',{'creation_id':container_id},token)
            remote_id=response.get('id')
            if not isinstance(remote_id,str) or not re.fullmatch(r'[0-9_]{1,100}',remote_id):raise PolicyError('Meta não confirmou um ID de publicação.')
            with self.store.connect() as db:db.execute('UPDATE marketing_deliveries SET state=\'confirmed\',remote_id=? WHERE id=?',(remote_id,ident))
        except Exception:
            with self.store.connect() as db:db.execute('UPDATE marketing_deliveries SET state=\'unknown\' WHERE id=?',(ident,))
            raise PolicyError('A entrega não foi confirmada. Confira na conta antes de qualquer nova tentativa; o recibo está preservado.') from None
        return {'delivery_id':ident,'state':'confirmed','remote_id':remote_id,'published':True,'verification':'Meta returned publication id; reach/conversions not measured'}

    def deliveries(self, project):
        self.store.project(project)
        with self.store.connect() as db:return [dict(r) for r in db.execute('SELECT id,campaign_id,piece_id,payload_hash,state,remote_id,created_at FROM marketing_deliveries WHERE project_id=? ORDER BY created_at DESC',(project,))]
