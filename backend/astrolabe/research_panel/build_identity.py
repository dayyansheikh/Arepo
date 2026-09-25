"""Pin source and panel code before measurement; never reinterpret a changed build."""

import hashlib
import sys
from pathlib import Path

from astrolabe.feature_store.build_identity import _codes, verified_build

from . import _PACKAGE_FILES


def verified_panel_build():
    source_build = verified_build()
    root = Path(__file__).parent
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.py')}
    if files != _PACKAGE_FILES:
        raise ValueError('panel measurement build changed on disk; start a new run')
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(__package__ + '.') or not getattr(module, '__file__', None):
            continue
        path = Path(module.__file__)
        if path.parent != root or path.name not in files:
            raise ValueError('unexpected panel module location')
        for qualname, expected in _codes(compile(
            path.read_bytes(), str(path), 'exec', dont_inherit=True,
        )).items():
            if '<' in qualname:
                continue
            obj = module
            try:
                for part in qualname.split('.'):
                    obj = getattr(obj, part)
            except AttributeError as exc:
                raise ValueError('loaded panel code is missing') from exc
            if isinstance(obj, type):
                continue
            if isinstance(obj, property):
                obj = obj.fget
            if getattr(obj, '__code__', None) != expected:
                raise ValueError('loaded panel code differs from source')
    return {'schema_version': 'fs2-panel-build-v1', 'files': files, 'source_build': source_build}
