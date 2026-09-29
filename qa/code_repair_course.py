"""Original synthetic demonstrations. Held-out combinations never enter training."""
from itertools import product
import hashlib

def examples():
    rows=[]
    for matcher,service,port in product(['','@api','@web','@files'],['api','app','files','worker'],[3000,5000,8080,8090]):
        header='handle'+(' '+matcher if matcher else '')
        broken=f'{header} {{ reverse_proxy {service}:{port} }}'
        answer=f'{header} {{\n    reverse_proxy {service}:{port}\n}}'
        rows.append({'family':'caddy','prompt':'Corrigir Caddy:\n'+broken+'\nResposta:\n','answer':answer})
    for obj,prop,validator in product(['input','request','data','item'],['Endpoint','Url','Address','Name'],['Rules.ValidPushEndpoint','Rules.ValidText','Rules.IsAllowed']):
        expr=obj+'.'+prop
        rows.append({'family':'csharp','prompt':f'Corrigir C#:\nAnulavel: {expr}\nValidador: {validator}\nResposta:\n',
                     'answer':f'{expr} != null && {validator}({expr})'})
    target_prompts={
        'Corrigir Caddy:\nhandle @api { reverse_proxy api:8080 }\nResposta:\n',
        'Corrigir Caddy:\nhandle { reverse_proxy app:3000 }\nResposta:\n',
        'Corrigir C#:\nAnulavel: input.Endpoint\nValidador: Rules.ValidPushEndpoint\nResposta:\n'}
    splits={'train':[],'validation':[],'test':[],'project':[]}
    for row in rows:
        key=hashlib.sha256(row['prompt'].encode()).hexdigest()
        row={**row,'id':key[:16]}
        split='project' if row['prompt'] in target_prompts else 'validation' if int(key[:8],16)%17==0 else 'test' if int(key[:8],16)%19==0 else 'train'
        splits[split].append(row)
    return splits
