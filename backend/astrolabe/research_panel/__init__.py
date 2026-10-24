"""Isolated, nonproduction prospective panel development; no application startup hooks."""

from hashlib import sha256 as _sha256
from pathlib import Path as _Path

_PACKAGE_FILES = {
    path.name: _sha256(path.read_bytes()).hexdigest()
    for path in _Path(__file__).parent.glob("*.py")
}
