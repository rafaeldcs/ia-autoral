from __future__ import annotations
from collections import Counter


class ByteTokenizer:
    bos_id, eos_id, vocab_size = 256, 257, 258

    def encode(self, text: str, *, special: bool = False) -> list[int]:
        ids = list(text.encode("utf-8"))
        return [self.bos_id, *ids, self.eos_id] if special else ids

    def decode(self, ids: list[int], *, errors: str = "strict") -> str:
        if any(type(x) is not int or x < 0 or x >= self.vocab_size for x in ids):
            raise ValueError("Token inválido.")
        return bytes(x for x in ids if x < 256).decode("utf-8", errors=errors)

    def to_dict(self):
        return {"kind": "utf8-byte", "version": 1, "vocab_size": 258}


class BPETokenizer(ByteTokenizer):
    """BPE próprio para experimentos pequenos, com desempate determinístico."""
    def __init__(self, merges: list[tuple[int, int]] | None = None):
        self.merges = [tuple(p) for p in (merges or [])]
        self.pieces = {i: bytes([i]) for i in range(256)}
        for index, pair in enumerate(self.merges, 258):
            if len(pair) != 2 or any(p not in self.pieces for p in pair):
                raise ValueError("Tabela de merges inválida.")
            self.pieces[index] = self.pieces[pair[0]] + self.pieces[pair[1]]
        self.vocab_size = 258 + len(self.merges)

    @staticmethod
    def _replace(sequence, pair, token):
        result, pos = [], 0
        while pos < len(sequence):
            if pos + 1 < len(sequence) and (sequence[pos], sequence[pos + 1]) == pair:
                result.append(token)
                pos += 2
            else:
                result.append(sequence[pos])
                pos += 1
        return result

    @classmethod
    def train(cls, documents: list[str], vocab_size: int = 320):
        if not 258 <= vocab_size <= 1024 or sum(len(d.encode("utf-8")) for d in documents) > 500_000:
            raise ValueError("BPE de referência limitado a 1024 tokens e 500 KB de entrada.")
        sequences = [list(d.encode("utf-8")) for d in documents]
        merges = []
        while 258 + len(merges) < vocab_size:
            counts = Counter(pair for seq in sequences for pair in zip(seq, seq[1:]))
            if not counts: break
            pair = min(counts, key=lambda p: (-counts[p], p))
            if counts[pair] < 2: break
            token = 258 + len(merges)
            merges.append(pair)
            sequences = [cls._replace(seq, pair, token) for seq in sequences]
        return cls(merges)

    def encode(self, text: str, *, special: bool = False) -> list[int]:
        sequence = list(text.encode("utf-8"))
        for token, pair in enumerate(self.merges, 258):
            sequence = self._replace(sequence, pair, token)
        return [256, *sequence, 257] if special else sequence

    def decode(self, ids: list[int], *, errors: str = "strict") -> str:
        if any(type(x) is not int or x < 0 or x >= self.vocab_size for x in ids):
            raise ValueError("Token inválido.")
        return b"".join(self.pieces[x] for x in ids if x not in {256, 257}).decode("utf-8", errors=errors)

    def to_dict(self):
        return {"kind": "utf8-bpe", "version": 1, "merges": [list(p) for p in self.merges]}


def tokenizer_from_dict(data: dict):
    if data.get("version") != 1:
        raise ValueError("Versão de tokenizador não suportada.")
    if data.get("kind") == "utf8-byte": return ByteTokenizer()
    if data.get("kind") == "utf8-bpe": return BPETokenizer(data["merges"])
    raise ValueError("Tipo de tokenizador desconhecido.")
