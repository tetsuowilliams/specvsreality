"""SHA-1 hashing helper used to derive ``content_hash`` for requirement versions."""

from __future__ import annotations

import hashlib


class HashUtil:
    """Stateless SHA-1 hasher.

    A class rather than a free function so it can be injected and replaced in
    tests without monkeypatching module-level helpers.
    """

    def sha1_hex(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
