"""Lazy optional libraries. No remote endpoints, model IDs or download fallback."""
from __future__ import annotations

import inspect
import os
import time

from ..errors import PolicyError
from ..efficiency.residency import release_tensors
from .models import ModelSpec, read_object


def check_cancel(cancel, deadline: float | None = None) -> None:
    if cancel is not None and cancel.is_set():
        raise PolicyError("Geração cancelada.")
    if deadline is not None and time.monotonic() >= deadline:
        raise PolicyError("Geração excedeu o orçamento de tempo.")


def offline_environment() -> None:
    # Defense in depth, not a security sandbox for operator-approved Python code.
    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "DO_NOT_TRACK"):
        os.environ[key] = "1"


class TextRuntime:
    def __init__(self, spec: ModelSpec):
        offline_environment()
        self.spec = spec
        self.model = self.tokenizer = None
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise PolicyError("Instale as dependências opcionais de requirements-foundation.txt.") from exc
        self.torch = torch
        options = {"local_files_only": True, "trust_remote_code": spec.reviewed_local_code}
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(spec.directory), **options)
            self.model = AutoModelForCausalLM.from_pretrained(
                str(spec.directory), **options, use_safetensors=True,
                torch_dtype=getattr(torch, spec.dtype), device_map=spec.device)
            self.model.eval()
        except (OSError, ValueError, ImportError, RuntimeError) as exc:
            self.close()
            raise PolicyError("Checkpoint incompatível ou dependência ausente. Homologue arquitetura/runtime; não houve fallback remoto.") from exc

    def close(self) -> None:
        release_tensors(self, ("model", "tokenizer"))

    def _template(self, messages, **kwargs):
        if self.model is None or self.tokenizer is None:
            raise PolicyError("Modelo textual descarregado.")
        # Identical profile for counting and generation; template support must
        # still be qualified against the checkpoint, not inferred from this flag.
        return self.tokenizer.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=True, enable_thinking=self.spec.enable_thinking, **kwargs)

    def count(self, messages: list[dict]) -> int:
        return len(self._template(messages, return_dict=False))

    def generate(self, messages: list[dict], cancel=None) -> tuple[str, bool]:
        from transformers import StoppingCriteria, StoppingCriteriaList
        check_cancel(cancel)
        deadline = time.monotonic() + self.spec.generation_seconds

        class Stop(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return (cancel is not None and cancel.is_set()) or time.monotonic() >= deadline

        inputs = self._template(messages, return_tensors="pt", return_dict=True)
        if inputs["input_ids"].shape[-1] + self.spec.output_tokens > self.spec.context_tokens:
            raise PolicyError("Contexto real excede o orçamento do modelo.")
        inputs = inputs.to(self.model.device)
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=self.spec.output_tokens,
                     do_sample=False, stopping_criteria=StoppingCriteriaList([Stop()]))
        check_cancel(cancel, deadline)
        tokens = output[0][inputs["input_ids"].shape[-1]:]
        text = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
        if not text:
            raise PolicyError("O modelo não produziu resposta; nenhuma conclusão foi inventada.")
        return text, len(tokens) >= self.spec.output_tokens


class ImageRuntime:
    def __init__(self, spec: ModelSpec):
        offline_environment()
        self.spec = spec
        self.pipeline = None
        if spec.device == "auto":
            raise PolicyError("Imagens exigem dispositivo cpu ou cuda explícito nesta versão.")
        try:
            import torch
            # Import only the homologated pipeline. AutoPipeline imports many
            # unrelated families and may require incompatible extra tokenizers.
            from diffusers import StableDiffusionPipeline
        except (ImportError, RuntimeError) as exc:
            raise PolicyError("Instale as dependências opcionais de requirements-foundation.txt.") from exc
        self.torch = torch
        if read_object(spec.directory / "model_index.json").get("_class_name") != "StableDiffusionPipeline":
            raise PolicyError("Este perfil visual homologa somente StableDiffusionPipeline nativo.")
        try:
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                str(spec.directory), local_files_only=True, use_safetensors=True,
                torch_dtype=getattr(torch, spec.dtype)).to(spec.device)
        except (OSError, ValueError, ImportError, RuntimeError) as exc:
            self.close()
            raise PolicyError("Pipeline visual local incompatível; nenhum serviço externo foi utilizado.") from exc
        if getattr(self.pipeline, "safety_checker", None) is None or getattr(self.pipeline, "feature_extractor", None) is None:
            raise PolicyError("Este perfil visual exige verificador e extrator ativos; não desative para aceitar uma imagem.")
        if "callback_on_step_end" not in inspect.signature(self.pipeline.__call__).parameters:
            self.close()
            raise PolicyError("Pipeline sem callback de cancelamento; homologue uma implementação suportada.")

    def close(self) -> None:
        release_tensors(self, ("pipeline",))

    def generate(self, prompt: str, cancel=None, *, options=None):
        from .visual import ImageOptions
        profile = ImageOptions.parse(options)
        if options is not None and type(self.pipeline).__name__ != "StableDiffusionPipeline":
            raise PolicyError("Parâmetros configuráveis exigem perfil StableDiffusionPipeline homologado.")
        check_cancel(cancel)
        if self.pipeline is None:
            raise PolicyError("Modelo visual descarregado.")
        for name in ("tokenizer", "tokenizer_2", "tokenizer_3"):
            tokenizer = getattr(self.pipeline, name, None)
            if tokenizer is not None:
                limit = getattr(tokenizer, "model_max_length", 0)
                count = len(tokenizer(prompt, truncation=False)["input_ids"])
                if isinstance(limit, int) and 0 < limit < 1000000 and count > limit:
                    raise PolicyError("Descrição excede o tokenizador visual; reduza o briefing. Nada foi truncado silenciosamente.")
        deadline = time.monotonic() + self.spec.generation_seconds

        def callback(pipe, step, timestep, kwargs):
            check_cancel(cancel, deadline)
            return kwargs

        generator = self.torch.Generator(device=self.spec.device).manual_seed(profile.seed)
        with self.torch.inference_mode():
            kwargs = dict(prompt=prompt, width=profile.width, height=profile.height,
                          num_inference_steps=profile.steps, generator=generator, callback_on_step_end=callback)
            if options is not None:
                kwargs["guidance_scale"] = profile.guidance_scale
            result = self.pipeline(**kwargs)
        check_cancel(cancel, deadline)
        flagged = getattr(result, "nsfw_content_detected", None)
        images = getattr(result, "images", None)
        if (not isinstance(flagged, (list, tuple)) or not images or len(flagged) != len(images)
                or any(type(flag) is not bool for flag in flagged)):
            raise PolicyError("Pipeline sem resultado verificável do controle visual.")
        if any(flagged):
            raise PolicyError("O verificador do pipeline bloqueou a saída visual.")
        return images[0]
