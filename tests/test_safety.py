import os
from pathlib import Path
from localauthor.errors import PolicyError
from localauthor.safety import PathPolicy, validate_relative, reject_secrets
from localauthor.config import Settings
from tests.helpers import WorkspaceCase


class SafetyTests(WorkspaceCase):
    def test_reads_only_authorized_regular_file(self):
        self.assertIn(b"Product", PathPolicy(self.project_root).read("Product.cs"))

    def test_rejects_parent_traversal(self):
        for p in ["../Product.cs", "a/../../x.cs", "a/./x.cs", "a//b.cs"]:
            with self.subTest(path=p), self.assertRaises(PolicyError): validate_relative(p)

    def test_rejects_absolute_and_windows_paths(self):
        for p in ["/etc/passwd", "C:/secret.cs", "C:\\secret.cs", "//host/share.cs", "x.cs:secret"]:
            with self.subTest(path=p), self.assertRaises(PolicyError): validate_relative(p)

    def test_rejects_hidden_credentials_and_git(self):
        for p in [".env", ".env.production", ".git/config", "secrets.json", "api.token", "a/credentials", ".github/workflows/a.yml"]:
            with self.subTest(path=p), self.assertRaises(PolicyError): validate_relative(p)

    def test_rejects_windows_reserved_names(self):
        for p in ["CON.cs", "a/NUL.txt", "lpt1.md", "x./a.cs", "a /b.cs"]:
            with self.subTest(path=p), self.assertRaises(PolicyError): validate_relative(p)

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).resolve("app.exe")

    def test_rejects_binary(self):
        (self.project_root/"binary.txt").write_bytes(b"x\x00y")
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).read("binary.txt")

    def test_rejects_large_file(self):
        with self.assertRaises(PolicyError): PathPolicy(self.project_root, 5).read("Product.cs")

    def test_rejects_symlink_file(self):
        try: (self.project_root/"link.cs").symlink_to(self.project_root/"Product.cs")
        except OSError: self.skipTest("Criação de symlink indisponível neste SO.")
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).read("link.cs")

    def test_rejects_symlink_directory(self):
        outside = self.root/"outside"; outside.mkdir(); (outside/"x.cs").write_text("test")
        try: (self.project_root/"link").symlink_to(outside, target_is_directory=True)
        except OSError: self.skipTest("Symlink indisponível.")
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).read("link/x.cs")

    def test_rejects_symlink_root(self):
        link = self.root/"root-link"
        try: link.symlink_to(self.project_root, target_is_directory=True)
        except OSError: self.skipTest("Symlink indisponível.")
        with self.assertRaises(PolicyError): PathPolicy(link)

    def test_rejects_hardlink(self):
        os.link(self.project_root/"Product.cs", self.project_root/"hard.cs")
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).read("hard.cs")

    def test_test_file_edit_needs_explicit_approval(self):
        policy = PathPolicy(self.project_root)
        with self.assertRaises(PolicyError): policy.resolve("tests/Test.cs", write=True)
        self.assertEqual(policy.resolve("tests/Test.cs", write=True, allow_tests=True).name, "Test.cs")

    def test_build_configuration_not_editable(self):
        with self.assertRaises(PolicyError): PathPolicy(self.project_root).resolve("Project.csproj", write=True)

    def test_secret_scanner(self):
        for content in ['api_key = "'+'a'*25+'"', "-----BEGIN PRIVATE"+" KEY-----", "ghp_"+"a"*36]:
            with self.subTest(content=content[:8]), self.assertRaises(PolicyError): reject_secrets(content)
        reject_secrets("public string Password { get; set; }")

    def test_project_does_not_accept_data_folder(self):
        with self.assertRaises(PolicyError): self.store.add_project("dados", str(self.settings.home))

    def test_config_unknown_field_fails_closed(self):
        from localauthor.util import write_json
        write_json(self.settings.home/"settings.json", {"allow_any_network": True})
        with self.assertRaises(PolicyError): Settings.load(self.settings.home)

    def test_index_walker_excludes_dependencies(self):
        (self.project_root/"node_modules").mkdir()
        (self.project_root/"node_modules"/"x.js").write_text("unneeded")
        self.assertNotIn("node_modules/x.js", list(PathPolicy(self.project_root).files()))
