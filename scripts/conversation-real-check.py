"""Opt-in real local-model exercise. Outputs are evidence for human review, not a judge."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from localauthor.foundation.context import SYSTEM, build_context
from localauthor.foundation.service import FoundationService
from localauthor.voice import DockerSpeechRuntime, validate_audio, validate_manifest
from localauthor.foundation.models import read_object

CASES = [
    ('greeting', 'Oi, bom dia!', []),
    ('thanks', 'Obrigado, ajudou muito!', []),
    ('farewell', 'Valeu, até amanhã!', []),
    ('frustration', 'Estou frustrado, não entendi sua explicação. Pode explicar de um jeito mais simples?', []),
    ('mixed', 'Obrigado! Agora me explique em duas frases o que é uma API.', []),
    ('honesty', 'Você já corrigiu meu código e treinou seus pesos com esta conversa?', []),
    ('english', 'Thanks, that helped! Please reply in English.', []),
    ('thanks_variant', 'Perfeito, muito grato pela ajuda.', []),
    ('spanish', 'Gracias por la ayuda. Responde en español.', []),
    ('new_question', 'Me explica em uma frase o que é DNS?', []),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-real', action='store_true', required=True)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audio-fixtures', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'kind': 'real_local_inference', 'cases': [], 'voice': [], 'success': False, 'quality_approved': False,
              'system_prompt_sha256': hashlib.sha256(SYSTEM.encode('utf-8')).hexdigest(),
              'limitations': ['Human semantic review required; no automatic quality score.',
                             'Synthetic audio does not qualify a physical microphone or latency on other machines.',
                             'No weight training; no external AI service.']}
    service = FoundationService(args.home)
    try:
        started = time.monotonic()
        spec, engine = service._engine('text')
        report['load_seconds'] = round(time.monotonic() - started, 3)
        report['model'] = spec.provenance()
        def answer(name, message, history):
            started = time.monotonic()
            context = build_context(message, history, [], scope='a' * 32, count=engine.count,
                                    context_tokens=spec.context_tokens, output_tokens=spec.output_tokens)
            content, truncated = engine.generate(context.messages)
            result = {'case': name, 'user': message, 'assistant': content, 'truncated': truncated,
                      'seconds': round(time.monotonic() - started, 3), 'input_tokens': context.input_tokens,
                      'history_messages_used': context.history_used}
            report['cases'].append(result)
            (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'case': name, 'seconds': result['seconds'], 'truncated': truncated}), flush=True)
            return content
        for name, message, history in CASES:
            answer(name, message, history)
        first = 'Meu projeto de laboratório se chama Aurora e usa Kanban. Repita apenas o nome e o método.'
        content = answer('context_first', first, [])
        history = [{'role': 'user', 'content': first}, {'role': 'assistant', 'content': content}]
        answer('context_followup', 'Obrigado! Qual era mesmo o nome do meu projeto e o método?', history)
        if args.audio_fixtures:
            voice_spec = validate_manifest(read_object(args.home / 'voice/model.json'))
            report['voice_model'] = voice_spec
            history = []
            for wav in sorted(args.audio_fixtures.glob('input-*.wav')):
                raw = wav.read_bytes()
                encoded = base64.b64encode(raw).decode('ascii')
                validate_audio(encoded)
                started = time.monotonic()
                result = DockerSpeechRuntime(voice_spec).transcribe(encoded, threading.Event())
                report['voice'].append({'file': wav.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                    'transcript': result['text'], 'offline': result['offline'],
                    'seconds': round(time.monotonic() - started, 3)})
                content = answer('audio_' + wav.stem, result['text'], history)
                history.extend([{'role': 'user', 'content': result['text']}, {'role': 'assistant', 'content': content}])
        report['success'] = all(not x['truncated'] for x in report['cases'])
    finally:
        service.close()
        (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
