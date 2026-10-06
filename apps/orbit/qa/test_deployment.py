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
    def test_repository_snapshot_retains_history_without_following_links(self):
        root=pathlib.Path(self.temp.name);repos=root/'repos';repos.mkdir()
        (repos/'project.git').mkdir();(repos/'project.git'/'HEAD').write_text('ref: refs/heads/main\n')
        outside=root/'private-outside';outside.write_text('not included')
        (repos/'link').symlink_to(outside)
        snapshot=root/'snapshot.tar.gz';deploy.backup_repositories(repos,snapshot)
        self.assertEqual(0o600,snapshot.stat().st_mode&0o777)
        with tarfile.open(snapshot) as archive:
            self.assertTrue(archive.getmember('repos/link').issym())
            self.assertEqual(b'ref: refs/heads/main\n',archive.extractfile('repos/project.git/HEAD').read())
            self.assertNotIn('private-outside',archive.getnames())
    def test_repository_snapshot_cannot_overwrite_a_prior_backup(self):
        root=pathlib.Path(self.temp.name);repos=root/'repos';repos.mkdir();snapshot=root/'snapshot.tar.gz';snapshot.write_bytes(b'preserved')
        with self.assertRaises(FileExistsError):deploy.backup_repositories(repos,snapshot)
        self.assertEqual(b'preserved',snapshot.read_bytes())
    def test_joint_backup_pauses_writer_before_both_snapshots(self):
        root=pathlib.Path(self.temp.name);repos=root/'repos';repos.mkdir();(repos/'HEAD').write_text('ref: refs/heads/main\n')
        events=[]
        def dump(args,**kwargs):
            self.assertEqual([('stop','api')],events)
            kwargs['stdout'].write(b'-- synthetic PostgreSQL backup\n')
            events.append(('dump',))
            return type('Result',(),{'returncode':0})()
        with patch.object(deploy,'ROOT',root),patch.object(deploy,'compose',side_effect=lambda *a:events.append(a)),patch.object(deploy.subprocess,'run',side_effect=dump):
            deploy.backup_state(repos)
        self.assertEqual([('stop','api'),('dump',)],events)
        self.assertEqual(1,len(list((root/'backups').glob('*-repos.tar.gz'))))
        self.assertEqual(0o600,next((root/'backups').glob('*.sql')).stat().st_mode&0o777)
    def test_database_backup_failure_resumes_only_own_api(self):
        root=pathlib.Path(self.temp.name);repos=root/'repos';repos.mkdir();events=[]
        with patch.object(deploy,'ROOT',root),patch.object(deploy,'compose',side_effect=lambda *a:events.append(a)),patch.object(deploy.subprocess,'run',return_value=type('Result',(),{'returncode':1})()):
            with self.assertRaises(RuntimeError):deploy.backup_state(repos)
        self.assertEqual([('stop','api'),('start','api')],events)
        self.assertEqual([],list((root/'backups').glob('*-repos.tar.gz')))
if __name__=='__main__':unittest.main(verbosity=2)
