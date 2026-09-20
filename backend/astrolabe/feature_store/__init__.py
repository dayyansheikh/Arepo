"""Isolated AREPO v2 research storage; never imported by v1 startup/migrations."""

# Freeze source files before submodules load. A long-running capture must refuse edits
# instead of hashing new files while executing old code. Not an owner-tamper security seal.
from hashlib import sha256 as _sha256
from pathlib import Path as _Path

_PACKAGE_FILES = {
    path.name: _sha256(path.read_bytes()).hexdigest()
    for path in _Path(__file__).parent.glob("*.py")
}
