"""Evaluator rejection tests with explicit fixtures; no model or generated code runs."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

loader=importlib.util.spec_from_file_location('chat_code_replay',Path(__file__).resolve().parents[1]/'scripts/chat-code-replay.py')
replay=importlib.util.module_from_spec(loader);loader.loader.exec_module(replay)


class ChatCodeReplayControls(unittest.TestCase):
    def candidate(self):
        content='```text\n\t// ação 😀\r\n```\n'
        row={'content':content,'sha256':hashlib.sha256(content.encode()).hexdigest(),
             'metadata':{'origin':'foundation_text','possibly_truncated':False,'model':{'model_id':'explicit-test-double'}}}
        return {'schema':1,'artifacts':{name:copy.deepcopy(row) for name in replay.FILES}}

    def test_original_code_bytes_and_provenance_are_preserved(self):
        candidate=self.candidate();before=copy.deepcopy(candidate)
        files,provenance=replay.decode_candidate(candidate)
        self.assertEqual(candidate,before)
        self.assertEqual(set(files),replay.FILES)
        self.assertTrue(all(source=='\t// ação 😀\r\n' for source in files.values()))
        self.assertEqual(provenance['Tarefa.cs']['source_sha256'],hashlib.sha256(files['Tarefa.cs'].encode()).hexdigest())

    def test_changed_hash_truncation_or_nonmodel_origin_is_rejected(self):
        for mutate in (lambda row:row.update(sha256='0'*64),
                       lambda row:row['metadata'].update(possibly_truncated=True),
                       lambda row:row['metadata'].update(origin='fixture')):
            value=self.candidate();mutate(value['artifacts']['Tarefa.cs'])
            with self.assertRaises(ValueError):replay.decode_candidate(value)

    def test_arbitrary_filenames_and_multiple_blocks_are_rejected(self):
        value=self.candidate();value['artifacts']['../outside.cs']=value['artifacts'].pop('Tarefa.cs')
        with self.assertRaises(ValueError):replay.decode_candidate(value)
        value=self.candidate();row=value['artifacts']['Tarefa.cs'];row['content']+='```text\nextra\n```'
        row['sha256']=hashlib.sha256(row['content'].encode()).hexdigest()
        with self.assertRaises(ValueError):replay.decode_candidate(value)

    def config(self):
        runner=Path('/trusted/qa/chat-code-replay')
        return runner,{'Image':'sha256:fixture','Config':{'User':'10001:10001'},'Mounts':[
            {'Type':'bind','Source':runner.as_posix(),'Destination':'/runner','RW':False}],
            'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'PortBindings':{},
            'Devices':[],'DeviceRequests':None,'CapDrop':['ALL'],'CapAdd':None,'SecurityOpt':['no-new-privileges'],
            'Memory':4*1024**3,'NanoCpus':2_000_000_000,'PidsLimit':512,'PidMode':'','IpcMode':'private','Binds':None,
            'Tmpfs':{'/tmp':'rw,nosuid,nodev,size=2g,mode=1777'}}}

    def test_network_root_user_writable_or_wrong_mount_never_pass_inspection(self):
        runner,config=self.config();replay.validate_container(config,'sha256:fixture',runner)
        for change in (lambda c:c['HostConfig'].update(NetworkMode='host'),
                       lambda c:c['Config'].update(User='0'),
                       lambda c:c['Mounts'][0].update(RW=True),
                       lambda c:c['Mounts'][0].update(Source='/other/chat-code-replay'),
                       lambda c:c['HostConfig'].update(ReadonlyRootfs=False),
                       lambda c:c['HostConfig'].update(DeviceRequests=[{'Count':-1}])):
            value=copy.deepcopy(config);change(value)
            with self.assertRaises(ValueError):replay.validate_container(value,'sha256:fixture',runner)

    def report(self):
        return {'csharp_build_passed':True,'tsx_typecheck_passed':True,'next_build_passed':True,
                'sql_script_passed':True,'csharp_test_exit':0,'cases':[
            {'area':area,'name':f'fixture-{n}','passed':True} for area,count in replay.EXPECTED.items() for n in range(count)]}

    def test_missing_duplicate_failed_or_extra_cases_cannot_become_a_pass(self):
        original=self.report();self.assertTrue(replay.summarize(original,'normal'))
        for change in (lambda r:r['cases'].pop(),lambda r:r['cases'][0].update(passed=False),
                       lambda r:r['cases'].append({'area':'unknown','name':'extra','passed':True}),
                       lambda r:r['cases'][1].update(name='fixture-0'),
                       lambda r:r.update(csharp_test_exit=1),lambda r:r.update(next_build_passed=False)):
            value=copy.deepcopy(original);change(value)
            self.assertFalse(replay.summarize(value,'normal'))

    def test_mutations_must_compile_and_be_detected_in_every_area(self):
        value=self.report();value['csharp_test_exit']=1
        self.assertFalse(replay.summarize(value,'mutations'))
        for area in replay.EXPECTED:
            next(r for r in value['cases'] if r['area']==area)['passed']=False
        self.assertTrue(replay.summarize(value,'mutations'))
        value['csharp_build_passed']=False
        self.assertFalse(replay.summarize(value,'mutations'))
