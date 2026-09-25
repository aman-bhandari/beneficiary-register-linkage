"""Script-neutral names, dates and places, so that 'भगवती देवी बिष्ट' and 'BHAGAWATI BIST' can be compared.

Nothing here knows how the synthetic data was made. Devanagari is transliterated with a generic scheme, then
both scripts go through the same phonetic folding: aspiration dropped, long vowels shortened, v/w/b merged,
sh/s merged, doubled letters collapsed, anusvara read as n. Two keys come out of a name:

    fold      'bagavati bist'   a readable folded form, for Jaro-Winkler similarity
    skeleton  'bgvt'            consonants only, for blocking (cheap candidate generation)
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from functools import lru_cache

from indic_transliteration import sanscript

# words that carry no identity: honorifics, "late", and the Devi/Kumari suffix women's names may or may not carry
STOP = {"devi", "debi", "kumari", "kaur", "kour", "smt", "shri", "sri", "late", "swargiya", "mr", "mrs", "ms",
        "km", "dr", "sv", "sw", "w/o", "s/o", "d/o"}
# name prefixes: Mohd / Md / Mohammad come before the given name and are written or omitted at will
PREFIX = {"mohd", "md", "mo", "mohammad", "mohammed", "muhammad", "mohamad", "mohmmad", "mohamed"}
# community middle names: present in one register, absent in the next, so they are compared separately
MIDDLE = {"singh", "sinh", "chandra", "chandr", "chander", "chand", "chandro", "datt", "dutt", "dat", "ram", "lal",
          "prasad", "nath", "rani", "bala"}

_DEV = re.compile(r"[ऀ-ॿ]")


def to_roman(s) -> str:
    if not isinstance(s, str) or not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    if _DEV.search(s):
        s = s.replace("ं", "न्")       # anusvara -> explicit n + halant, read as n
        s = s.replace("ँ", "न्")       # chandrabindu likewise
        s = sanscript.transliterate(s, sanscript.DEVANAGARI, sanscript.IAST)
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


_FOLD = [("ksh", "x"), ("chh", "c"), ("ch", "c"), ("sh", "s"), ("ph", "f"), ("th", "t"), ("dh", "d"), ("bh", "b"),
         ("kh", "k"), ("gh", "g"), ("jh", "j"), ("w", "v"), ("v", "b"), ("z", "j"), ("q", "k"), ("x", "ks"),
         ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("ou", "o"), ("au", "o"), ("ai", "e"),
         ("y", "i")]


def fold_word(w: str) -> str:
    w = re.sub(r"[^a-z]", "", w)
    for a, b in _FOLD:
        w = w.replace(a, b)
    w = re.sub(r"(.)\1+", r"\1", w)                    # doubled letters
    w = re.sub(r"(?<=[bcdfgjklmnpqrstvx])h", "", w)    # stray aspiration
    if len(w) > 3 and w.endswith("a"):                 # final schwa: Surendra/Surendr, Kamla/Kamal-a, Aria/Ari
        w = w[:-1]
    return w


def skeleton_word(w: str) -> str:
    """Consonant skeleton: drop vowels after the first letter. 'bagavati' and 'bagvati' both give 'bgvt'."""
    if not w:
        return ""
    return w[0] + re.sub(r"[aeiou]", "", w[1:])


_STOP_F = {fold_word(x) for x in STOP}
_PREFIX_F = {fold_word(x) for x in PREFIX}
_MIDDLE_F = {fold_word(m) for m in MIDDLE}


@lru_cache(maxsize=None)
def split_name(s) -> dict:
    """-> {'first', 'middle', 'last', 'fold', 'skel_first', 'skel_last'} from any spelling in either script.
    The first word is the given name (after any Mohd/Md prefix), even if it is a word that elsewhere serves as a
    community middle name: 'Ram Singh Rana' is Ram, 'Kishan Ram Arya' is Kishan."""
    words = [fold_word(t) for t in re.split(r"[\s.\-,/]+", to_roman(s)) if t]
    words = [w for w in words if w and w not in _STOP_F]
    prefix = []
    while len(words) > 1 and words[0] in _PREFIX_F:
        words.pop(0)
        prefix = ["md"]                                   # one canonical form for Mohd / Md / मोहम्मद
    if not words:
        words, prefix = prefix, []
    first = words[0] if words else ""
    rest = words[1:]
    middle = prefix + [w for w in rest if w in _MIDDLE_F]
    core = [w for w in rest if w not in _MIDDLE_F]
    last = core[-1] if core else ""
    return dict(first=first, middle=" ".join(middle), last=last, fold=" ".join([first] + core).strip(),
                skel_first=skeleton_word(first), skel_last=skeleton_word(last))


def parse_date(s) -> date | None:
    if s is None or (isinstance(s, float)):
        return None
    m = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", str(s))
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d)
    except ValueError:
        return None


@lru_cache(maxsize=None)
def place_key(s) -> str:
    """Panchayat names re-typed by each department fold to one key."""
    if not isinstance(s, str):
        return ""
    r = to_roman(s)
    digits = "".join(re.findall(r"\d+", r))
    return fold_word(re.sub(r"\bward\b|\d+|\s", "", r)) + (f"w{digits}" if digits else "")
