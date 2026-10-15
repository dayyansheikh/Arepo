"""Bind a measurement run to unchanged files and their actually loaded Python code."""

import hashlib
import importlib.metadata
import sys
import threading
from collections import OrderedDict
from pathlib import Path
from types import CodeType

from . import _PACKAGE_FILES


def _codes(code):
    result = {code.co_qualname: code}
    for value in code.co_consts:
        if isinstance(value, CodeType):
            result.update(_codes(value))
    return result


# Cache only immutable expectations, never a verification result. File bytes and loaded
# function identities are checked on every call. No mtime-only or root-only trust shortcut.
_COMPILED_LIMIT = 256
_COMPILED = OrderedDict()
_COMPILED_LOCK = threading.Lock()


def _compiled_codes(source, filename):
    key = (source, filename)
    with _COMPILED_LOCK:
        if key not in _COMPILED:
            codes = tuple(_codes(compile(source, filename, 'exec', dont_inherit=True)).items())
            _COMPILED[key] = codes
            if len(_COMPILED) > _COMPILED_LIMIT:
                _COMPILED.popitem(last=False)
        _COMPILED.move_to_end(key)
        return _COMPILED[key]


def verified_build():
    root = Path(__file__).parent
    current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.py")}
    if current != _PACKAGE_FILES:
        raise ValueError("measurement build changed on disk; restart with a new source run")
    prefix = __package__ + "."
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(prefix) or not getattr(module, "__file__", None):
            continue
        path = Path(module.__file__)
        if path.parent != root or path.name not in current:
            raise ValueError("unexpected measurement module location")
        codes = _compiled_codes(path.read_bytes(), str(path))
        for qualname, expected in codes:
            if "<" in qualname:
                continue  # nested code is part of its parent code's digest
            obj = module
            try:
                for part in qualname.split("."):
                    obj = getattr(obj, part)
                if isinstance(obj, property):
                    obj = obj.fget
                actual = getattr(obj, "__code__", None)
                # Class bodies are not callable code; their methods are checked separately.
                if isinstance(obj, type):
                    continue
                if actual is None or actual != expected:
                    raise ValueError(
                        f"loaded measurement code differs from source: {name}.{qualname}"
                    )
            except AttributeError as exc:
                raise ValueError("loaded measurement code is missing") from exc
    return {
        "schema_version": "fs2-build-v1", "files": current,
        "python": sys.version,
        "libraries": {name: importlib.metadata.version(name)
                      for name in ("httpx", "SQLAlchemy", "aiosqlite", "asyncpg")},
    }
