"""Trust boundary checks for release archives; never calls Docker or SSH."""
import hashlib, importlib.util, io, json, pathlib, tarfile, tempfile, unittest
spec=importlib.util.spec_from_file_location('orbit_deploy',pathlib.Path(__file__).resolve().parents[1]/'ops/server_deploy.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
class Archives(unittest.TestCase):
    def archive(self,tag='orbit-hml-api:'+('a'*40),user='10001:10001',revision='a'*40,bad_digest=False):
        data=json.dumps({'config':{'User':user,'Labels':{'org.opencontainers.image.revision':revision}}}).encode()
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
if __name__=='__main__':unittest.main(verbosity=2)
