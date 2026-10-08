import json
import unittest
from pathlib import Path

from localauthor.message_format import detect_message_format, resolve_message_format


class MessageFormatTests(unittest.TestCase):
    def test_code_prose_and_mixed_content(self):
        samples = json.loads((Path(__file__).parent / "fixtures/message_formats.json").read_text(encoding="utf-8"))
        for sample in samples:
            with self.subTest(message=sample["message"]):
                self.assertEqual(detect_message_format(sample["message"]), sample["format"])

    def test_legacy_explicit_formats_remain_supported(self):
        self.assertEqual(resolve_message_format("const x = 1;", "text"), "text")
        self.assertEqual(resolve_message_format("Explique o projeto", "code"), "code")

    def test_classification_does_not_rewrite_input(self):
        original = '\tconst texto = "ação é 😀";  \r\n// <script>não executar</script>\r\n'
        encoded = original.encode("utf-8")
        self.assertEqual(resolve_message_format(original), "code")
        self.assertEqual(original.encode("utf-8"), encoded)
