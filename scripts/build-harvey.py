"""Build optional Harvey infrastructure from reviewed Git objects, preserving LF."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from localauthor.harvey.contracts import REVISION
from localauthor.harvey.runner import git,verify_checkout


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--upstream',type=Path,required=True)
    parser.add_argument('--context',type=Path,required=True);parser.add_argument('--tag',default='localauthor-harvey-local:97810fac')
    args=parser.parse_args();verify_checkout(args.upstream)
    if not re.fullmatch(r'[a-z0-9._/-]+:[a-z0-9._-]+',args.tag):parser.error('Invalid local image tag')
    args.context.mkdir(parents=True,exist_ok=False)
    paths=git(args.upstream,'ls-tree','-r','--name-only',REVISION,'lab_core').decode().splitlines()
    for name in paths+['LICENSE']:
        target=args.context/'core'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(git(args.upstream,'show',REVISION+':'+name))
    for name in ['Dockerfile','install_pandoc.sh','parsers/parse_doc.py']:
        target=args.context/'base'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(git(args.upstream,'show',REVISION+':lab_core/sandbox/'+name))
    base='localauthor-harvey-base:'+REVISION[:8]
    subprocess.run(['docker','build','--pull=false','-t',base,str(args.context/'base')],check=True)
    dockerfile=('FROM '+base+'\nCOPY core/lab_core /opt/harvey-core/lab_core\nCOPY core/LICENSE /opt/harvey-core/LICENSE\n'
                'RUN pip install --no-cache-dir anthropic\nENV PYTHONPATH=/opt/harvey-core\n')
    (args.context/'Dockerfile').write_text(dockerfile,encoding='utf-8',newline='\n')
    subprocess.run(['docker','build','--pull=false','-t',args.tag,str(args.context)],check=True)
    image=subprocess.check_output(['docker','image','inspect',args.tag,'--format','{{.Id}}']).decode().strip()
    result={'image_id':image,'tag':args.tag,'upstream_revision':REVISION,'source':'https://github.com/harveyai/harvey-labs','foundation_model_weights_downloaded':False}
    (args.context/'image.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
