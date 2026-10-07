"""Original CPU matrix-block adapter for F32/BF16 matrices. NOT a full Safetensors validator, nor Qwen/Nemotron forward, GPU runtime, or training. Caller must reserve decoded matrix memory. Files are immutable operator-owned."""
import hashlib,json,math,struct
from .weight_store import WeightStore,WeightBlock,file_info,signature
from ..foundation.models import child
from ..errors import PolicyError
def read_header(path):
    with path.open('rb') as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise PolicyError('Cabeçalho Safetensors inválido.')
        size = struct.unpack('<Q', prefix)[0]
        if not (0 < size <= 2000000) or 8 + size > path.stat().st_size:
            raise PolicyError('Cabeçalho Safetensors inválido.')
        raw = stream.read(size)
        if len(raw) != size:
            raise PolicyError('Cabeçalho Safetensors inválido.')
        try:
            header = json.loads(raw.decode('utf-8'))
        except (UnicodeError, ValueError) as exc:
            raise PolicyError('Cabeçalho Safetensors inválido.') from exc
        if not isinstance(header, dict):
            raise PolicyError('Cabeçalho Safetensors inválido.')
    return header, 8 + size

def selected_blocks(path, header, offset, names, max_block_bytes):
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or n == '' for n in names) or len(names) != len(set(names)):
        raise PolicyError("Invalid names: must be a non-empty list of unique non-empty strings")
    if not isinstance(max_block_bytes, int) or isinstance(max_block_bytes, bool) or max_block_bytes <= 0:
        raise PolicyError("max_block_bytes must be a positive integer")

    blocks = {}
    metadata = {}
    intervals = []
    try:
        with path.open('rb') as stream:
            for name in names:
                entry = header.get(name)
                if not isinstance(entry, dict):
                    raise PolicyError(f"Missing or invalid entry for name: {name}")
                dtype = entry.get('dtype')
                if dtype not in ('F32', 'BF16'):
                    raise PolicyError(f"Unsupported dtype: {dtype} for name: {name}")
                shape = entry.get('shape')
                if not isinstance(shape, list) or len(shape) != 2 or not all(type(s) is int and s > 0 for s in shape):
                    raise PolicyError(f"Invalid shape: {shape} for name: {name}")
                data_offsets = entry.get('data_offsets')
                if not isinstance(data_offsets, list) or len(data_offsets) != 2 or not all(type(o) is int and o >= 0 for o in data_offsets):
                    raise PolicyError(f"Invalid data_offsets: {data_offsets} for name: {name}")
                start, end = data_offsets
                if start >= end or start < 0:
                    raise PolicyError(f"Invalid data_offsets range: {data_offsets} for name: {name}")

                length = math.prod(shape) * (4 if dtype == 'F32' else 2)
                if length != (end - start):
                    raise PolicyError(f"Length mismatch for {name}: expected {length}, got {end - start}")
                if length > max_block_bytes:
                    raise PolicyError(f"Block size exceeds max_block_bytes for {name}")
                file_size = path.stat().st_size
                if offset + end > file_size:
                    raise PolicyError(f"Data offset exceeds file size for {name}")

                for a, b in intervals:
                    if start < b and a < end:
                        raise PolicyError(f"Overlap detected with existing interval for {name}")

                stream.seek(offset + start)
                raw = stream.read(length)
                if len(raw) != length:
                    raise PolicyError(f"Failed to read full block for {name}")

                blocks[name] = WeightBlock('model.safetensors', offset + start, length, hashlib.sha256(raw).hexdigest())
                metadata[name] = {'dtype': dtype, 'shape': shape}
                intervals.append((start, end))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"Error processing block: {str(exc)}") from exc
    return blocks, metadata

def build_matrix_store(spec, names, *, cache_bytes, max_block_bytes):
    path = child(spec.directory, 'model.safetensors')
    before = signature(file_info(path))
    spec.verify()
    header, offset = read_header(path)
    blocks, metadata = selected_blocks(path, header, offset, names, max_block_bytes)
    if signature(file_info(path)) != before:
        raise PolicyError('Pesos mudaram durante o inventário.')
    store = WeightStore(spec.directory, blocks, cache_bytes=cache_bytes, max_block_bytes=max_block_bytes)
    return store, metadata

def decode_matrix(store, metadata, name, cancel=None):
    import numpy as np
    if name not in metadata:
        raise PolicyError
    raw = store.get(name, cancel)
    dtype = metadata[name]['dtype']
    shape = metadata[name]['shape']
    if dtype == 'F32':
        matrix = np.frombuffer(raw, dtype='<f4').reshape(shape)
    else:
        matrix = np.frombuffer(raw, dtype='<u2').astype('<u4') << 16
        matrix = matrix.view('<f4').reshape(shape)
    if not np.isfinite(matrix).all():
        raise PolicyError
    return matrix
