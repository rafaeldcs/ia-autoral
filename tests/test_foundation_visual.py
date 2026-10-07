import io
from unittest.mock import Mock
from types import SimpleNamespace

from tests.helpers import WorkspaceCase
from tests.test_foundation import DummyImageArtifact, register_fixture, DummyImage
from localauthor.errors import PolicyError
from localauthor.foundation.runtime import ImageRuntime
from localauthor.foundation.service import FoundationService
from localauthor.foundation.visual import ImageOptions, verify_png


class VisualProfileTests(WorkspaceCase):
    def test_options_are_bounded_typed_and_finite(self):
        self.assertEqual(ImageOptions.parse().metadata()["seed"], 31)
        for value in ({"width": 255}, {"height": True}, {"steps": 0}, {"steps": 51}, {"seed": -1},
                      {"guidance_scale": float("nan")}, {"guidance_scale": 16}, {"unknown": 3}):
            with self.subTest(value=value), self.assertRaises(PolicyError): ImageOptions.parse(value)

    def test_png_requires_valid_crc_pixels_end_and_dimensions(self):
        stream = io.BytesIO(); DummyImageArtifact().save(stream, "PNG"); valid = stream.getvalue()
        verify_png(valid, (512, 512))
        for value, size in ((valid[:-12], (512, 512)), (valid + b"extra", (512, 512)),
                            (valid[:40] + b"bad" + valid[43:], (512, 512)), (valid, (256, 256)),
                            (b"\x89PNG\r\n\x1a\n", (512, 512)), (valid, (100000, 100000))):
            with self.subTest(size=size), self.assertRaises(PolicyError): verify_png(value, size)

    def test_configurable_runtime_passes_exact_options_to_supported_pipeline(self):
        runtime = ImageRuntime.__new__(ImageRuntime)
        runtime.spec = SimpleNamespace(device="cpu", generation_seconds=300)
        generator = Mock(); runtime.torch = SimpleNamespace(Generator=Mock(return_value=generator), inference_mode=__import__('contextlib').nullcontext)
        received = {}
        class StableDiffusionPipeline:
            def __call__(self, **kwargs):
                received.update(kwargs)
                kwargs["callback_on_step_end"](self, 0, 0, {})
                return SimpleNamespace(images=[DummyImageArtifact()], nsfw_content_detected=[False])
        runtime.pipeline = StableDiffusionPipeline()
        runtime.generate("fixture", options={"width": 256, "height": 512, "steps": 8, "seed": 17})
        self.assertEqual((received["width"], received["height"], received["num_inference_steps"]), (256, 512, 8))
        generator.manual_seed.assert_called_once_with(17)

    def test_service_stores_options_and_recovers_valid_png(self):
        register_fixture(self.settings.home, self.root / "visual-model", "image")
        service = FoundationService(self.settings.home, image_factory=DummyImage)
        result = service.create_image(self.project["id"], "fixture", options={"seed": 17, "steps": 8})
        self.assertEqual((result["seed"], result["steps"]), (17, 8))
        self.assertEqual(service.image(self.project["id"], result["artifact_id"])["sha256"], result["artifact_sha256"])
