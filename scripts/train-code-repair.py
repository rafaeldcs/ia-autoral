"""Train an original generative repair specialist; never auto-qualify or deploy."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'qa')]
import numpy as np
from code_repair_course import examples
from localauthor.nn.transformer import Transformer,ModelConfig
from localauthor.nn.tokenizer import BPETokenizer
from localauthor.nn.optimizer import AdamW
from localauthor.nn.checkpoint import save_checkpoint,load_checkpoint

def batch(rows,tokenizer):
    sequences=[];starts=[]
    for row in rows:
        prefix=[256]+tokenizer.encode(row['prompt']);sequences.append(prefix+tokenizer.encode(row['answer'])+[257]);starts.append(len(prefix)-1)
    length=max(len(s)-1 for s in sequences)
    x=np.full((len(rows),length),257,dtype=np.int64);y=x.copy();mask=np.zeros_like(x,dtype=float)
    for i,(seq,start) in enumerate(zip(sequences,starts)):
        n=len(seq)-1;x[i,:n]=seq[:-1];y[i,:n]=seq[1:];mask[i,start:n]=1
    return x,y,mask

def response_loss(logits,targets,mask):
    flat=logits.data.reshape(-1,logits.data.shape[-1]);centered=flat-flat.max(axis=1,keepdims=True)
    ex=np.exp(centered);prob=ex/ex.sum(axis=1,keepdims=True);rows=np.arange(targets.size);weights=mask.ravel()/mask.sum()
    loss=float(((-centered[rows,targets.ravel()]+np.log(ex.sum(axis=1)))*weights).sum())
    def backward(g):
        grad=prob.copy();grad[rows,targets.ravel()]-=1
        logits._add_grad((grad*weights[:,None]).reshape(logits.data.shape)*float(g))
    return logits._result(loss,(logits,),backward)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--steps',type=int,default=6000);parser.add_argument('--resume',type=Path)
    args=parser.parse_args();out=args.output.resolve()
    if out.is_relative_to(ROOT):raise ValueError('Weights/corpus stay outside Git')
    if (out/'report.json').exists() or (out/'best-validation.npz').exists():raise ValueError('Use a new output folder; preserve previous checkpoints and evaluation receipts')
    if not 500<=args.steps<=50000:raise ValueError('Use 500 to 50000 steps for this bounded experiment')
    out.mkdir(parents=True,exist_ok=True)
    splits=examples();raw=json.dumps(splits,sort_keys=True).encode();digest=hashlib.sha256(raw).hexdigest()
    (out/'frozen-course.json').write_bytes(raw)
    provenance={'kind':'original-synthetic-authorized','permission':'User requested teaching and qualification, 2026-09-29','corpusHash':digest,'test_used_for_training':False,'scope':'two known repair families; held-out combinations, not general programming'}
    if args.resume:
        model,opt,tokenizer,rng,meta=load_checkpoint(args.resume)
        if meta['provenance'].get('corpusHash')!=digest:raise ValueError('Cannot resume with a changed evaluation split')
    else:
        tokenizer=BPETokenizer.train([r['prompt']+r['answer'] for r in splits['train']],vocab_size=384)
        model=Transformer(ModelConfig(vocab_size=tokenizer.vocab_size,context_length=192,dimension=64,heads=4,layers=2,expansion=2,seed=6301))
        opt=AdamW(model.parameters,lr=.001);rng=np.random.default_rng(1791)
    def evaluate(rows):
        results=[]
        for row in rows:
            ids=model.generate([256]+tokenizer.encode(row['prompt']),max_tokens=100,temperature=.05,seed=31)
            try:generated=tokenizer.decode(ids)
            except UnicodeError:generated='[invalid UTF-8]'
            results.append({**row,'generated':generated,'exact':generated==row['answer']})
        return results
    if max(batch([r],tokenizer)[0].shape[1] for r in splits['train'])>192:raise ValueError('Context too small')
    report={'state':'training','scope':'caddy-block-and-csharp-null-guard-v1','counts':{k:len(v) for k,v in splits.items()},'parameters':model.parameter_count,'provenance':provenance,'history':[],'qualified':False}
    (out/'manifest.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps({'parameters':model.parameter_count,'counts':report['counts']}),flush=True)
    best=-1;streak=0;started=time.monotonic()
    for step in range(1,args.steps+1):
        selected=[splits['train'][int(i)] for i in rng.integers(0,len(splits['train']),size=4)]
        x,y,mask=batch(selected,tokenizer);loss=response_loss(model.forward(x),y,mask);loss.backward();opt.step()
        if step%100==0:print(json.dumps({'step':step,'loss':float(loss.data),'seconds':round(time.monotonic()-started)}),flush=True)
        if step%500==0:
            result=evaluate(splits['validation']);score=sum(r['exact'] for r in result)
            report['history'].append({'step':step,'passed':score,'total':len(result)})
            if score>=best:
                best=score;save_checkpoint(out/'best-validation.npz',model,opt,tokenizer,rng,provenance);report['selectedStep']=step
            streak=streak+1 if score==len(result) else 0
            (out/'validation-latest.json').write_text(json.dumps(result,indent=2))
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['history'][-1]),flush=True)
            if streak>=2:break
    model,_,tokenizer,_,_=load_checkpoint(out/'best-validation.npz')
    report.update(state='awaiting_external_execution',checkpointHash=hashlib.sha256((out/'best-validation.npz').read_bytes()).hexdigest(),test=evaluate(splits['test']),project=evaluate(splits['project']))
    report['testPassed']=sum(r['exact'] for r in report['test']);report['projectPassed']=sum(r['exact'] for r in report['project'])
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ('state','testPassed','projectPassed')}),flush=True)

if __name__=='__main__':main()
