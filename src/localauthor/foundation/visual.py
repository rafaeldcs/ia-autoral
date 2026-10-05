"""Bounded Stable Diffusion profiles and PNG integrity, without model claims."""
from dataclasses import asdict, dataclass
import math
import struct
import zlib

from ..errors import PolicyError


@dataclass(frozen=True)
class ImageOptions:
    width: int = 512
    height: int = 512
    seed: int = 31
    steps: int = 20
    guidance_scale: float = 7.5

    @classmethod
    def parse(cls, value=None):
        value = {} if value is None else value
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise PolicyError("Parâmetros visuais desconhecidos.")
        option = cls(**value)
        if any(type(n) is not int or not 256 <= n <= 768 or n % 64 for n in (option.width, option.height)):
            raise PolicyError("Dimensões visuais: 256 a 768, múltiplos de 64.")
        if type(option.seed) is not int or not 0 <= option.seed <= 2147483647:
            raise PolicyError("Seed visual inválida.")
        if type(option.steps) is not int or not 1 <= option.steps <= 50:
            raise PolicyError("Passos visuais: 1 a 50.")
        if (type(option.guidance_scale) not in (int, float) or not math.isfinite(option.guidance_scale)
                or not 1 <= option.guidance_scale <= 15):
            raise PolicyError("Guidance visual: 1 a 15.")
        return option

    def metadata(self):
        return asdict(self)


def verify_png(raw: bytes, expected_size: tuple[int, int]) -> None:
    if (not isinstance(expected_size, tuple) or len(expected_size) != 2
            or any(type(n) is not int or not 256 <= n <= 768 or n % 64 for n in expected_size)):
        raise PolicyError("Dimensões PNG fora do orçamento homologado.")
    if len(raw) > 8000000 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise PolicyError("PNG ausente, inválido ou excessivo.")
    cursor, header, compressed, ended = 8, None, bytearray(), False
    while cursor < len(raw):
        if cursor + 12 > len(raw): raise PolicyError("PNG truncado.")
        size = struct.unpack(">I", raw[cursor:cursor + 4])[0]
        kind = raw[cursor + 4:cursor + 8]
        end = cursor + 8 + size
        if end + 4 > len(raw): raise PolicyError("Chunk PNG truncado.")
        content = raw[cursor + 8:end]
        if struct.unpack(">I", raw[end:end + 4])[0] != zlib.crc32(kind + content) & 0xffffffff:
            raise PolicyError("CRC do PNG não confere.")
        if header is None and kind != b"IHDR": raise PolicyError("IHDR precisa ser o primeiro chunk.")
        if kind == b"IHDR":
            if header is not None or size != 13: raise PolicyError("IHDR inválido.")
            header = struct.unpack(">2I5B", content)
            width, height, depth, color, compression, filtering, interlace = header
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            if ((width, height) != expected_size or not channels or depth != 8
                    or compression or filtering or interlace):
                raise PolicyError("Perfil PNG não suportado ou dimensões divergentes.")
        elif kind == b"IDAT": compressed.extend(content)
        elif kind == b"IEND":
            if size or end + 4 != len(raw): raise PolicyError("Fim de PNG inválido.")
            ended = True
        cursor = end + 4
    if not header or not compressed or not ended: raise PolicyError("PNG incompleto.")
    width, height, _, color, *_ = header
    stride = width * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color] + 1
    expected = stride * height
    try:
        decompressor = zlib.decompressobj()
        pixels = decompressor.decompress(compressed, expected + 1)
        if (len(pixels) != expected or not decompressor.eof or decompressor.unused_data
                or decompressor.unconsumed_tail or any(pixels[row * stride] > 4 for row in range(height))):
            raise PolicyError("Pixels PNG truncados, excessivos ou filtros inválidos.")
    except zlib.error as exc:
        raise PolicyError("Compressão PNG corrompida.") from exc
