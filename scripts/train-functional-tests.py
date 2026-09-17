"""Continue own weights on authorized synthetic functional tests; never auto-promote."""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'qa/functional-lab'))
from course import examples
from localauthor.nn.checkpoint import load_checkpoint, save_checkpoint
from localauthor.nn.optimizer import AdamW
from localauthor.dataset import validate_dataset
from localauthor.util import write_json
import numpy as np

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--orbit-root',type=Path,required=True)
parser.add_argument('--steps',type=int,default=6000)
args=parser.parse_args()
sys.path.insert(0,str(args.orbit_root.resolve()/'scripts'))
from response_training import batch,response_loss
from code_course import examples as old_examples
home=Path(os.environ['LOCALAPPDATA'])/'LocalAuthor'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=home/'models'/('functional-tests-'+stamp);out.mkdir()
corpus=home/'corpus'/out.name;corpus.mkdir()
export=home/'exports'/out.name;export.mkdir()
previous=json.loads((home/'exports/engineering-report.json').read_text(encoding='utf-8'))
parent=Path(previous['selectedCheckpoint'])
model,_,tokenizer,_,_=load_checkpoint(parent)
held=[17,19,43,47,61,79]
train=examples([n for n in range(2,100) if n not in held])
validation=examples([17,19]);final=examples([43,47,61,79])
replay=old_examples([('train',[n for n in range(2,100) if n not in held+[41,49]])],arithmetic_expression=True)
records=[]
for split,rows in [('train',train+replay),('validation',validation),('test',final)]:
    for row in rows:
        prefix='old-' if row in replay else ''
        path=corpus/split/(prefix+row['id']+'.txt');path.parent.mkdir(exist_ok=True)
        raw=row['prompt']+row['answer']
        if len(tokenizer.encode(raw))+1>model.config.context_length:raise ValueError('Context overflow: '+row['id'])
        path.write_text(raw,encoding='utf-8',newline='\n')
        records.append({'path':path.relative_to(corpus).as_posix(),'split':split,'group':prefix+row['id'],
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'training_allowed':split!='test',
            'provenance':{'kind':'synthetic-authorized','owner':'Rafael; original references by Codex',
            'license_or_permission':'User explicitly requested teaching and complete functional verification. Parameter variants of nine known families; not general-purpose qualification.'}})
manifest=corpus/'manifest.json';write_json(manifest,{'schema_version':1,'dataset_id':out.name,'records':records})
dataset=validate_dataset(manifest)
write_json(export/'frozen-test-cases.json',final)
def evaluate(rows):
    results=[]
    for row in rows:
        ids=model.generate([tokenizer.bos_id]+tokenizer.encode(row['prompt']),max_tokens=220,temperature=.05,seed=31)
        try:source=tokenizer.decode(ids)
        except UnicodeError:source='[invalid UTF-8]'
        results.append({**row,'generated':source,'exact':source==row['answer']})
    return results
report={'state':'training','parentCheckpoint':str(parent),'parentHash':hashlib.sha256(parent.read_bytes()).hexdigest(),
    'selectedCheckpoint':str(out/'best-validation.npz'),'corpusDirectory':str(corpus),'exportDirectory':str(export),
    'manifestHash':dataset['manifest_hash'],'counts':{'train':len(train),'replay':len(replay),'validation':len(validation),'test':len(final)},
    'chatEnabled':False,'programmingQualified':False,'history':[],
    'limitations':'Raw JS snippets using documented action helpers. Parameter variants, not novel task families. Execution evaluated separately. No automatic activation.'}
write_json(export/'report.json',report)
print(json.dumps({'report':str(export/'report.json'),'counts':report['counts']}),flush=True)
optimizer=AdamW(model.parameters,lr=.0007);rng=np.random.default_rng(7219)
best=-1;streak=0
for step in range(1,args.steps+1):
    pool=replay if step%4==0 else train
    selected=[pool[int(i)] for i in rng.integers(0,len(pool),size=2)]
    x,y,mask=batch([(c['prompt'],c['answer']) for c in selected],tokenizer)
    loss=response_loss(model.forward(x),y,mask);loss.backward();optimizer.step()
    if step%100==0:print(json.dumps({'step':step,'loss':float(loss.data)}),flush=True)
    if step%500==0:
        result=evaluate(validation);score=sum(c['exact'] for c in result)
        report['history'].append({'step':step,'passed':score,'total':len(result)})
        if score>best or score==len(validation):
            best=score;report['selectedStep']=step
            save_checkpoint(out/'best-validation.npz',model,optimizer,tokenizer,rng,
                {'manifest_hash':dataset['manifest_hash'],'training_method':'own weights; response-only loss; old code rehearsal','test_used':False})
        streak=streak+1 if score==len(validation) else 0
        write_json(export/'report.json',report)
        print(json.dumps(report['history'][-1]),flush=True)
        if streak>=2:break
model,_,_,_,_=load_checkpoint(out/'best-validation.npz')
regression=json.loads((home/'exports/jira-experimental/generalization-report.json').read_text(encoding='utf-8'))['after']
report.update(state='awaiting_execution',steps=step,after=evaluate(final),regression=evaluate(regression),
    checkpointHash=hashlib.sha256((out/'best-validation.npz').read_bytes()).hexdigest())
write_json(export/'report.json',report)
print(json.dumps({'testExact':sum(c['exact'] for c in report['after']),'testTotal':len(final),
    'regressionExact':sum(c['exact'] for c in report['regression']),'regressionTotal':len(regression),'report':str(export/'report.json')}),flush=True)
