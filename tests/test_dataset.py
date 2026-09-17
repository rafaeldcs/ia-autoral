from localauthor.dataset import validate_dataset
from localauthor.errors import PolicyError
from localauthor.util import read_json, write_json, sha256
from tests.helpers import WorkspaceCase, make_dataset


class DatasetTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.manifest = make_dataset(self.root/"dataset")
    def modify(self, change):
        data=read_json(self.manifest); change(data); write_json(self.manifest,data)

    def test_valid_manifest_test_text_not_returned(self):
        result = validate_dataset(self.manifest)
        self.assertEqual(len(result["splits"]["train"]),1)
        self.assertNotIn("text",result["splits"]["test"][0])

    def test_permission_required(self):
        self.modify(lambda d: d["records"][0].update(training_allowed=False))
        with self.assertRaises(PolicyError): validate_dataset(self.manifest)

    def test_provenance_required(self):
        self.modify(lambda d: d["records"][0].update(provenance={}))
        with self.assertRaises(PolicyError): validate_dataset(self.manifest)

    def test_exact_duplicate_across_split_blocked(self):
        raw=(self.manifest.parent/"train.txt").read_bytes(); (self.manifest.parent/"validation.txt").write_bytes(raw)
        self.modify(lambda d: d["records"][1].update(sha256=sha256(raw)))
        with self.assertRaises(PolicyError): validate_dataset(self.manifest)

    def test_group_cannot_cross_split(self):
        self.modify(lambda d: d["records"][1].update(group=d["records"][0]["group"]))
        with self.assertRaises(PolicyError): validate_dataset(self.manifest)

    def test_hash_change_detected(self):
        (self.manifest.parent/"train.txt").write_text("changed")
        with self.assertRaises(PolicyError): validate_dataset(self.manifest)

    def test_near_duplicate_across_split_detected(self):
        train=" ".join("word"+str(i) for i in range(120))
        validation=train+" extra"
        manifest=make_dataset(self.root/"near",train,validation)
        with self.assertRaises(PolicyError): validate_dataset(manifest)
