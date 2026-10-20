import copy
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from localauthor.errors import PolicyError
from localauthor.harvey.contracts import content_hash,parse_action,receive_record,relative_file,sign_frame,validate_task,verify_frame,verify_sandbox
from localauthor.harvey.runner import adapter_hash,write_report


class HarveyContractsTests(unittest.TestCase):
    def test_resume_freeze_includes_inference_sources_and_rpc_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bridge=root/'src/localauthor/foundation/gguf_bridge.py'
            bridge.parent.mkdir(parents=True);bridge.write_text('original bridge')
            rpc=root/'scripts/foundation-gguf-rpc.py';rpc.parent.mkdir();rpc.write_text('original RPC')
            with patch('localauthor.harvey.runner.ROOT',root):
                first=adapter_hash();self.assertEqual(first,adapter_hash())
                bridge.write_text('changed bridge');second=adapter_hash();self.assertNotEqual(first,second)
                rpc.write_text('changed RPC');self.assertNotEqual(second,adapter_hash())

    def test_generated_commands_cannot_forge_controller_frames(self):
        key=b'a'*32;original={'op':'done','scores':{'score':1}}
        signed=sign_frame(original,key);self.assertEqual(verify_frame(signed,key),original)
        altered=copy.deepcopy(signed);altered['body']['scores']['score']=0
        for message,other in [(original,key),(altered,key),(signed,b'b'*32)]:
            with self.assertRaises(PolicyError):verify_frame(message,other)

    def test_chunked_records_preserve_large_transcripts_and_reject_wrong_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw=b'large transcript\n'*100_000
            for offset in range(0,len(raw),100_000):receive_record(root,{'kind':'transcript','offset':offset,'data':base64.b64encode(raw[offset:offset+100_000]).decode()})
            self.assertEqual((root/'transcript.jsonl').read_bytes(),raw)
            with self.assertRaises(PolicyError):receive_record(root,{'kind':'transcript','offset':0,'data':''})
            with self.assertRaises(PolicyError):receive_record(root,{'kind':'../../outside','offset':0,'data':''})
            with self.assertRaises(PolicyError):receive_record(root,{'kind':'result','offset':0,'data':'invalid base64!'})
    def test_all_seven_tools_are_explicit_and_supported(self):
        for tool in ['read','write','edit','glob','grep','bash','finish']:
            self.assertEqual(parse_action(json.dumps({'tool':tool,'arguments':{}}))['tool'],tool)

    def test_invalid_truncated_cloud_or_repaired_actions_are_not_executed(self):
        for raw in ['{}','[]','null','```json\n{}\n```','{"tool":"email","arguments":{}}','{"tool":[],"arguments":{}}','{"tool":"bash","arguments":[]}','{"tool":"bash","arguments":{},"url":"https://example.com"}']:
            with self.subTest(raw=raw),self.assertRaises(PolicyError):parse_action(raw)
        with self.assertRaises(PolicyError):parse_action('{"tool":"bash","arguments":{}}',True)

    def test_final_is_text_and_not_an_execution_command(self):
        self.assertEqual(parse_action('{"final":"done"}'),{'final':'done'})
        with self.assertRaises(PolicyError):parse_action('{"final":42}')

    def test_artifacts_cannot_escape_or_name_windows_drives(self):
        for path in ['../secret','/etc/passwd','C:/secret','a\\b','a//b','a/./b','a/../b','\x00']:
            with self.subTest(path=path),self.assertRaises(PolicyError):relative_file(path)
        self.assertEqual(str(relative_file('reports/result.md')),'reports/result.md')

    def test_criteria_cannot_be_missing_or_duplicated(self):
        valid={'title':'case','instructions':'do work','deliverables':{'answer':'answer.md'},'criteria':[{'id':'C1','title':'criterion','match_criteria':'evidence','deliverables':['answer']}]}
        self.assertEqual(validate_task(valid),valid)
        for modification in [{'criteria':[]},{'criteria':valid['criteria']*2},{'instructions':''},{'deliverables':{'secret':'../secret'}}]:
            with self.subTest(modification=modification),self.assertRaises(PolicyError):validate_task({**valid,**modification})

    def test_case_freeze_changes_if_a_criterion_changes(self):
        original={'criterion':'must include evidence'}
        self.assertEqual(content_hash(original),content_hash(dict(original)))
        self.assertNotEqual(content_hash(original),content_hash({'criterion':'optional evidence'}))

    def test_sandbox_requires_isolation_before_start(self):
        expected={'/opt/localauthor':('/source',False),'/workspace/documents':('/documents',False)}
        info={'Image':'sha256:'+'a'*64,'Config':{'User':'10001:10001'},'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'Memory':2*1024**3,'MemorySwap':2*1024**3,'NanoCpus':2_000_000_000,'PidsLimit':128,'Tmpfs':{'/tmp':'rw,nosuid,nodev,size=256m','/workspace':'rw,nosuid,nodev,size=512m,mode=1777','/workspace/output':'rw,nosuid,nodev,size=64m,mode=1777'}},'Mounts':[{'Destination':target,'Source':source,'Type':'bind','RW':rw} for target,(source,rw) in expected.items()]}
        verify_sandbox(info,info['Image'],expected)
        for key,value in [('NetworkMode','host'),('ReadonlyRootfs',False),('Privileged',True),('PidsLimit',0),('CapDrop',[]),('Memory',0),('PortBindings',{'80/tcp':[{}]})]:
            altered=copy.deepcopy(info);altered['HostConfig'][key]=value
            with self.subTest(key=key),self.assertRaises(PolicyError):verify_sandbox(altered,info['Image'],expected)
        altered=copy.deepcopy(info);altered['Mounts'][0]['RW']=True
        with self.assertRaises(PolicyError):verify_sandbox(altered,info['Image'],expected)
        altered=copy.deepcopy(info);altered['Mounts'][0]['Source']='/different'
        with self.assertRaises(PolicyError):verify_sandbox(altered,info['Image'],expected)

    def test_report_escapes_model_and_task_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);write_report(root,[{'id':'<img src=x>','status':'error','error':'<script>alert(1)</script>','scores':{'criteria_results':[{'verdict':'fail','title':'<iframe>','reasoning':'<script>model()</script>'}]}}])
            text=(root/'report.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>',text);self.assertNotIn('<iframe>',text)
            self.assertIn('&lt;script&gt;',text);self.assertIn('Revisão humana necessária',text)


if __name__=='__main__':unittest.main()
