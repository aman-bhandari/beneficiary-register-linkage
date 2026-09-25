"""Blinded identifiers for privacy-preserving linkage.

A department that must not hand over names can hand over a Bloom-filter encoding instead (Schnell's
cryptographic long-term key, CLK): the name's letter bigrams are hashed k times under a secret key into a
1,024-bit array. Two encodings of similar names share most set bits, so similarity survives (Dice coefficient);
the name itself cannot be read back without the key. Blocking keys are keyed hashes of the folded skeletons.

This is the documented way to link without exchanging names. It is not unbreakable: frequency attacks on
Bloom filters are published, so the key stays with the linkage unit and encodings are never published.
"""
from __future__ import annotations

import hashlib
import hmac
import os

import numpy as np

BITS = 1024
K = 20
KEY = os.environ.get("BLOOM_KEY", "demo-bloom-key-rotate-me").encode()


def _bigrams(s: str) -> list[str]:
    s = f"_{s}_"
    return [s[i:i + 2] for i in range(len(s) - 1)]


def encode(first: str | None, last: str | None, rel: str | None, birth_year) -> bytes:
    """One CLK per record: first-name, surname and relation-name bigrams (field-tagged) and birth year."""
    bits = np.zeros(BITS, dtype=np.uint8)
    feats = []
    for tag, v in (("f", first), ("l", last), ("r", rel)):
        if v:
            feats += [f"{tag}:{g}" for g in _bigrams(v)]
    if birth_year is not None and birth_year == birth_year:
        feats.append(f"y:{int(birth_year)}")
        feats.append(f"d:{int(birth_year) // 5}")
    for f in feats:
        h1 = int.from_bytes(hmac.new(KEY, b"1" + f.encode(), hashlib.sha256).digest()[:8], "big")
        h2 = int.from_bytes(hmac.new(KEY, b"2" + f.encode(), hashlib.sha256).digest()[:8], "big")
        for i in range(K):                                      # double hashing
            bits[(h1 + i * h2) % BITS] = 1
    return np.packbits(bits).tobytes()


def dice(a: bytes, b: bytes) -> float:
    x = np.frombuffer(a, dtype=np.uint8)
    y = np.frombuffer(b, dtype=np.uint8)
    inter = int(np.unpackbits(x & y).sum())
    tot = int(np.unpackbits(x).sum() + np.unpackbits(y).sum())
    return 2 * inter / tot if tot else 0.0


def blind_key(v: str | None) -> str | None:
    return hmac.new(KEY, v.encode(), hashlib.sha256).hexdigest()[:16] if v else None
