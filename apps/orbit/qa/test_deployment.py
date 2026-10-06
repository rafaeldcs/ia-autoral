"""Trust boundary checks for release archives; never calls Docker or SSH."""
import hashlib, importlib.util, io, json, pathlib, tarfile, tempfile, unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('orbit_deploy',pathlib.Path(__file__).resolve().parents[1]/'ops/server_deploy.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
class Archives(unittest.TestCase):
    def archive(self,tag='orbit-hml-api:'+('a'*40),user='10001:10001',revision='a'*40,bad_digest=False):
        data=json.dumps({'config':{'User':user,'Labels':{'org.opencontainers.image.revision':revision,'io.localauthor.application':'orbit-hml'}}}).encode()
        digest='b'*64 if bad_digest else hashlib.sha256(data).hexdigest()
        config='blobs/sha256/'+digest
        manifest=json.dumps([{'Config':config,'RepoTags':[tag]}]).encode()
        path=pathlib.Path(self.temp.name)/'image.tar'
        with tarfile.open(path,'w') as archive:
            for name,body in [('manifest.json',manifest),(config,data)]:
                entry=tarfile.TarInfo(name);entry.size=len(body);archive.addfile(entry,io.BytesIO(body))
        return path
    def setUp(self):self.temp=tempfile.TemporaryDirectory()
    def tearDown(self):self.temp.cleanup()
    def validate(self,**changes):deploy.validate_image(self.archive(**changes),'orbit-hml-api:'+('a'*40),'a'*40)
    def test_valid_immutable_image(self):self.validate()
    def test_other_application_tag_rejected(self):
        with self.assertRaises(ValueError):self.validate(tag='shopair-api:latest')
    def test_privileged_user_rejected(self):
        with self.assertRaises(ValueError):self.validate(user='root')
    def test_wrong_revision_rejected(self):
        with self.assertRaises(ValueError):self.validate(revision='b'*40)
    def test_digest_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.validate(bad_digest=True)
    def test_rerun_cannot_replace_existing_rollback_image(self):
        existing=type('Result',(),{'returncode':0,'stdout':json.dumps([{'Config':{'User':'10001:10001','Labels':{'org.opencontainers.image.revision':'a'*40,'io.localauthor.application':'orbit-hml'}}}])})()
        with patch.object(deploy.subprocess,'run',return_value=existing),patch.object(deploy,'run',side_effect=AssertionError('Existing SHA must never be loaded again')):
            deploy.load_once(self.archive(),'orbit-hml-api:'+('a'*40),'a'*40)
    def test_occupied_foreign_tag_rejected(self):
        existing=type('Result',(),{'returncode':0,'stdout':json.dumps([{'Config':{'User':'root','Labels':{}}}])})()
        with patch.object(deploy.subprocess,'run',return_value=existing),patch.object(deploy,'run',side_effect=AssertionError('Foreign tag must not be replaced')):
            with self.assertRaises(ValueError):deploy.load_once(self.archive(),'orbit-hml-api:'+('a'*40),'a'*40)
if __name__=='__main__':unittest.main(verbosity=2)
