"""Exact-token working memory with a complete, read-only external archive.

The assignment and system rules are never shortened. Criteria/judge evidence do
not use this function. Excerpts and evicted turns are explicitly identified.
"""
import json

from ..errors import PolicyError


def fit_agent_context(messages, count, budget, archive):
    if (len(messages)<2 or messages[0].get('role')!='system'
            or messages[1].get('role')!='user'
            or any(not isinstance(row.get('content'),str) for row in messages)):
        raise PolicyError('Histórico do agente fora do contrato.')
    original=[dict(row) for row in messages]

    count_calls=0
    def tokens(rows):
        nonlocal count_calls
        # The inference bridge accepts bounded frames. Do not close an otherwise
        # healthy engine by submitting a request larger than its IPC contract.
        if len(json.dumps(rows,ensure_ascii=False).encode())>110_000:return None
        count_calls+=1
        if count_calls>32:raise PolicyError('context_length_exceeded: limite de contagem; originais preservados em '+archive)
        return count(rows)

    before=tokens(original)
    if before is not None and before<=budget:
        return original,{'before_tokens':before,'after_tokens':before,'archived_messages':0,'excerpts':[]}
    initial=original[:2];remaining=[(index,dict(row)) for index,row in enumerate(original[2:],2)]
    omitted=[];excerpts=[]
    while True:
        notice={'role':'user','content':(
            'WORKING MEMORY NOTICE: full earlier messages and full tool outputs are preserved read-only in '
            +archive+'. The original assignment and system rules are unchanged. '
            +'Archived message indexes: '+str(omitted)+'. Excerpted indexes: '+str(excerpts)+'. '
            +'Output files remain on disk. Revisit evidence before making claims. To inspect a range, use bash with Python: '
            +'json.load(open("'+archive+'"))[INDEX]["content"][START:END]. Read small ranges; do not read the entire archive at once.')}
        candidate=[*initial,notice,*[row for _,row in remaining]]
        size=tokens(candidate)
        if size is not None and size<=budget:
            return candidate,{'before_tokens':before,'after_tokens':size,'archived_messages':len(omitted),'excerpts':excerpts}
        # First page large tool results, retaining their beginning and ending.
        available=[(len(row['content']),position,index) for position,(index,row) in enumerate(remaining)
                   if row['role']=='user' and row['content'].startswith('Tool result ') and len(row['content'])>900]
        if available:
            length,position,index=max(available)
            source=original[index]['content'];limit=max(600,length//2)
            if index not in excerpts:excerpts.append(index)
            remaining[position][1]['content']=(source[:limit//2]+'\n[EXPLICIT EXCERPT; full message '+str(index)
                +' at '+archive+'; '+str(len(source))+' characters]\n'+source[-limit//4:])
            continue
        # Evict complete assistant/result pairs only; the most recent pair stays.
        if len(remaining)>2 and remaining[0][1]['role']=='assistant' and remaining[1][1]['role']=='user':
            omitted.extend([remaining[0][0],remaining[1][0]]);del remaining[:2]
            continue
        raise PolicyError('context_length_exceeded: pedido/regras e última ação não cabem; originais preservados em '+archive)
