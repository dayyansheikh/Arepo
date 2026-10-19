# ruff: noqa: E501
"""CB14-S: intra-speech hazard decay for mention baskets (docs/research_lab/CREATIVE_BATCH_14.md CB14-S, sections 1.1-1.4, 2.1-2.8, 5, 9-10). Rules part ``S``.

EXPLORATORY ("L1, hindsight start time"; Stage 2 "L2"). No edge, calibration or profitability claim. This module imports ``cb14_common`` (and the CB12-M sports registry / regex, pinned by
sha256 below) and nothing from ``cb14_w`` / ``cb14_smoke``, so its rules hash is independent of every other family.

Hash rule: part S hashes the functions / classes and the UPPER_CASE JSON-able constants defined HERE plus ``cb14_common``. Every frozen rule (windows, regexes, thresholds, floors, seeds,
checkpoints, gates, loadings, column lists, status tokens) is a module-level UPPER_CASE constant or a module-level function. Non-rule machinery lives inside functions.

Data layout under ``<hist_root>/h14_speech`` (``FRAME_RUN``):

  frame.csv.gz, members.csv.gz, map.csv.gz, records.csv.gz, frame_report.json   q0312 (no price, print, transcript text or outcome; ``manifest.json``)
  fit/records.csv.gz, fit/offsets.csv.gz, fit/manifest.json                      q0313 (fit transcripts reduced at parse: per-term first-mention offsets, last offset; no text)
  prices_{p,n}.csv.gz, tx_{p,n}.csv.gz, markets_{p,n}.csv.gz, manifest_{p,n}.json q0317 / q0318 (1-minute prices-history; prints aggregated to transactions; no hash, side, wallet)
  guarded_{p,n,s2}/transcripts.csv.gz, mentions.csv.gz                           target transcripts reduced (outcome-bearing: read only through ``CausalTranscript``)
  guarded_{p,n,s2}/outcomes_guarded_{p,n,s2}.csv.gz                              Gamma outcomes (opened only by ``screen`` / ``rep``)
  stage2/{frame,members,map,markets,prices,tx}.csv.gz, manifest_s2.json         q0321 (post-freeze events; same schema as the P / N files)
  <out_root>/s_model.json, s_model_rebased.json, s_map_audit_sample.csv          the frozen position model (q0314) and the blind GS0 sample
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import html as htmllib
import json
import math
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
from scipy.stats import norm

from . import cb8_common as cm
from . import cb12_m as m12
from . import cb14_common as c14
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

# =====================================================================================================================================================
# Frozen constants
# =====================================================================================================================================================
HOUR = 3600.0
DAY = 86400.0
TAG_ID = 100343
FRAME_RUN = "h14_speech"
FIT_RUN = "h14_speech/fit"
LABEL_S = "L1, hindsight start time"
LABEL_S2 = "L2, out-of-time post-freeze events"
# status tokens (the queue drafts' until_log_regex matches `"status": "<token>"`)
FRAME_STATUS = "s_frame_complete"
FIT_FETCH_STATUS = "s_fit_fetch_complete"
FIT_STATUS = "s_fit_complete"
DATA_STATUS_P = "s_data_P_complete"
DATA_STATUS_N = "s_data_N_complete"
STAGE2_STATUS_CLOSED = "s_stage2_window_closed"
STAGE2_STATUS_OPEN = "s_stage2_collecting"
STAGE2_STATUS_FINAL = "s_stage2_outcomes_final"  # the post-close outcome wait is over: q0322 may analyse
IN_PROGRESS = "in_progress"
# dates (UTC; the three windows are keyed on the event ``endDate``)
T14_P = ("2024-11-01", "2025-06-01")
T14_N = ("2025-06-01", "2026-03-01")
T14_HOLDOUT = ("2026-03-01", "2026-10-27")  # CB12-M's HOLDOUT calendar: never fetched, opened or analysed
T14_FIT = ("2023-01-01", "2024-11-01")
T14_S2_FLOOR = "2026-10-27T00:00:00Z"
T14_S2_CAP = "2027-02-28T00:00:00Z"
P_MONTHS = ("2024-11", "2024-12", "2025-01", "2025-02", "2025-03", "2025-04", "2025-05")
SUBSETS = ("P", "N")
# population rules
MIN_MEMBERS = 8
OCCASION_MAX_S = 36 * HOUR
PRIMARY_MIN_FIT = 40  # speakers with >= 40 timestamped Factbase transcripts dated in the fit window
TIMESTAMPED_MIN_STAMPS = 20  # a parsed transcript is "timestamped" with at least this many distinct segment stamps
SMOKE_MIN_STAMPS = 100
FETCH_BEFORE_S = 30 * 60
FETCH_AFTER_S = 5 * 3600
FIDELITY = 1
GS0_N = 120
GS0_SEED = c14.SEED_GS0
GS0_MIN_PRECISION = 0.90
FACTBASE_BASE = "https://rollcall.com"
FACTBASE_SEARCH = "https://rollcall.com/wp-json/factbase/v1/search"
FACTBASE_MAX_PAGES = 300
FACTBASE_SEGMENT_TEXT_CAP = 5000
SPEAKER_KEYWORDS = (("trump", "trump"), ("biden", "biden"), ("harris", "harris"), ("vance", "vance"), ("powell", "powell"), ("leavitt", "leavitt"), ("musk", "musk"), ("obama", "obama"),
                    ("walz", "walz"), ("newsom", "newsom"))  # (keyword in an event title or a Factbase speaker id, speaker key); first match, several distinct -> no speaker
TYPE_RULES = (("press conference", ("Press Conference",)), ("press briefing", ("Press Briefing",)), ("briefing", ("Press Briefing",)), ("gaggle", ("Press Gaggle",)),
              ("interview", ("Interview",)), ("vlog", ("Vlog",)), ("remarks", ("Remarks",)), ("rally", ("Speech",)), ("speech", ("Speech",)), ("address", ("Speech",)),
              ("inauguration", ("Speech",)), ("joint session", ("Speech",)), ("convention", ("Speech",)))  # event-title keyword (first match) -> Factbase record types
TYPE_CLASS = {"Speech": "prepared", "Remarks": "prepared", "Vlog": "prepared", "Press Conference": "press", "Press Briefing": "press", "Press Gaggle": "press", "Interview": "press"}
TYPE_STOPWORDS = ("will", "what", "say", "says", "during", "the", "a", "an", "of", "at", "in", "on", "to", "and", "by", "with", "for", "his", "her", "mention", "word", "words", "speech", "remarks")
# term parser and rule booleans (a member's market question / description)
TERM_QUOTE_RE = re.compile(r"[\"“”]([^\"“”]{1,80})[\"“”]")
TERM_MAX_TOKENS = 6
QA_EXCLUDED_RE = re.compile(r"(?i)(?:exclud\w*|not (?:includ\w*|count\w*)|won'?t count|will not count|does not count|do not count)[^.;]{0,80}(?:q\s*&\s*a|q\s*and\s*a|question(?:s| and answer)|press conference|interview)"
                            r"|(?:q\s*&\s*a|q\s*and\s*a|question(?:s| and answer)\w*)[^.;]{0,40}(?:will not count|does not count|not (?:included|counted)|excluded)")
SECTION_EXCLUDED_RE = re.compile(r"(?i)(?:only|solely|just)[^.;]{0,40}(?:prepared remarks|opening remarks|introduction|first \d+ minutes|speech portion)"
                                 r"|(?:exclud\w*|not (?:includ\w*|count\w*))[^.;]{0,60}(?:introduction|opening remarks|remarks by (?:others|other speakers)|other speakers|guest|moderator|audience)")
QA_INCLUDED_RE = re.compile(r"(?i)(?:includ\w*|count\w*)[^.;]{0,60}(?:q\s*&\s*a|q\s*and\s*a|question)")
PLURAL_NO_RE = re.compile(r"(?i)plurals?\b[^.;]{0,60}(?:not|won'?t|no)\b[^.;]{0,20}(?:count|be counted|included)|\b(?:no|not)\s+plurals?\b")
PLURAL_YES_RE = re.compile(r"(?i)plurals?\b[^.;]{0,60}(?:count|counted|included|accepted)")
POSSESSIVE_NO_RE = re.compile(r"(?i)possessives?\b[^.;]{0,60}(?:not|won'?t|no)\b[^.;]{0,20}(?:count|be counted|included)|\b(?:no|not)\s+possessives?\b")
POSSESSIVE_YES_RE = re.compile(r"(?i)possessives?\b[^.;]{0,60}(?:count|counted|included|accepted)")
COMPOUND_NO_RE = re.compile(r"(?i)(?:compound|hyphenated)[^.;]{0,60}(?:not|won'?t|no)\b|\b(?:no|not)\s+(?:compound|hyphenated)")
COMPOUND_YES_RE = re.compile(r"(?i)(?:compound|hyphenated)[^.;]{0,60}(?:count|counted|included|accepted)")
DEFAULT_PLURAL = True  # a rule that is silent on a form: plural and possessive count, compounds do not (declared)
DEFAULT_POSSESSIVE = True
DEFAULT_COMPOUND = False
# transcript parsing / matching
STAMP_RE = re.compile(r"(?<!\d)(\d{1,2}):([0-5]\d):([0-5]\d)(?!\d)")
SCRIPT_RE = re.compile(r"(?is)<(script|style|noscript)\b.*?</\1>")
TAG_RE = re.compile(r"(?s)<[^>]*>")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
# prices (section 2.2) and units
POINT_LAG_S = 60  # a fidelity-1 point is usable from stamp + 60 s
P_T_MAX_AGE_S = 300
P_LAG_BACK_S = 180
P_LAG_MAX_AGE_S = 1800
P15_BACK_S = 900
RISING_WINDOW_S = 300
RISING_MIN = 0.15
P_MIN = 0.03
P_MAX = 0.97
CHECKPOINT_S = 300
CHECKPOINT_ALT_S = 600
MIN_E_S = 600
ROBUST_E_S = 1200
S2_MIN_E_S = 1800
SHIFT_S = 120
LATE_START_S = 90 * 60
# alignment (causal; round 1 item 4)
ANCHOR_HI = 0.85
ANCHOR_LO = 0.60
ANCHOR_BACK_S = 180
ANCHOR_BACK_MAX_AGE_S = 600
ANCHOR_LAG_S = 60
ANCHOR_WITHIN_S = 300
ANCHOR_MIN = 2
ALIGN_MAX_ITER = 10
PI_BACK_S = 300
# position model
MODEL_GRID_MIN = 180
SHRINK = 10
SHRINK_ALT = (5, 20)
MODEL_VERSION = "cb14-s-model-v1"
MODEL_FILE = "s_model.json"
MODEL_REBASED_FILE = "s_model_rebased.json"
# The position-model pins live OUTSIDE the part-S rules hash (section 11 fix F10; design section 1.4 puts the pin in the freeze spec): a committed, write-once pin file that the coordinator
# writes after q0314 and before any S price, print or target transcript is read. q0317 / q0318 / q0321 / the screen / the rep refuse while it is missing, uncommitted or differs from the
# model files; the S freeze entry (model_specs/cb14_v1.json, part S) must carry the same two sha256. Pinning therefore never changes the part-S rules sha (the N timing rule of 1.3).
MODEL_PIN_REL = "docs/research_lab/seals/cb14_s_model_pin.json"
MODEL_PIN_VERSION = "cb14-s-model-pin-v1"
S_SPORTS_REGISTRY_FILE_SHA256 = "b47b3d20c0bbf71a4e0dc912b0a32533fcd7e796e2c289a4b525774c8857bce6"  # evidence_cb12/sports_tag_registry_20261018.json
S_SPORTS_IDS_SHA256 = "9485fe3595c9bf0db16ace97c60ca68eca9fdef0ef69f2883f3a313b85c76227"  # sha256 of json (compact) of the sorted CB12-M SPORTS_TAG_IDS
S_SPORTS_SLUGS_SHA256 = "95edfe3c9dc42e788bf18ef4613a9689c32d0f2d1ee0941acfb5bd33921b70dd"  # ... of the CB12-M SPORTS_TAG_SLUGS tuple
S_BROADCAST_RE_SHA256 = "61b45196fef836799064a6277c9bcca9316a7c240e21bfb291c6b25557d6b8c0"  # sha256 of the UTF-8 pattern string of CB12-M's BROADCAST_RE
SPORTS_REGISTRY_REL = "docs/research_lab/evidence_cb12/sports_tag_registry_20261018.json"
# tests
S1_FLOOR = 0.30
S2_FLOOR = 0.01
JOINT_HALF = 0.5
JOINT_P = 0.05
SHIFT_P = 0.05
ASK_OFFSET_P = 0.01
ASK_OFFSET_Q = 0.02
ASK_OFFSET_P_ROBUST = 0.005
ASK_OFFSET_Q_ROBUST = 0.01
TRADE_THROUGH = 0.01
TRADE_THROUGH_ROBUST = 0.02
FILL_WINDOW_S = 300
FILL_CAP = 100.0
SIGNFLIP_DRAWS = c14.PLACEBO_DRAWS
GSP_LOADINGS = (0.15, 0.25, 0.15, 0.45)  # week, event, term, idiosyncratic (variances; sum 1)
MDE_S1_MAX = 0.60
MDE_S2_MAX = 0.02  # 2.0 cents
GS_MIN = {"events": 100, "weeks": 30, "words": 1000, "align_share": 0.60}
GSC_MIN = {"events": 100, "weeks": 30, "p_events": 25}
REP_MIN_EVENTS = 100
REP_CAP_MIN_EVENTS = 60
S2_STOP_EVENTS = 100  # T14_S2_end (section 1.2): Stage-2 collection closes at the cap or once this many Stage-2 events with a mapped transcript and >= 1 aligned unit have RESOLVED (every
# member resolved on Gamma; counted from resolution flags, never from outcome values)
# Post-close outcome wait (review of 515d68d, F13): the window closes on a count of resolutions, so the latest events are unresolved by construction. After the closing pass NO event is
# added; every member whose last lookup was unresolved is looked up again at most once a day until closed_at + S2_OUTCOME_WAIT_D (a fixed, pre-declared wait: mention markets normally
# resolve within 1-2 days of the event, a UMA dispute round adds about 2-4 days, so 14 days cover two dispute rounds); the first pass at or after that time is final
# (``STAGE2_STATUS_FINAL``) and only then does q0322 analyse. A word still unresolved at the final lookup follows the design rule (scored 0.5 with the binding worst case at 1; counted).
S2_OUTCOME_WAIT_D = 14
S2_POST_CLOSE_EVERY_S = DAY
S2_PASS_EVERY_S = 7 * DAY  # q0321 is weekly: a pass starts at most once per 7 days (idle exit 75 between, an idle heartbeat exit 0 at least every 10 h; CB8 q0162 pattern)
# availability rule on the P months (smoke; section 11 fix F12, declared engineering gate, outcome-blind): the design's 3 events x 2 members per month over 7 months (7 lookups + 42 price
# reads) cannot fit the smoke's 30 requests, so ONE out-of-frame event x 2 members per month (7 + 14 = 21 requests) and a month is usable iff BOTH members return rows (the design's
# ">= 4 of 6" share, 2/3, rounded up to 2 of 2: stricter); a month with no out-of-frame event found is not usable; P keeps only usable months (the smoke criterion: >= 1 usable month)
AVAIL_EVENTS_PER_MONTH = 1
AVAIL_MEMBERS_PER_EVENT = 2
AVAIL_MIN_FRACTION = 4.0 / 6.0
AVAIL_WINDOW_S = 2 * 3600
AVAIL_MIN_MONTHS = 1
SMOKE_TAG_WEEK = ("2024-10-07T00:00:00Z", "2024-10-14T00:00:00Z")
SMOKE_NEEDS = ("s_guards_fixture", "s_pins", "s_causal_accessor", "s_alignment_fixture", "s_tag_walk", "s_factbase_transcript", "s_term_matcher", "s_availability_p_months")
# output columns (no side / wallet / hash / user / comment / outcome column outside a guarded file; ``assert_clean_columns`` is applied to every header)
EVENT_COLUMNS = ["event_id", "series_id", "title", "start_epoch", "end_epoch", "created_epoch", "neg_risk", "n_members", "subset", "status", "status_source", "sports_tag", "sports_re", "occasion",
                 "speaker_key", "type_keys", "qa_excluded", "section_excluded", "n_term_fail", "week", "month", "title_sha256", "key_series_cf"]
MEMBER_COLUMNS = ["event_id", "market_id", "condition_id", "token_yes", "yes_index", "created_epoch", "term_raw", "term_norm", "variants", "plural", "possessive", "compound", "desc_sha256",
                  "neg_risk_market_id", "fee_rate"]
MAP_COLUMNS = ["event_id", "subset", "speaker_key", "type_keys", "status", "reason", "n_candidates", "record_id", "record_url", "record_date", "record_type", "record_title"]
RECORD_COLUMNS = ["record_id", "date", "date_epoch", "type", "speaker_id", "speaker_key", "title", "url"]
FIT_RECORD_COLUMNS = ["record_id", "speaker_key", "type", "type_class", "date", "status", "n_stamps", "last_s", "base_s", "first_seg_s", "last_rebased_s", "timestamped"]
FIT_OFFSET_COLUMNS = ["record_id", "term", "first_s", "first_rebased_s"]
TRANSCRIPT_COLUMNS = ["event_id", "record_url", "status", "n_stamps", "last_s", "base_s", "first_seg_s"]
MENTION_COLUMNS = ["event_id", "market_id", "first_s"]
PRICE_COLUMNS = ["market_id", "ts", "p"]
TX_COLUMNS = ["market_id", "ts", "price", "size", "n_fills"]
MARKET_COLUMNS = ["market_id", "event_id", "status", "n_points", "n_prints", "n_tx", "oldest_ts", "truncated"]
OUTCOME_COLUMNS = ["market_id", "event_id", "yes_index", "outcome_prices", "uma_status"]
AUDIT_COLUMNS = ["event_id", "event_title", "start_utc", "record_title", "record_date", "record_type"]
UNAVAILABLE_NETWORK = "unavailable (network)"
UNAVAILABLE_SOURCE = "unavailable (source)"
FRAME_OUTPUT_CAP_GB = 0.005
FIT_OUTPUT_CAP_GB = 0.05
DATA_OUTPUT_CAP_GB = {"P": 0.05, "N": 0.15, "S2": 0.05}
MAX_ITEM_ATTEMPTS = cm.MAX_ITEM_ATTEMPTS
GAMMA_LOOKUP_PER_REQUEST = 50


# =====================================================================================================================================================
# Small helpers, windows, pins
# =====================================================================================================================================================


def _ep(d: str) -> float:
    return c14.ep(d if "T" in d else d + "T00:00:00Z")


def window_of(end_epoch: float) -> str | None:
    """'P' / 'N' (event ``endDate`` windows), 'HOLDOUT' (CB12-M's HOLDOUT calendar, never touched) or None (outside every CB14 S window)."""
    if not math.isfinite(end_epoch):
        return None
    for name, w in (("P", T14_P), ("N", T14_N), ("HOLDOUT", T14_HOLDOUT)):
        if _ep(w[0]) <= end_epoch < _ep(w[1]):
            return name
    return None


def guard_window(end_epoch: float, what: str = "event") -> str:
    """Refuse any ``what`` whose end falls in the HOLDOUT window (or outside P and N)."""
    w = window_of(end_epoch)
    if w == "HOLDOUT":
        raise Refused(f"{what} ends in CB12-M's HOLDOUT window [{T14_HOLDOUT[0]}, {T14_HOLDOUT[1]}): CB14-S never fetches, opens or analyses it")
    if w is None:
        raise Refused(f"{what} ends outside the S windows P and N")
    return w


def _sha_list(items) -> str:
    return hashlib.sha256(json.dumps(list(items), separators=(",", ":")).encode()).hexdigest()


def verify_pins(registry_path: Path | None = None) -> dict:
    """Refuse (exit 2) unless CB12-M's sports registry (tag ids and slugs) and broadcast regex are the ones pinned by sha256 in part S; when the registry file is readable its file sha256
    and its tag list are checked too."""
    got = {"ids": _sha_list(sorted(m12.SPORTS_TAG_IDS)), "slugs": _sha_list(m12.SPORTS_TAG_SLUGS), "regex": hashlib.sha256(m12.BROADCAST_RE.pattern.encode("utf-8")).hexdigest()}
    want = {"ids": S_SPORTS_IDS_SHA256, "slugs": S_SPORTS_SLUGS_SHA256, "regex": S_BROADCAST_RE_SHA256}
    bad = [k for k in want if got[k] != want[k]]
    if bad:
        raise Refused(f"CB12-M sports registry / regex differ from the sha256 pinned in part S: {bad}")
    reg = Path(registry_path) if registry_path is not None else c14.provenance.REPO_ROOT / SPORTS_REGISTRY_REL
    file_checked = False
    if reg.exists():
        raw = reg.read_bytes()
        if hashlib.sha256(raw).hexdigest() != S_SPORTS_REGISTRY_FILE_SHA256:
            raise Refused(f"sports registry file {reg} sha256 differs from the pin in part S")
        if sorted(json.loads(raw)["tag_ids"]) != sorted(m12.SPORTS_TAG_IDS):
            raise Refused("the registry file's tag ids differ from CB12-M's SPORTS_TAG_IDS")
        file_checked = True
    return {"pins_ok": True, "registry_file_checked": file_checked, **got}


def is_sports_s(tags: Iterable[dict], title: str) -> tuple[bool, bool]:
    """(by tag, by broadcast regex): CB12-M's frozen registry, slug list and regex (pinned by ``verify_pins``)."""
    by_tag = any(str(t.get("id")) in m12.SPORTS_TAG_IDS or str(t.get("slug") or "").lower() in m12.SPORTS_TAG_SLUGS for t in tags if isinstance(t, dict))
    return by_tag, bool(m12.BROADCAST_RE.search(title or ""))


def model_pins(path: Path | None = None, *, require_committed: bool = True) -> dict[str, str]:
    """The committed position-model pins ``{"model", "model_rebased"}`` from ``MODEL_PIN_REL`` (outside the rules hash). Missing, uncommitted, foreign-version or unset -> refusal."""
    p = Path(path) if path is not None else c14.provenance.REPO_ROOT / MODEL_PIN_REL
    if not p.is_file():
        raise Refused(f"the position-model pin file {p.name} is missing (pins unset, {c14.PIN_UNSET}): the coordinator writes and commits it after q0314, before any S price, print or target transcript is read")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"the position-model pin file {p} is not committed (or differs from HEAD)")
    doc = json.loads(p.read_text())
    if doc.get("version") != MODEL_PIN_VERSION:
        raise Refused(f"pin file version {doc.get('version')!r} != {MODEL_PIN_VERSION!r}")
    out = {"model": str(doc.get("s_model_sha256") or ""), "model_rebased": str(doc.get("s_model_rebased_sha256") or "")}
    if any(not re.fullmatch(r"[0-9a-f]{64}", v) for v in out.values()):
        raise Refused(f"the position-model pin file {p.name} has an unset or malformed sha256")
    return out


def check_model_pin(model_path: Path, pin: str | None = None, *, what: str = "position model") -> str:
    """The sha256 of a model file must equal its pin (``pin`` given by the caller from the committed pin file; ``None`` reads that file; unset -> refuse; mismatch -> refuse)."""
    if pin is None:
        pin = model_pins()["model_rebased" if "re-based" in what else "model"]
    if not pin or pin == c14.PIN_UNSET:
        raise Refused(f"the sha256 pin of the {what} is unset ({c14.PIN_UNSET}); the coordinator pins it after q0314 (seals/cb14_s_model_pin.json), before any S price, print or target transcript is read")
    p = Path(model_path)
    if not p.exists():
        raise Refused(f"{what} file {p} not found")
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != pin:
        raise Refused(f"{what} {p.name} sha256 {got} != the pin in part S {pin}")
    return got


# =====================================================================================================================================================
# Term parser, rule booleans, frozen normaliser and matcher
# =====================================================================================================================================================


def normalise_text(s) -> str:
    """Frozen normaliser: NFKD without accents, lower case, curly apostrophes to ``'``, dashes / slashes / underscores to spaces (a plain hyphen between letters is kept)."""
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = t.replace("’", "'").replace("‘", "'").replace("ʼ", "'").replace("`", "'").replace("‑", "-")
    return re.sub(r"[–—−_/]", " ", t)


def tokenize(s) -> list[str]:
    return TOKEN_RE.findall(normalise_text(s))


def singular(tok: str) -> str:
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith(("ses", "xes", "zes", "ches", "shes")):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
        return tok[:-1]
    return tok


def normalise_term(raw) -> str:
    """The market's term after the frozen normaliser (the cluster key and the model key): tokens, last token singular ("tariff" / "tariffs" -> ``tariff``)."""
    toks = tokenize(raw)
    if not toks:
        return ""
    toks[-1] = singular(toks[-1])
    return " ".join(toks)


def plural_forms(base: str) -> set[str]:
    out = {base + "s", base + "es"}
    if len(base) > 2 and base.endswith("y") and base[-2] not in "aeiou":
        out.add(base[:-1] + "ies")
    return out


def token_forms(tok: str, plural: bool, possessive: bool) -> set[str]:
    core = {tok}
    if plural:
        b = singular(tok)
        core |= {tok, b} | plural_forms(b)
    if possessive:
        core |= {f + "'s" for f in core}
    return core


def parse_term(question, group_title=None) -> dict | None:
    """The market's term from the question (a quoted word or phrase; ``/`` separates alternatives that all count) or, failing that, the group title. None = parse failure (counted)."""
    raw = None
    m = TERM_QUOTE_RE.search(str(question or ""))
    if m:
        raw = m.group(1)
    elif group_title:
        raw = str(group_title)
    if not raw or not raw.strip():
        return None
    variants = []
    for v in re.split(r"\s*/\s*", raw.strip()):
        toks = tokenize(v)
        if toks and len(toks) <= TERM_MAX_TOKENS and toks not in variants:
            variants.append(toks)
    if not variants:
        return None
    return {"raw": raw.strip(), "variants": [" ".join(v) for v in variants], "norm": normalise_term(" ".join(variants[0]))}


def rule_flags(description) -> dict:
    """Rule booleans of a market description: Q&A excluded / section excluded (the event is dropped, counted), Q&A included, and the plural / possessive / compound forms (silent -> the
    declared defaults; a 'no' beats a 'yes')."""
    d = str(description or "")
    qa_ex = bool(QA_EXCLUDED_RE.search(d))
    return {"qa_excluded": qa_ex, "section_excluded": bool(SECTION_EXCLUDED_RE.search(d)), "qa_included": bool(QA_INCLUDED_RE.search(d)) and not qa_ex,
            "plural": False if PLURAL_NO_RE.search(d) else (True if PLURAL_YES_RE.search(d) else DEFAULT_PLURAL),
            "possessive": False if POSSESSIVE_NO_RE.search(d) else (True if POSSESSIVE_YES_RE.search(d) else DEFAULT_POSSESSIVE),
            "compound": False if COMPOUND_NO_RE.search(d) else (True if COMPOUND_YES_RE.search(d) else DEFAULT_COMPOUND)}


def make_matcher(variants: Iterable[str], plural: bool = DEFAULT_PLURAL, possessive: bool = DEFAULT_POSSESSIVE, compound: bool = DEFAULT_COMPOUND) -> dict:
    """A matcher: phrase token lists (alternatives) with the rule booleans. Plural / possessive forms apply to the last token of a phrase; ``compound`` also matches a hyphen part."""
    phrases = []
    for v in variants:
        toks = tokenize(v)
        if toks and toks not in phrases:
            phrases.append(toks)
    return {"phrases": phrases, "plural": bool(plural), "possessive": bool(possessive), "compound": bool(compound)}


def index_segments(segments: list[tuple[int, str]]) -> dict:
    """Token index of a transcript (in memory only): the first offset of every token and of every hyphen part, and the segments each token occurs in."""
    inf = float("inf")
    seg_tokens: list[list[str]] = []
    tok_first: dict[str, float] = {}
    part_first: dict[str, float] = {}
    tok_segs: dict[str, list[int]] = {}
    for i, (off, text) in enumerate(segments):
        toks = tokenize(text)
        seg_tokens.append(toks)
        for t in set(toks):
            tok_first[t] = min(tok_first.get(t, inf), off)
            tok_segs.setdefault(t, []).append(i)
            if "-" in t:
                for part in t.split("-"):
                    if part:
                        part_first[part] = min(part_first.get(part, inf), off)
    return {"segments": segments, "seg_tokens": seg_tokens, "tok_first": tok_first, "part_first": part_first, "tok_segs": tok_segs}


def first_mention(idx: dict, matcher: dict) -> int | None:
    """The offset of the first segment in which the term is said, or None. Segment resolution (a phrase split across two segments is not matched; declared)."""
    best = None
    for toks in matcher["phrases"]:
        prefix, last = toks[:-1], toks[-1]
        forms = token_forms(last, matcher["plural"], matcher["possessive"])
        if not prefix:
            for f in forms:
                for src in ((idx["tok_first"], idx["part_first"]) if matcher["compound"] else (idx["tok_first"],)):
                    v = src.get(f)
                    if v is not None and (best is None or v < best):
                        best = v
            continue
        for f in forms:
            for si in idx["tok_segs"].get(f, ()):
                st = idx["seg_tokens"][si]
                off = idx["segments"][si][0]
                if best is not None and off >= best:
                    continue
                for j, tk in enumerate(st):
                    if tk == f and j >= len(prefix) and st[j - len(prefix):j] == prefix:
                        best = off
                        break
    return None if best is None else int(best)


def parse_transcript_html(page) -> list[tuple[int, str]]:
    """A Factbase transcript page (HTML) -> [(offset seconds from the video's 00:00:00, segment text)]: scripts / styles / tags removed, ``hh:mm:ss`` stamps split the text, consecutive equal
    stamps merged, each segment capped at ``FACTBASE_SEGMENT_TEXT_CAP`` characters. The text exists in memory only (``reduce_transcript`` keeps offsets)."""
    s = page.decode("utf-8", "replace") if isinstance(page, bytes | bytearray) else str(page)
    txt = htmllib.unescape(TAG_RE.sub(" ", SCRIPT_RE.sub(" ", s)))
    ms = list(STAMP_RE.finditer(txt))
    segs: list[tuple[int, str]] = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(txt)
        off = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        body = " ".join(txt[m.end():end].split())[:FACTBASE_SEGMENT_TEXT_CAP]
        if segs and segs[-1][0] == off:
            segs[-1] = (off, (segs[-1][1] + " " + body).strip()[:FACTBASE_SEGMENT_TEXT_CAP])
        else:
            segs.append((off, body))
    return segs


def first_speaker_offset(segments: list[tuple[int, str]], speaker_key: str) -> int | None:
    """Offset of the first segment attributed to the speaker (text starting with, or labelled by, the speaker key); None if the page carries no such label."""
    if not speaker_key:
        return None
    pat = re.compile(r"(?i)^\W*(?:the |president |mr\.? |mrs\.? |ms\.? |dr\.? |governor )?(?:[a-z.\-']+ ){0,2}" + re.escape(speaker_key) + r"\b[^:]{0,30}:|\b" + re.escape(speaker_key) + r"\s*:")
    for off, text in segments:
        if pat.search(text[:80]):
            return int(off)
    return None


def reduce_transcript(segments: list[tuple[int, str]], matchers: dict[str, dict], speaker_key: str = "") -> dict:
    """Reduce a parsed transcript to numbers: stamps, first / last offset, the per-term first-mention offsets (said terms only) and the first speaker-attributed offset. No text is returned."""
    if not segments:
        return {"n_stamps": 0, "first_seg_s": None, "last_s": None, "base_s": None, "first": {}}
    idx = index_segments(segments)
    first = {}
    for key, mt in matchers.items():
        v = first_mention(idx, mt)
        if v is not None:
            first[key] = v
    fs = first_speaker_offset(segments, speaker_key)
    return {"n_stamps": len(segments), "first_seg_s": int(segments[0][0]), "last_s": int(max(o for o, _ in segments)), "base_s": int(fs if fs is not None else segments[0][0]),
            "first_speaker_s": fs, "first": first}


# =====================================================================================================================================================
# Occasion, speaker, transcript map, Factbase records
# =====================================================================================================================================================


def occasion_ok(start_epoch: float, end_epoch: float) -> bool:
    """Occasion rule: ``startTime`` present and ``endDate - startTime <= 36 h``."""
    return bool(math.isfinite(start_epoch) and math.isfinite(end_epoch) and (end_epoch - start_epoch) <= OCCASION_MAX_S)


def speaker_of_title(title: str) -> str | None:
    """The speaker key of an event title by the frozen keyword map; None if no keyword, or two different speakers (a debate)."""
    low = normalise_text(title)
    keys = []
    for kw, key in SPEAKER_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low) and key not in keys:
            keys.append(key)
    return keys[0] if len(keys) == 1 else None


def record_speaker_key(speaker_id) -> str | None:
    """The speaker key of a Factbase ``speaker_id`` (the keyword occurs in the normalised id)."""
    low = re.sub(r"[^a-z0-9]+", " ", normalise_text(speaker_id)).strip()
    for kw, key in SPEAKER_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return key
    return None


def type_keys_of_title(title: str) -> tuple[str, ...]:
    """Factbase record types an event title allows (first keyword rule that matches); () = no type keyword (unmapped)."""
    low = normalise_text(title)
    for kw, types in TYPE_RULES:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return tuple(types)
    return ()


def type_class_of(rec_type: str) -> str:
    return TYPE_CLASS.get(str(rec_type), "press")


def primary_speakers(counts: dict[str, int], min_n: int = PRIMARY_MIN_FIT) -> list[str]:
    """Speakers with at least ``min_n`` fit-window Factbase transcripts (metadata count at frame time, timestamped count at fit time)."""
    return sorted(k for k, n in counts.items() if n >= min_n)


def factbase_search_params(page: int) -> dict:
    return {"page": int(page), "sort": "date", "sort_order": "desc", "format": "json"}


def parse_search_page(data) -> list[dict]:
    """Whitelisted record fields (``date``, ``type``, ``record_title``, ``speaker_id``, ``factbase_url``; ``video_url`` and everything else dropped) of one Factbase search page."""
    rows = []
    for r in (data.get("data") if isinstance(data, dict) else None) or []:
        if not isinstance(r, dict):
            continue
        url = str(r.get("factbase_url") or "")
        d = str(r.get("date") or "")[:10]
        try:
            de = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
        except ValueError:
            continue
        if not url:
            continue
        sid = str(r.get("speaker_id") or "")
        rows.append({"record_id": hashlib.sha256(url.encode()).hexdigest()[:16], "date": d, "date_epoch": de, "type": str(r.get("type") or ""), "speaker_id": sid,
                     "speaker_key": record_speaker_key(sid) or "", "title": str(r.get("record_title") or ""), "url": url})
    return rows


def title_tokens(title: str) -> set[str]:
    return {t for t in tokenize(title) if len(t) > 2 and t not in TYPE_STOPWORDS and not t.isdigit()}


def map_event(title: str, start_epoch: float, speaker_key: str, records: list[dict]) -> dict:
    """Frozen transcript map (metadata only): the record of the speaker whose UTC date is within +-1 day of ``startTime`` and whose type matches the title's type; ties go first to the
    record title sharing the most content words with the event title (unique maximum), then to the nearest date (unique minimum); else 'unmapped'."""
    types = type_keys_of_title(title)
    base = {"status": "unmapped", "reason": "", "n_candidates": 0, "record": None}
    if not speaker_key:
        return {**base, "reason": "no_speaker"}
    if not types:
        return {**base, "reason": "no_type"}
    if not math.isfinite(start_epoch):
        return {**base, "reason": "no_start"}
    day = int(start_epoch // DAY)
    cand = [r for r in records if r["speaker_key"] == speaker_key and r["type"] in types and abs(int(r["date_epoch"] // DAY) - day) <= 1]
    base["n_candidates"] = len(cand)
    if not cand:
        return {**base, "reason": "no_record"}
    if len(cand) == 1:
        return {**base, "status": "mapped", "reason": "unique", "record": cand[0]}
    tt = title_tokens(title)
    score = [(len(tt & title_tokens(r["title"])), r) for r in cand]
    top = max(s for s, _ in score)
    best = [r for s, r in score if s == top]
    if len(best) == 1:
        return {**base, "status": "mapped", "reason": "title_keywords", "record": best[0]}
    near = min(abs(int(r["date_epoch"] // DAY) - day) for r in best)
    best2 = [r for r in best if abs(int(r["date_epoch"] // DAY) - day) == near]
    if len(best2) == 1:
        return {**base, "status": "mapped", "reason": "nearest_date", "record": best2[0]}
    return {**base, "reason": "tie"}


def gs0_sample(map_rows: list[dict], n: int = GS0_N, seed: int = GS0_SEED) -> list[dict]:
    """The blind GS0 audit sample: mapped events ranked by sha256(seed | event id), first ``n``. Rows carry event title, start, record title, date and type; no transcript text, price or outcome."""
    mapped = [r for r in map_rows if r.get("status") == "mapped"]
    mapped.sort(key=lambda r: c14.rank(str(seed), str(r["event_id"])))
    return [{k: r[k] for k in AUDIT_COLUMNS} for r in mapped[:n]]


def audit_precision(doc: dict) -> float:
    """GS0 precision from a committed audit file (``n_match`` / ``n_total``, else ``precision``); NaN if neither is present."""
    nt = c14.num(doc.get("n_total"))
    if math.isfinite(nt) and nt > 0 and math.isfinite(c14.num(doc.get("n_match"))):
        return float(c14.num(doc.get("n_match")) / nt)
    return c14.num(doc.get("precision"))


# =====================================================================================================================================================
# Gamma parsing (whitelisted fields only; outcomes discarded) and event statuses
# =====================================================================================================================================================


def parse_member_s(m: dict, event_id: str) -> dict | None:
    """Whitelisted member fields (ids, token, outcome labels, dates, the parsed term and rule booleans, ``description`` sha256 only, ``feeSchedule`` rate). ``outcomePrices``,
    ``umaResolutionStatus(es)`` and ``closedTime`` are never read. None = not a binary Yes/No market."""
    labels = [str(x).strip().lower() for x in c14.c12.listish(m.get("outcomes"))]
    toks = [str(x) for x in c14.c12.listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2 or m.get("id") is None:
        return None
    yi = labels.index("yes")
    desc = str(m.get("description") or "")
    term = parse_term(m.get("question"), m.get("groupItemTitle"))
    fl = rule_flags(desc)
    fs = m.get("feeSchedule")
    return {"event_id": event_id, "market_id": str(m["id"]), "condition_id": str(m.get("conditionId") or ""), "token_yes": toks[yi], "yes_index": yi,
            "created_epoch": c14.parse_iso(m.get("createdAt")), "term_raw": term["raw"] if term else "", "term_norm": term["norm"] if term else "",
            "variants": "|".join(term["variants"]) if term else "", "plural": int(fl["plural"]), "possessive": int(fl["possessive"]), "compound": int(fl["compound"]),
            "desc_sha256": hashlib.sha256(desc.encode()).hexdigest()[:16], "neg_risk_market_id": str(m.get("negRiskMarketID") or ""),
            "fee_rate": c14.num(fs.get("rate")) if isinstance(fs, dict) else math.nan, "_qa_excluded": fl["qa_excluded"], "_section_excluded": fl["section_excluded"]}


def parse_event_s(ev: dict) -> tuple[dict, list[dict]] | None:
    """(event row, member rows) with whitelisted fields only. The title is stored (public metadata for the map and the blind audit); descriptions are hashed; no outcome is read."""
    if not isinstance(ev, dict) or ev.get("id") is None:
        return None
    eid = str(ev["id"])
    title = str(ev.get("title") or "")
    tags = ev.get("tags") if isinstance(ev.get("tags"), list) else []
    ser = [s for s in (ev.get("series") if isinstance(ev.get("series"), list) else []) if isinstance(s, dict) and s.get("id") is not None]
    start, end = c14.parse_iso(ev.get("startTime")), c14.parse_iso(ev.get("endDate"))
    by_tag, by_re = is_sports_s(tags, title)
    members = []
    for m in ev.get("markets") if isinstance(ev.get("markets"), list) else []:
        pm = parse_member_s(m, eid) if isinstance(m, dict) else None
        if pm:
            members.append(pm)
    w = window_of(end)
    row = {"event_id": eid, "series_id": str(ser[0]["id"]) if ser else "", "title": title, "start_epoch": start, "end_epoch": end, "created_epoch": c14.parse_iso(ev.get("createdAt")),
           "neg_risk": int(bool(ev.get("negRisk"))), "n_members": len(members), "subset": w or "", "status": "", "status_source": "", "sports_tag": int(by_tag), "sports_re": int(by_re),
           "occasion": int(occasion_ok(start, end)), "speaker_key": speaker_of_title(title) or "", "type_keys": "|".join(type_keys_of_title(title)),
           "qa_excluded": int(any(m["_qa_excluded"] for m in members)), "section_excluded": int(any(m["_section_excluded"] for m in members)),
           "n_term_fail": sum(1 for m in members if not m["term_norm"]), "week": c14.iso_week_of(end) if math.isfinite(end) else "",
           "month": datetime.fromtimestamp(end, UTC).strftime("%Y-%m") if math.isfinite(end) else "", "title_sha256": c14.rank("arepo-cb14-title", title), "key_series_cf": 0}
    return row, members


def load_exempt(path: Path) -> dict[str, set[str]]:
    """The ids that come ONLY from CB12-M's SCREEN frame (``s_exempt_ids.csv.gz`` of q0302): N keeps them (declared deviation). {market, event, series, neg_risk_market}."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"{p} not found: the S frame needs the CB12-M SCREEN exemption file of q0302 (an empty file if h12_say was absent)")
    out: dict[str, set[str]] = {"market": set(), "event": set(), "series": set(), "neg_risk_market": set()}
    for r in c14.read_csv_gz(p):
        if str(r.get("found")) != "1":
            continue
        out["market"].add(str(r["market_id"]))
        out["event"].update(e for e in str(r.get("event_ids") or "").split(";") if e)
        out["series"].update(s for s in str(r.get("series_ids") or "").split(";") if s)
        if r.get("neg_risk_market_id"):
            out["neg_risk_market"].add(str(r["neg_risk_market_id"]))
    return out


def effective_keys(ids: set[str], sets: dict[str, set[str]], exempt: dict[str, set[str]], subset: str) -> dict[str, set[str]]:
    """The key sets that apply to a subset: P and Stage 2 drop every key; N does not drop the ids that live only in CB12-M's SCREEN frame."""
    if subset == "N":
        return {"market": set(ids) - exempt["market"], "event": set(sets["event"]) - exempt["event"], "neg_risk_market": set(sets["neg_risk_market"]) - exempt["neg_risk_market"],
                "series": set(sets["series"]) - exempt["series"]}
    return {"market": set(ids), "event": set(sets["event"]), "neg_risk_market": set(sets["neg_risk_market"]), "series": set(sets["series"])}


def key_drop(row: dict, members: list[dict], keys: dict[str, set[str]]) -> str | None:
    """'event' / 'market' / 'neg_risk' if the event hits an exclusion key, else None (the series-date key is applied by ``event_status_s``)."""
    if str(row["event_id"]) in keys["event"]:
        return "event"
    if any(m["market_id"] in keys["market"] for m in members):
        return "market"
    if any(m["neg_risk_market_id"] and m["neg_risk_market_id"] in keys["neg_risk_market"] for m in members):
        return "neg_risk"
    return None


def event_status_s(row: dict, members: list[dict], keys: dict[str, set[str]], series_dates: dict[str, list[float]], primary: set[str] | None) -> tuple[str, str]:
    """(status, source). Order: window (HOLDOUT / none) -> sports -> period (not an occasion) -> key drop (market, event, neg-risk, series-date) -> too few binary members -> Q&A or
    section excluded -> not a primary speaker. 'kept' = a primary-speaker occasion event."""
    if not math.isfinite(row["start_epoch"]) or row.get("subset") not in (*SUBSETS, "S2"):
        return "dropped:no_start_or_window", "frame"
    if row["sports_tag"] or row["sports_re"]:
        return "dropped:sports", "tag" if row["sports_tag"] else "regex"
    if not row["occasion"]:
        return "period", "occasion_rule"
    src = key_drop(row, members, keys)
    if src:
        return "dropped:key", src
    if row["series_id"] in series_dates and any(abs(row["start_epoch"] - d) <= DAY for d in series_dates[row["series_id"]]):
        return "dropped:key", "series_date"
    if row["n_members"] < MIN_MEMBERS:
        return "dropped:members", "n_members"
    if row["qa_excluded"] or row["section_excluded"]:
        return "dropped:qa_or_section", "qa" if row["qa_excluded"] else "section"
    if primary is not None and row["speaker_key"] not in primary:
        return "dropped:speaker", row["speaker_key"] or "none"
    return "kept", ""


def walk_window_s(lim, a: float, b: float, *, tag_id: int = TAG_ID, page: int = c14.GAMMA_PAGE, offset_cap: int = c14.GAMMA_OFFSET_CAP, stats: dict | None = None) -> list[dict]:
    """Closed Gamma events with ``tag_id`` and ``endDate`` in ``[a, b)``, paged to the offset cap; a window still full at the cap is split in half (< 1 h still capped -> refusal)."""
    out: list[dict] = []
    capped = True
    for off in range(0, offset_cap + page, page):
        st, data = lim.get(c14.GAMMA_EVENTS, {"closed": "true", "tag_id": tag_id, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "order": "id", "ascending": "true", "limit": page, "offset": off})
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma events status {st}")
        out.extend(x for x in data if isinstance(x, dict))
        if len(data) < page:
            capped = False
            break
    if not capped:
        return out
    if b - a < HOUR:
        raise Refused(f"gamma events window {cm.iso(a)}..{cm.iso(b)} is capped even below 1 h")
    if stats is not None:
        stats["splits"] = stats.get("splits", 0) + 1
    mid = a + (b - a) / 2
    return walk_window_s(lim, a, mid, tag_id=tag_id, page=page, offset_cap=offset_cap, stats=stats) + walk_window_s(lim, mid, b, tag_id=tag_id, page=page, offset_cap=offset_cap, stats=stats)


def week_windows(a: float, b: float, step: float = 7 * DAY) -> list[tuple[float, float]]:
    out, t = [], a
    while t < b:
        out.append((t, min(t + step, b)))
        t += step
    return out


# =====================================================================================================================================================
# Position model S_w(e) (fit transcripts only), the anchor q_t
# =====================================================================================================================================================


def count_curves(first: np.ndarray, last: np.ndarray, grid: int = MODEL_GRID_MIN) -> tuple[np.ndarray, np.ndarray]:
    """For the (speech, term) pairs ``first <= last`` (seconds): per minute ``m = 0..grid`` and ``e = 60 m``, ``n(m)`` = pairs with ``last >= e`` and ``k(m)`` = pairs with ``first > e``
    (every such pair has ``last >= first > e``), so ``S(e) = k / n`` = P(first mention > e | said, L >= e)."""
    e = np.arange(grid + 1) * 60.0
    ls, fs = np.sort(np.asarray(last, float)), np.sort(np.asarray(first, float))
    n = len(ls) - np.searchsorted(ls, e, side="left")
    k = len(fs) - np.searchsorted(fs, e, side="right")
    return n.astype(float), k.astype(float)


def shrunk_curve(n_w: np.ndarray, k_w: np.ndarray, n_p: np.ndarray, k_p: np.ndarray, shrink: float) -> list[float | None]:
    """``Shat_w(e) = (n_w S_w(e) + shrink S_pool(e)) / (n_w + shrink)``; a term never said (n_w = 0) uses ``S_pool``; undefined where the pool has no speech running (None)."""
    out: list[float | None] = []
    for nw, kw, npl, kpl in zip(n_w, k_w, n_p, k_p, strict=True):
        if npl <= 0:
            out.append(None)
            continue
        sp = kpl / npl
        out.append(round(float((kw + shrink * sp) / (nw + shrink)), 8))  # n_w S_w = k_w
    return out


def fit_model(transcripts: list[dict], *, shrink: float = SHRINK, rebased: bool = False, grid: int = MODEL_GRID_MIN, min_speeches: int = PRIMARY_MIN_FIT) -> dict:
    """The frozen position model. ``transcripts``: dicts with ``speaker_key``, ``type_class``, ``last_s`` / ``last_rebased_s``, ``first`` (term -> offset; ``first_rebased`` if rebased) and
    ``timestamped``. A speaker needs ``min_speeches`` timestamped fit transcripts; per (speaker, type class) the curves are stored for the terms said at least once, plus the pooled curve."""
    lk, fk = ("last_rebased_s", "first_rebased") if rebased else ("last_s", "first")
    by_sp: dict[str, list[dict]] = {}
    for t in transcripts:
        if t.get("timestamped", True) and t.get(lk) is not None:
            by_sp.setdefault(t["speaker_key"], []).append(t)
    speakers: dict[str, dict] = {}
    skipped = {}
    for sp, ts in sorted(by_sp.items()):
        if len(ts) < min_speeches:
            skipped[sp] = len(ts)
            continue
        classes: dict[str, dict] = {}
        for cls in sorted({t["type_class"] for t in ts}):
            sub = [t for t in ts if t["type_class"] == cls]
            pairs: dict[str, tuple[list[float], list[float]]] = {}
            for t in sub:
                for term, off in (t.get(fk) or {}).items():
                    f, l_ = pairs.setdefault(term, ([], []))
                    f.append(float(off))
                    l_.append(float(max(t[lk], off)))
            allf = np.array([x for f, _ in pairs.values() for x in f], float)
            alll = np.array([x for _, l_ in pairs.values() for x in l_], float)
            n_p, k_p = count_curves(allf, alll, grid) if len(allf) else (np.zeros(grid + 1), np.zeros(grid + 1))
            pool = [None if n <= 0 else round(float(k / n), 8) for n, k in zip(n_p, k_p, strict=True)]
            terms = {}
            for term, (f, l_) in sorted(pairs.items()):
                n_w, k_w = count_curves(np.array(f), np.array(l_), grid)
                terms[term] = shrunk_curve(n_w, k_w, n_p, k_p, shrink)
            classes[cls] = {"n_speeches": len(sub), "pool": pool, "terms": terms}
        speakers[sp] = classes
    return {"version": MODEL_VERSION, "shrinkage": shrink, "grid_minutes": grid, "rebased": bool(rebased), "min_speeches": min_speeches, "speakers": speakers, "speakers_below_minimum": skipped}


def model_text(model: dict) -> str:
    return json.dumps(model, sort_keys=True, separators=(",", ":"))


def shat(model: dict, speaker: str, cls: str, term: str, e_s: float) -> float:
    """``Shat_w(e)`` on the 1-minute grid (floor of ``e`` in minutes, clamped at the last grid minute); NaN where the model has no speaker / class / value (unit label 'no model')."""
    node = (model.get("speakers") or {}).get(speaker, {}).get(cls)
    if node is None or not math.isfinite(e_s):
        return math.nan
    m = int(min(model["grid_minutes"], max(0, e_s // 60)))
    arr = node["terms"].get(term) or node["pool"]
    v = arr[m]
    return math.nan if v is None else float(v)


def anchor_q(pi: float, s_hat: float) -> float:
    """``q = pi Shat / (1 - pi + pi Shat)`` = P(said by the end | unsaid after e_t) under the prior ``pi``: ``Shat = 1`` -> ``q = pi``; ``Shat = 0`` -> ``q = 0``."""
    if not (math.isfinite(pi) and math.isfinite(s_hat)):
        return math.nan
    den = 1.0 - pi + pi * s_hat
    return 0.0 if den <= 0 else float(pi * s_hat / den)


# =====================================================================================================================================================
# Price rules, causal alignment, causal transcript accessor
# =====================================================================================================================================================


def price_arrays(points: Iterable[tuple[float, float]]) -> tuple[list[float], list[float]]:
    """Sorted (stamps, prices) of 1-minute points (one row per stamp, the last wins)."""
    d: dict[float, float] = {}
    for ts, p in points:
        if math.isfinite(ts) and math.isfinite(p):
            d[float(ts)] = float(p)
    ks = sorted(d)
    return ks, [d[k] for k in ks]


def usable_index(stamps: list[float], T: float) -> int:
    """Index of the last point usable at ``T`` (stamp + 60 s <= T), or -1."""
    return bisect.bisect_right(stamps, T - POINT_LAG_S) - 1


def last_usable(pr: tuple[list[float], list[float]], T: float, max_age: float | None = None) -> tuple[int, float, float] | None:
    """(index, stamp, price) of the last point usable at ``T`` with age ``T - stamp <= max_age``; None if none."""
    i = usable_index(pr[0], T)
    if i < 0 or (max_age is not None and T - pr[0][i] > max_age):
        return None
    return i, pr[0][i], pr[1][i]


def jump_time(pr: tuple[list[float], list[float]]) -> float | None:
    """``J`` = the first minute at which the price is >= 0.85 while the price 3 minutes earlier was <= 0.60 (the last point at or before stamp - 180 s, at most 10 minutes stale)."""
    stamps, prices = pr
    for ts, p in zip(stamps, prices, strict=True):
        if p < ANCHOR_HI:
            continue
        j = bisect.bisect_right(stamps, ts - ANCHOR_BACK_S) - 1
        if j >= 0 and (ts - ANCHOR_BACK_S) - stamps[j] <= ANCHOR_BACK_MAX_AGE_S and prices[j] <= ANCHOR_LO:
            return float(ts)
    return None


def align_fixed_point(cands: list[tuple[float, float]], t: float) -> dict:
    """Causal clock alignment at checkpoint ``t``. ``cands`` = (J, o) per member said in the transcript with a jump time. Start from the candidates with ``J <= t - 1 min``; ``delta`` = the lower
    median of ``J - o`` over the set (an observed anchor, so two anchors 6 min apart cannot both lie within 5 min of it); keep the candidates with ``o <= e = t - delta``; repeat until the set is
    stable (<= 10 iterations; no convergence or an empty set -> unaligned). Aligned iff >= 2 anchors of the final set lie within 5 min of ``delta``."""
    pool = [(float(j), float(o)) for j, o in cands if j <= t - ANCHOR_LAG_S]
    cur = list(range(len(pool)))
    res = {"aligned": False, "delta": math.nan, "e": math.nan, "n_anchors": 0, "n_candidates": len(pool), "iterations": 0, "converged": False}
    for it in range(1, ALIGN_MAX_ITER + 1):
        if not cur:
            return {**res, "iterations": it, "reason": "no_anchor"}
        ds = sorted(pool[i][0] - pool[i][1] for i in cur)
        delta = ds[(len(ds) - 1) // 2]
        e = t - delta
        nxt = [i for i in range(len(pool)) if pool[i][1] <= e]
        if nxt == cur:
            near = sum(1 for i in cur if abs((pool[i][0] - pool[i][1]) - delta) <= ANCHOR_WITHIN_S)
            ok = near >= ANCHOR_MIN
            return {"aligned": bool(ok), "delta": float(delta), "e": float(e), "n_anchors": len(cur), "n_near": near, "n_candidates": len(pool), "iterations": it, "converged": True,
                    "reason": "" if ok else "fewer_than_2_anchors_within_5min"}
        cur = nxt
    return {**res, "iterations": ALIGN_MAX_ITER, "reason": "no_convergence"}


class CausalTranscript:
    """The causal transcript accessor. A target transcript is outcome-bearing (it says which words were said and when), so census paths see it only through ``said_by`` and
    ``offsets_upto`` (what a viewer knew at ``e_t``) and ``anchor_offset`` (the alignment input of the frozen fixed point, which keeps only anchors with ``o <= e_t``). ``full_offset``
    (the first mention after ``e_t``, the transcript-based Y) is opened by the screen and rep jobs only."""

    def __init__(self, last_s: float, mentions: dict[str, float | None], base_s: float = 0.0, *, open_full: bool = False, rebase: bool = False):
        shift = float(base_s) if rebase else 0.0
        self._last = max(0.0, float(last_s) - shift)
        self._m = {k: (None if v is None else max(0.0, float(v) - shift)) for k, v in mentions.items()}
        self._open_full = bool(open_full)

    @property
    def last_s(self) -> float:
        return self._last

    def said_by(self, mid: str, e: float) -> bool:
        o = self._m.get(mid)
        return bool(o is not None and o <= e)

    def offsets_upto(self, e: float) -> dict[str, float]:
        return {k: v for k, v in self._m.items() if v is not None and v <= e}

    def anchor_offset(self, mid: str) -> float | None:
        return self._m.get(mid)

    def full_offset(self, mid: str) -> float | None:
        if not self._open_full:
            raise Refused("the full target transcript (offsets after e_t, the transcript-based Y) is opened only by the screen and rep jobs")
        return self._m.get(mid)


def outcome_y(outcome_prices, uma_status, yes_index: int) -> tuple[float, str]:
    """(Y, kind): a clean resolved vector -> 1 or 0 ('clean'); 50-50 -> 0.5 ('5050'); anything else (unresolved, voided, malformed) -> 0.5 ('unclean')."""
    v = [c14.num(x) for x in c14.c12.listish(outcome_prices)]
    st = str(uma_status or "").lower()
    if len(v) != 2 or not all(math.isfinite(x) for x in v):
        return 0.5, "unclean"
    yes, other = v[yes_index], v[1 - yes_index]
    if "resolved" in st and abs(yes - 0.5) < 1e-9 and abs(other - 0.5) < 1e-9:
        return 0.5, "5050"
    if "resolved" in st and ((abs(yes - 1) < 1e-9 and abs(other) < 1e-9) or (abs(yes) < 1e-9 and abs(other - 1) < 1e-9)):
        return float(yes > 0.5), "clean"
    return 0.5, "unclean"


# =====================================================================================================================================================
# Units
# =====================================================================================================================================================


def event_checkpoints(start: float, grid_s: int = CHECKPOINT_S) -> list[float]:
    """Wall-clock checkpoints (multiples of ``grid_s`` since the epoch) over the fetched span ``[start - 30 min, start + 5 h]``."""
    t = math.ceil((start - FETCH_BEFORE_S) / grid_s) * grid_s
    out = []
    while t <= start + FETCH_AFTER_S:
        out.append(float(t))
        t += grid_s
    return out


def build_event_units(ev: dict, members: list[dict], ct: CausalTranscript, prices: dict[str, tuple[list[float], list[float]]], model: dict, *, shift_s: float = 0.0, grid_s: int = CHECKPOINT_S,
                      min_e_s: float = MIN_E_S) -> dict:
    """Units of one event: (word, 5-minute checkpoint) from the first aligned checkpoint with ``e_t >= 10 min``, the word unsaid by ``e_t`` (first mention > ``e_t`` or never), not 'rising'
    (>= 15c over [t - 5 min, t]), ``p_t`` in [0.03, 0.97], ``p_lag`` available and a different point from ``p_t``. Reads prices usable before ``t`` and the causal accessor only; ``shift_s``
    shifts ``e_t`` (the +-2 min clock check). Returns the units, the per-label counts and the alignment facts."""
    labels: Counter = Counter()
    cands, jumps = [], {}
    for m in members:
        pr = prices.get(m["market_id"])
        o = ct.anchor_offset(m["market_id"])
        if pr and pr[0]:
            j = jump_time(pr)
            jumps[m["market_id"]] = j
            if j is not None and o is not None:
                cands.append((j, o))
    info = {"event_id": ev["event_id"], "n_candidates": len(cands), "aligned_checkpoints": 0, "anchor_counts": [], "delta_first": None, "first_anchor_J": min((c[0] for c in cands), default=None),
            "first_aligned_t": None, "last_s": ct.last_s}
    units: list[dict] = []
    started = False
    pi: dict[str, float | None] = {}
    for t in event_checkpoints(ev["start_epoch"], grid_s):
        al = align_fixed_point(cands, t)
        if not al["aligned"]:
            labels["unaligned_checkpoint" if started else "unaligned_checkpoint_before_start"] += 1
            continue
        info["aligned_checkpoints"] += 1
        info["anchor_counts"].append(al["n_anchors"])
        if info["delta_first"] is None:
            info["delta_first"] = al["delta"]
            info["first_aligned_t"] = t
            for m in members:
                pr = prices.get(m["market_id"])
                lp = last_usable(pr, al["delta"] - PI_BACK_S) if pr else None
                pi[m["market_id"]] = None if lp is None else lp[2]
        e = t - al["delta"] + shift_s
        if e < min_e_s:
            if started:
                labels["before_10min"] += 1
            continue
        if e >= ct.last_s:
            break
        started = True
        for m in members:
            mid = m["market_id"]
            if ct.said_by(mid, e):
                labels["said"] += 1
                continue
            pr = prices.get(mid)
            pt = last_usable(pr, t, P_T_MAX_AGE_S) if pr else None
            if pt is None:
                labels["no_price"] += 1
                continue
            if not (P_MIN <= pt[2] <= P_MAX):
                labels["outside"] += 1
                continue
            lo = bisect.bisect_left(pr[0], t - RISING_WINDOW_S)
            hi = usable_index(pr[0], t) + 1
            if hi > lo and pt[2] - min(pr[1][lo:hi]) >= RISING_MIN - 1e-9:
                labels["rising"] += 1
                continue
            pl = last_usable(pr, t - P_LAG_BACK_S, P_LAG_MAX_AGE_S)
            if pl is None or pl[0] == pt[0]:
                labels["no_price"] += 1
                continue
            if pi.get(mid) is None:
                labels["no_price"] += 1
                continue
            sh = shat(model, ev["speaker_key"], ev["cls"], m["term_norm"], e)
            if not math.isfinite(sh):
                labels["no_model"] += 1
                continue
            p15 = last_usable(pr, t - P15_BACK_S, P_LAG_MAX_AGE_S)
            labels["unit"] += 1
            units.append({"event_id": ev["event_id"], "market_id": mid, "term": m["term_norm"], "subset": ev["subset"], "speaker": ev["speaker_key"], "cls": ev["cls"], "start": ev["start_epoch"],
                          "week": ev["week"], "t": t, "e": e, "p": pt[2], "p_lag": pl[2], "p15": p15[2] if p15 else math.nan, "pi": pi[mid], "shat": sh, "q": anchor_q(pi[mid], sh),
                          "delta": al["delta"], "n_anchors": al["n_anchors"], "first_anchor_J": info["first_anchor_J"]})
    return {"units": units, "labels": labels, "info": info}


def build_units(data: dict, model: dict, *, shift_s: float = 0.0, grid_s: int = CHECKPOINT_S, min_e_s: float = MIN_E_S, rebase: bool = False) -> dict:
    """Units of every event of a loaded dataset (``rebase`` builds the transcripts' re-based accessors). Returns {units, labels, events: {event_id: info}}."""
    units: list[dict] = []
    labels: Counter = Counter()
    events: dict[str, dict] = {}
    for eid, ev in sorted(data["events"].items()):
        ct = data["ct_rebased"][eid] if rebase else data["ct"][eid]
        r = build_event_units(ev, data["members"][eid], ct, data["prices"], model, shift_s=shift_s, grid_s=grid_s, min_e_s=min_e_s)
        units += r["units"]
        labels.update(r["labels"])
        events[eid] = {**r["info"], "n_units": len(r["units"])}
    return {"units": units, "labels": labels, "events": events}


# =====================================================================================================================================================
# Dataset layout and loaders (a census never receives an outcome; the full transcript opens only for screen / rep)
# =====================================================================================================================================================


def subset_files(rdir: Path, tag: str) -> dict[str, Path]:
    """Paths of one subset ('P', 'N' or 'S2') under the run directory."""
    rdir = Path(rdir)
    if tag in SUBSETS:
        lo = tag.lower()
        return {"frame": rdir / "frame.csv.gz", "members": rdir / "members.csv.gz", "map": rdir / "map.csv.gz", "prices": rdir / f"prices_{lo}.csv.gz", "tx": rdir / f"tx_{lo}.csv.gz",
                "markets": rdir / f"markets_{lo}.csv.gz", "guarded": rdir / f"guarded_{lo}", "outcomes": rdir / f"guarded_{lo}" / f"outcomes_guarded_{lo}.csv.gz", "manifest": rdir / f"manifest_{lo}.json"}
    if tag == "S2":
        s2 = rdir / "stage2"
        return {"frame": s2 / "frame.csv.gz", "members": s2 / "members.csv.gz", "map": s2 / "map.csv.gz", "prices": s2 / "prices.csv.gz", "tx": s2 / "tx.csv.gz", "markets": s2 / "markets.csv.gz",
                "guarded": rdir / "guarded_s2", "outcomes": rdir / "guarded_s2" / "outcomes_guarded_s2.csv.gz", "manifest": rdir / "manifest_s2.json"}
    raise Refused(f"unknown subset {tag!r}")


def refuse_if_other_root(rdir: Path) -> Path:
    """S reads only its own run directory (never another batch's root, never an ``h12_say`` file)."""
    c14.guard_input_path(Path(rdir))
    if "h12_say" in Path(rdir).parts:
        raise Refused("CB14 opens no h12_say file")
    return Path(rdir)


def _f(x) -> float:
    return c14.num(x) if x not in ("", None) else math.nan


def read_frame(rdir: Path, tag: str) -> list[dict]:
    """All frame rows of a subset (every status), numbers parsed; any P / N row in CB12-M's HOLDOUT window (or a Stage-2 event before the floor) is a refusal."""
    fp = subset_files(rdir, tag)["frame"]
    rows = []
    for r in c14.read_csv_gz(fp):
        if tag in SUBSETS and r["subset"] != tag:
            continue
        for k in ("start_epoch", "end_epoch", "created_epoch"):
            r[k] = _f(r[k])
        for k in ("sports_tag", "sports_re", "occasion", "qa_excluded", "section_excluded", "n_members", "n_term_fail"):
            r[k] = int(float(r[k] or 0))
        if tag in SUBSETS:
            if guard_window(r["end_epoch"], f"frame event {r['event_id']}") != tag:
                raise Refused(f"frame event {r['event_id']} of subset {tag} ends outside the S windows for that subset")
        elif r["start_epoch"] < _ep(T14_S2_FLOOR):
            raise Refused(f"Stage-2 event {r['event_id']} starts before {T14_S2_FLOOR}")
        rows.append(r)
    return rows


def load_dataset(rdir: Path, tags: Iterable[str], *, job: str) -> dict:
    """Kept, mapped events with a parsed target transcript, their members, 1-minute prices, transactions and market records, and the causal transcript accessors. ``job`` is 'census',
    'screen' or 'rep'; only the last two get accessors with ``full_offset``. No outcome file is opened here."""
    if job not in ("census", "screen", "rep", "pregate"):
        raise Refused(f"unknown job {job!r}")
    rdir = refuse_if_other_root(Path(rdir))
    open_full = job in ("screen", "rep")
    out: dict = {"events": {}, "members": {}, "map": {}, "ct": {}, "ct_rebased": {}, "prices": {}, "tx": {}, "markets": {}, "transcripts": {}, "tags": list(tags), "frame_rows": {}}
    for tag in tags:
        f = subset_files(rdir, tag)
        frame = read_frame(rdir, tag)
        out["frame_rows"][tag] = frame
        maps = {r["event_id"]: r for r in c14.read_csv_gz(f["map"])} if f["map"].exists() else {}
        mem: dict[str, list[dict]] = {}
        for r in c14.read_csv_gz(f["members"]):
            mem.setdefault(r["event_id"], []).append(r)
        trs = {r["event_id"]: r for r in c14.read_csv_gz(f["guarded"] / "transcripts.csv.gz")} if (f["guarded"] / "transcripts.csv.gz").exists() else {}
        ments: dict[str, dict[str, float | None]] = {}
        if (f["guarded"] / "mentions.csv.gz").exists():
            c14.log_access(f["guarded"], job, "mentions.csv.gz")
            for r in c14.read_csv_gz(f["guarded"] / "mentions.csv.gz"):
                ments.setdefault(r["event_id"], {})[r["market_id"]] = None if r["first_s"] == "" else float(r["first_s"])
        for r in frame:
            eid = r["event_id"]
            if r["status"] != "kept" or maps.get(eid, {}).get("status") != "mapped" or trs.get(eid, {}).get("status") != "ok" or eid not in mem:
                continue
            tr = trs[eid]
            ev = {**r, "subset": tag if tag in SUBSETS else "S2", "cls": type_class_of(maps[eid]["record_type"]), "record_type": maps[eid]["record_type"]}
            out["events"][eid] = ev
            out["members"][eid] = [{**m, "yes_index": int(float(m["yes_index"]))} for m in mem[eid]]
            out["map"][eid] = maps[eid]
            out["transcripts"][eid] = tr
            mm = ments.get(eid, {})
            mm = {m["market_id"]: mm.get(m["market_id"]) for m in mem[eid]}
            out["ct"][eid] = CausalTranscript(float(tr["last_s"]), mm, float(tr["base_s"] or 0), open_full=open_full)
            out["ct_rebased"][eid] = CausalTranscript(float(tr["last_s"]), mm, float(tr["base_s"] or 0), open_full=open_full, rebase=True)
        keep_mid = {m["market_id"] for eid in out["events"] for m in out["members"][eid] if out["events"][eid]["subset"] == (tag if tag in SUBSETS else "S2")}
        raw: dict[str, list[tuple[float, float]]] = {}
        for r in c14.read_csv_gz(f["prices"]):
            if r["market_id"] in keep_mid:
                raw.setdefault(r["market_id"], []).append((float(r["ts"]), float(r["p"])))
        for mid, pts in raw.items():
            out["prices"][mid] = price_arrays(pts)
        for r in c14.read_csv_gz(f["tx"]):
            if r["market_id"] in keep_mid:
                out["tx"].setdefault(r["market_id"], []).append((float(r["ts"]), float(r["price"]), float(r["size"])))
        for v in out["tx"].values():
            v.sort()
        for r in c14.read_csv_gz(f["markets"]):
            if r["market_id"] in keep_mid:
                out["markets"][r["market_id"]] = r
    return out


def load_fit_transcripts(fit_dir: Path) -> list[dict]:
    """Fit transcripts (record metadata + per-term first offsets, plain and re-based) from ``fit/records.csv.gz`` and ``fit/offsets.csv.gz``."""
    fit_dir = Path(fit_dir)
    recs = {}
    for r in c14.read_csv_gz(fit_dir / "records.csv.gz"):
        recs[r["record_id"]] = {"record_id": r["record_id"], "speaker_key": r["speaker_key"], "type_class": r["type_class"], "timestamped": r["timestamped"] == "1", "last_s": _f(r["last_s"]),
                                "last_rebased_s": _f(r["last_rebased_s"]), "first": {}, "first_rebased": {}}
    for r in c14.read_csv_gz(fit_dir / "offsets.csv.gz"):
        t = recs.get(r["record_id"])
        if t is not None:
            t["first"][r["term"]] = float(r["first_s"])
            t["first_rebased"][r["term"]] = float(r["first_rebased_s"])
    for t in recs.values():
        for k in ("last_s", "last_rebased_s"):
            if not math.isfinite(t[k]):
                t[k] = None
    return sorted(recs.values(), key=lambda t: t["record_id"])


def load_model(path: Path, pin: str | None = None, *, what: str = "position model") -> dict:
    check_model_pin(Path(path), pin, what=what)
    return json.loads(Path(path).read_text())


# =====================================================================================================================================================
# Statistics: S1 (slope), S2 (in-speech maker), GSP latents
# =====================================================================================================================================================


def word_weights(units: list[dict]) -> np.ndarray:
    """Each word weight 1, split over its units (``Y`` is one value per word): the weights of a word's units sum to 1."""
    cnt = Counter(u["market_id"] for u in units)
    return np.array([1.0 / cnt[u["market_id"]] for u in units], float)


def build_ymap(data: dict, outcomes: list[dict]) -> dict[str, dict]:
    """Per word: Gamma ``y`` (unclean scored 0.5), ``y_wc`` (unclean at 1), ``kind`` and the transcript-derived ``y_tr`` (1 iff the word is said anywhere in the transcript). Screen / rep only."""
    by = {r["market_id"]: r for r in outcomes}
    out = {}
    for eid, mems in data["members"].items():
        for m in mems:
            r = by.get(m["market_id"])
            y, kind = outcome_y(r["outcome_prices"], r["uma_status"], int(float(r["yes_index"]))) if r is not None else (0.5, "unclean")
            out[m["market_id"]] = {"y": y, "y_wc": 1.0 if kind == "unclean" else y, "kind": kind, "y_tr": 0.0 if data["ct"][eid].full_offset(m["market_id"]) is None else 1.0}
    return out


def unit_clusters(units: list[dict]) -> dict[str, list[str]]:
    return {"event": [u["event_id"] for u in units], "week": [u["week"] for u in units], "term": [u["term"] for u in units]}


def s1_fit(units: list[dict], ymap: dict, key: str = "y", extra: bool = False) -> dict | None:
    """Word-weighted OLS (intercept) of ``Y - p_t`` on ``q_t - p_lag`` (``extra``: also ``pi - p_lag`` and ``p_lag - p_{t-15 min}``; units without ``p15`` dropped). Returns the clustered
    pseudo-values of the first coefficient."""
    us = [u for u in units if math.isfinite(u["p15"])] if extra else list(units)
    if len(us) < 5:
        return None
    y = np.array([ymap[u["market_id"]][key] for u in us], float)
    p = np.array([u["p"] for u in us], float)
    x1 = np.array([u["q"] - u["p_lag"] for u in us], float)
    X = np.column_stack([x1, [u["pi"] - u["p_lag"] for u in us], [u["p_lag"] - u["p15"] for u in us]]) if extra else x1
    w = word_weights(us)
    v, b = c14.wls_coef_pseudo(y - p, X, w, 0)
    if not math.isfinite(b):
        return None
    return {"units": us, "y_minus_p": y - p, "x": x1, "X": X, "w": w, "v": v, "b": b, "cl": unit_clusters(us), "n": len(us), "n_words": len({u["market_id"] for u in us}),
            "n_events": len({u["event_id"] for u in us})}


def s1_cp(fit: dict, *, n_wild: int = c14.N_WILD, alpha: float | None = None) -> dict:
    """The S1 p (max over the event, ISO-week and term ways; CB10 small-G rule: a way with G < 15 leaves the max and its leave-one-cluster-out sign rule binds on the RE-ESTIMATED
    coefficient)."""
    X = np.asarray(fit["X"], float)

    def est(keep: np.ndarray) -> float:
        return float(c14.wls_coef_pseudo(fit["y_minus_p"][keep], X[keep], fit["w"][keep], 0)[1]) if keep.sum() >= 5 else math.nan

    return c14.cluster_p(fit["v"], fit["cl"], n_wild=n_wild, alpha=alpha, estimator=est)


def s1_slope(units: list[dict], ymap: dict, key: str = "y") -> float:
    f = s1_fit(units, ymap, key)
    return math.nan if f is None else float(f["b"])


def s1_holds(units: list[dict], ymap: dict, alpha_adv: float, *, key: str = "y", n_wild: int = c14.N_WILD) -> bool:
    """p < ``alpha_adv`` (testable) and the slope floor hold on ``units``."""
    f = s1_fit(units, ymap, key)
    if f is None:
        return False
    cp = s1_cp(f, n_wild=n_wild)
    return bool(c14.p_pass(cp, alpha_adv) and f["b"] >= S1_FLOOR)


def s1_signflip(units: list[dict], ymap: dict, *, n_draws: int = SIGNFLIP_DRAWS, seed: int = c14.PLACEBO_SEEDS["S1_signflip"], n_wild: int = c14.N_WILD) -> dict:
    """Binding calibration: one coin per event flips the regressor; the advance rate on the p threshold alone (floors off) must be <= 1.5%."""
    f = s1_fit(units, ymap)
    if f is None:
        return {"note": "S1 event sign-flip calibration", "n_draws": 0, "advance_rate": 1.0, "holds": False, "seed": seed}

    def base(signs: np.ndarray) -> float | None:
        v, b = c14.wls_coef_pseudo(f["y_minus_p"], f["x"] * signs, f["w"], 0)
        return c14.cluster_p(v, f["cl"], n_wild=n_wild, alpha=c14.GATE_P)["p"] if math.isfinite(b) else None

    ps = c14.sign_flip_p_draws(n_draws, seed, f["cl"]["event"], base)
    return {**c14.placebo_advance_rate(ps), "note": "S1 event sign-flip calibration (floors off)", "seed": seed}


def s1_joint(units: list[dict], ymap: dict, solo_b: float, *, n_wild: int = c14.N_WILD) -> dict:
    """Binding clock attribution: the ``q_t - p_lag`` coefficient of the joint fit with ``pi - p_lag`` and ``p_lag - p_{t-15 min}`` keeps >= half its solo value with one-sided p < 0.05."""
    f = s1_fit(units, ymap, extra=True)
    if f is None:
        return {"ok": False, "reason": "joint fit unavailable"}
    cp = s1_cp(f, n_wild=n_wild)
    ok = bool(c14.p_pass(cp, JOINT_P) and f["b"] >= JOINT_HALF * solo_b and f["b"] > 0)
    return {"ok": ok, "b_joint": f["b"], "b_solo": solo_b, "p": cp["p"], "testable": cp["testable"], "n": f["n"],
            "label": None if ok else "start-price drift or momentum, not the clock"}


def band_slopes(units: list[dict], ymap: dict) -> dict:
    """Reported (uncounted): slope by elapsed band, by type class and by start-price band."""
    out: dict = {}
    for name, fn in (("elapsed_10_30", lambda u: 600 <= u["e"] < 1800), ("elapsed_30_60", lambda u: 1800 <= u["e"] < 3600), ("elapsed_gt_60", lambda u: u["e"] >= 3600),
                     ("type_prepared", lambda u: u["cls"] == "prepared"), ("type_press", lambda u: u["cls"] == "press"), ("pi_lt_0.3", lambda u: u["pi"] < m12.PRICE_BANDS[0]),
                     ("pi_0.3_0.6", lambda u: m12.PRICE_BANDS[0] <= u["pi"] <= m12.PRICE_BANDS[1]), ("pi_gt_0.6", lambda u: u["pi"] > m12.PRICE_BANDS[1])):
        sub = [u for u in units if fn(u)]
        out[name] = {"n": len(sub), "slope": s1_slope(sub, ymap) if len(sub) >= 30 else None}
    return out


def gsp_latent(rng: np.random.Generator, week_idx: np.ndarray, event_idx: np.ndarray, term_idx: np.ndarray, price: np.ndarray) -> np.ndarray:
    """One latent per word: ``Z = sqrt(.15) V_week + sqrt(.25) U_event + sqrt(.15) T_term + sqrt(.45) eps_w`` and ``Y* = 1{Phi(Z) > 1 - price}`` (so P(Y* = 1) = price)."""
    a, b, c, d = (math.sqrt(x) for x in GSP_LOADINGS)
    n = len(price)
    if n == 0:
        return np.zeros(0)
    V = rng.standard_normal(int(week_idx.max()) + 1)
    U = rng.standard_normal(int(event_idx.max()) + 1)
    T = rng.standard_normal(int(term_idx.max()) + 1)
    Z = a * V[week_idx] + b * U[event_idx] + c * T[term_idx] + d * rng.standard_normal(n)
    return (norm.cdf(Z) > 1.0 - np.asarray(price, float)).astype(float)


def _codes(labels: Iterable[str]) -> np.ndarray:
    d: dict[str, int] = {}
    return np.array([d.setdefault(str(x), len(d)) for x in labels], int)


def gsp_s1(units: list[dict], *, n_draws: int = c14.GSP_DRAWS, seed: int = c14.SEED_GSP) -> dict:
    """GSP (S1 power, feature-only): per draw one latent per word (week, event and normalised-term factors), ``Y* = 1{Phi(Z) > 1 - pi_w}``, the S1 slope of ``Y* - p_t`` on ``q_t - p_lag``;
    ``MDE_S1 = 3.16 x 1.2 x max(SD(beta*), mean SE per way)`` over the event, week and term ways. No outcome is read."""
    words = sorted({u["market_id"] for u in units})
    if len(units) < 10 or len(words) < 3:
        return {"pass": False, "MDE_S1": math.nan, "note": "too few units"}
    widx = {m: i for i, m in enumerate(words)}
    first = {}
    for u in units:
        first.setdefault(u["market_id"], u)
    wk = _codes(first[m]["week"] for m in words)
    ev = _codes(first[m]["event_id"] for m in words)
    tm = _codes(first[m]["term"] for m in words)
    pi = np.array([first[m]["pi"] for m in words], float)
    ui = np.array([widx[u["market_id"]] for u in units], int)
    p = np.array([u["p"] for u in units], float)
    X = np.array([u["q"] - u["p_lag"] for u in units], float)
    w = word_weights(units)
    cl = unit_clusters(units)
    rng = np.random.default_rng(seed)
    bs, ses = [], {k: [] for k in cl}
    for _ in range(n_draws):
        ystar = gsp_latent(rng, wk, ev, tm, pi)[ui]
        v, b = c14.wls_coef_pseudo(ystar - p, X, w, 0)
        if not math.isfinite(b):
            continue
        bs.append(b)
        for k, c in cl.items():
            ses[k].append(c14.cluster_se_mean(v, c))
    if len(bs) < 2:
        return {"pass": False, "MDE_S1": math.nan, "note": "too few valid draws"}
    mean_se = {k: float(np.nanmean(v)) if np.isfinite(v).any() else math.nan for k, v in ses.items()}
    sd = float(np.std(bs, ddof=1))
    m = c14.mde(max([sd, *[x for x in mean_se.values() if math.isfinite(x)]]))
    return {"MDE_S1": m, "sd_beta": sd, "mean_se": mean_se, "max_mde": MDE_S1_MAX, "draws": len(bs), "seed": seed, "pass": bool(math.isfinite(m) and m <= MDE_S1_MAX)}


def s2_eligible(units: list[dict]) -> list[dict]:
    return [u for u in units if u["e"] >= S2_MIN_E_S]


def reach_at(market: dict | None, t: float) -> bool:
    """True iff the market's fetched prints reach back to ``t`` (not truncated, or the oldest reachable print is at or before ``t``)."""
    if not market:
        return False
    tr = c14.num(market.get("truncated"))
    if math.isfinite(tr) and not int(tr):
        return True
    o = c14.num(market.get("oldest_ts"))
    return bool(math.isfinite(o) and o <= t)


def s2_fills(units: list[dict], data: dict, *, off_p: float = ASK_OFFSET_P, off_q: float = ASK_OFFSET_Q, through: float = TRADE_THROUGH, ymap: dict | None = None,
             ykey: str = "y", reach_worst: bool = False) -> dict:
    """S2 on the S2-eligible units (``e_t >= 30 min``): per word, in time order, the ask ``a = ceil_tick(max(p_t + off_p, q_t + off_q))`` capped at 0.99 is filled only by the first transaction
    in ``[t, t + 5 min)`` with YES-terms price >= ``a + through``; size ``min(100, tx size)``; one fill per word. A word whose prints do not reach back to ``t`` is unavailable (counted), or, with
    ``reach_worst``, filled at ``a`` for 100 shares at its first eligible checkpoint iff ``Y > 0``. Without ``ymap`` no outcome is touched (census)."""
    by_word: dict[str, list[dict]] = {}
    for u in s2_eligible(units):
        by_word.setdefault(u["market_id"], []).append(u)
    fills, n_words, n_unreached, n_ckpt = [], 0, 0, 0
    for mid, us in sorted(by_word.items()):
        n_words += 1
        us.sort(key=lambda u: u["t"])
        rows = data["tx"].get(mid, [])
        mk = data["markets"].get(mid)
        unreached_here = False
        for u in us:
            n_ckpt += 1
            a = min(c14.ceil_tick(max(u["p"] + off_p, u["q"] + off_q)), c14.PRICE_CAP)
            if not reach_at(mk, u["t"]):
                unreached_here = True
                if reach_worst and ymap is not None and ymap[mid][ykey] > 0:
                    fills.append({**_fill_base(u), "a": a, "price": a, "size": FILL_CAP, "worst": True})
                    break
                continue
            hit = next(((ts, px, sz) for ts, px, sz in rows if u["t"] <= ts < u["t"] + FILL_WINDOW_S and px >= a + through - 1e-9), None)
            if hit is not None:
                fills.append({**_fill_base(u), "a": a, "price": hit[1], "size": min(FILL_CAP, hit[2]), "worst": False})
                break
        n_unreached += int(unreached_here and not any(f["market_id"] == mid for f in fills))
    return {"fills": fills, "n_words": n_words, "n_unreached_words": n_unreached, "n_checkpoints": n_ckpt}


def _fill_base(u: dict) -> dict:
    return {"event_id": u["event_id"], "market_id": u["market_id"], "term": u["term"], "week": u["week"], "subset": u["subset"], "t": u["t"], "e": u["e"]}


def s2_stat(fills: list[dict], ymap: dict, key: str = "y", y_override: np.ndarray | None = None) -> dict | None:
    """S2 statistic: the mean over events with >= 1 fill of the event's size-weighted net per filled share ``a - Y``. Fill-level pseudo-values ``v_i = (N / n_events) w_i net_i`` (``w_i``: the
    fill's size share in its event) have ``mean(v) = event mean``, so the event / week / term cluster sandwich applies."""
    if not fills:
        return None
    ev = [f["event_id"] for f in fills]
    size = np.array([f["size"] for f in fills], float)
    tot = {}
    for e, s in zip(ev, size, strict=True):
        tot[e] = tot.get(e, 0.0) + s
    w = np.array([s / tot[e] for e, s in zip(ev, size, strict=True)], float)
    y = y_override if y_override is not None else np.array([ymap[f["market_id"]][key] for f in fills], float)
    net = np.array([f["a"] for f in fills], float) - y
    v = (len(fills) / len(tot)) * w * net
    return {"v": v, "mean": float(v.mean()), "n_fills": len(fills), "n_events": len(tot), "cl": {"event": ev, "week": [f["week"] for f in fills], "term": [f["term"] for f in fills]}, "net": net, "w": w}


def s2_cp(fills: list[dict], ymap: dict, *, key: str = "y", n_wild: int = c14.N_WILD, alpha: float | None = None) -> tuple[dict | None, dict | None]:
    """(statistic, p) of S2 on ``fills``: the max over the event, ISO-week and term ways under the CB10 small-G rule (a way with G < 15 leaves the max and its leave-one-cluster-out
    sign rule binds on the re-estimated event-mean net)."""
    st = s2_stat(fills, ymap, key)
    if st is None:
        return None, None

    def est(keep: np.ndarray) -> float:
        sub = s2_stat([f for f, k in zip(fills, keep, strict=True) if k], ymap, key)
        return math.nan if sub is None else float(sub["mean"])

    return st, c14.cluster_p(st["v"], st["cl"], n_wild=n_wild, alpha=alpha, estimator=est)


def s2_sign(fills: list[dict], ymap: dict, key: str = "y") -> bool:
    """A sign-only S2 robustness check: the event-mean net on ``fills`` is positive (no fill = unknown = not met)."""
    st = s2_stat(fills, ymap, key)
    return bool(st is not None and math.isfinite(st["mean"]) and st["mean"] > 0)


def s2_placebo(fills: list[dict], *, n_draws: int = c14.PLACEBO_DRAWS, seed: int = c14.PLACEBO_SEEDS["S2_calibrated"], n_wild: int = c14.N_WILD) -> dict:
    """Binding placebo: ``Y*`` calibrated to the FILL-TIME price with the GSP latents (one latent per word); same fills; judged on p < 0.01 alone."""
    if not fills:
        return {"note": "S2 fill-time calibrated placebo", "n_draws": 0, "advance_rate": 1.0, "holds": False, "seed": seed}
    wk, ev, tm = _codes(f["week"] for f in fills), _codes(f["event_id"] for f in fills), _codes(f["term"] for f in fills)
    px = np.clip(np.array([f["price"] for f in fills], float), 0.0, 1.0)
    rng = np.random.default_rng(seed)
    ps = []
    for _ in range(n_draws):
        st = s2_stat(fills, {}, y_override=gsp_latent(rng, wk, ev, tm, px))
        ps.append(c14.cluster_p(st["v"], st["cl"], n_wild=n_wild, alpha=c14.GATE_P)["p"])
    return {**c14.placebo_advance_rate(ps), "note": "S2 fill-time calibrated placebo (floors off)", "seed": seed}


def gsp_s2(fills: list[dict], *, n_draws: int = c14.GSP_DRAWS, seed: int = c14.SEED_GSP) -> dict:
    """GSP2 (S2 power, feature-only): the same latents calibrated to the fill price; ``MDE_S2 = 3.16 x 1.2 x max(SD of the event-mean net, mean SE per way)``; > 2.0c -> 'not run (power)'."""
    if len(fills) < 10:
        return {"pass": False, "MDE_S2": math.nan, "note": "too few fills"}
    wk, ev, tm = _codes(f["week"] for f in fills), _codes(f["event_id"] for f in fills), _codes(f["term"] for f in fills)
    px = np.clip(np.array([f["price"] for f in fills], float), 0.0, 1.0)
    rng = np.random.default_rng(seed)
    means, ses = [], {"event": [], "week": [], "term": []}
    for _ in range(n_draws):
        st = s2_stat(fills, {}, y_override=gsp_latent(rng, wk, ev, tm, px))
        means.append(st["mean"])
        for k, c in st["cl"].items():
            ses[k].append(c14.cluster_se_mean(st["v"], c))
    mean_se = {k: float(np.nanmean(v)) if np.isfinite(v).any() else math.nan for k, v in ses.items()}
    sd = float(np.std(means, ddof=1))
    m = c14.mde(max([sd, *[x for x in mean_se.values() if math.isfinite(x)]]))
    return {"MDE_S2": m, "sd_mean": sd, "mean_se": mean_se, "max_mde": MDE_S2_MAX, "draws": n_draws, "seed": seed, "pass": bool(math.isfinite(m) and m <= MDE_S2_MAX)}


# =====================================================================================================================================================
# Pre-fetch gate GSC, census (counts only), screen and rep
# =====================================================================================================================================================


def not_run_result(label: str, test: str = "") -> dict:
    return {"test": test, "p": 1.0, "testable": False, "advance": False, "verdict": label, "label": LABEL_S, "effect": None, "n": 0}


def p_months_usable(smoke_doc: dict | None) -> set[str] | None:
    """The P months whose 1-minute availability passed in the S smoke (``detail.s_availability_p_months.months_usable``); None if the smoke file carries no such list."""
    d = ((smoke_doc or {}).get("detail") or {}).get("s_availability_p_months") or {}
    mu = d.get("months_usable")
    return None if mu is None else {str(x) for x in mu}


def pregate_s(hist_root: Path, *, audit_path: Path, smoke_path: Path) -> dict:
    """GSC (q0316): counts only, no network, no price / print / transcript / outcome. Needs >= 100 primary-speaker events with a mapped Factbase record across P and N in >= 30 ISO weeks,
    >= 25 of them in P (months whose 1-minute availability failed are dropped from P), GS0 PASS (precision >= 90%) and the S smoke's availability rule PASS."""
    rdir = refuse_if_other_root(Path(hist_root) / FRAME_RUN)
    fp = subset_files(rdir, "P")
    frame = {r["event_id"]: r for r in c14.read_csv_gz(fp["frame"])}
    maps = {r["event_id"]: r for r in c14.read_csv_gz(fp["map"])}
    sm = json.loads(Path(smoke_path).read_text()) if Path(smoke_path).exists() else {}
    crit = sm.get("criteria") or {}
    usable = p_months_usable(sm)
    audit = json.loads(Path(audit_path).read_text()) if Path(audit_path).exists() else None
    prec = audit_precision(audit) if audit else math.nan
    rows, dropped_month = [], 0
    for eid, r in frame.items():
        if r["status"] != "kept" or maps.get(eid, {}).get("status") != "mapped" or r["subset"] not in SUBSETS:
            continue
        end = c14.num(r["end_epoch"])
        guard_window(end, f"frame event {eid}")
        if r["subset"] == "P" and usable is not None and r["month"] not in usable:
            dropped_month += 1
            continue
        rows.append(r)
    weeks = {r["week"] for r in rows}
    n_p = sum(1 for r in rows if r["subset"] == "P")
    checks = {"events": len(rows) >= GSC_MIN["events"], "weeks": len(weeks) >= GSC_MIN["weeks"], "p_events": n_p >= GSC_MIN["p_events"],
              "gs0_audit": bool(audit is not None and math.isfinite(prec) and prec >= GS0_MIN_PRECISION), "smoke_availability": bool(crit.get("s_availability_p_months"))}
    ok = all(checks.values())
    return {"version": "cb14-pregate-S-v1", "counts_only": True, "pass": ok, "events_mapped_primary": len(rows), "iso_weeks": len(weeks), "p_events": n_p, "n_events": len(rows) - n_p,
            "p_events_dropped_unusable_month": dropped_month, "gs0_precision": None if not math.isfinite(prec) else prec, "checks": checks, "min": GSC_MIN,
            "label": None if ok else "not testable (population)"}


def frame_report_counts(frame_rows: dict[str, list[dict]], maps: dict[str, dict], transcripts: dict[str, dict]) -> dict:
    """Frame-level census counts (metadata): events by subset, status, speaker, type and month; term-parser failures; Q&A / section exclusions; map and parse statuses."""
    out: dict = {"by_subset_status": {}, "kept_by_speaker": {}, "kept_by_type": {}, "kept_by_month": {}, "members_kept": 0, "term_parse_failures_kept": 0, "qa_or_section_excluded_events": 0,
                 "dropped_speaker": {}, "map_status": dict(Counter(f"{m['status']}:{m['reason']}" for m in maps.values())), "transcript_status": dict(Counter(t["status"] for t in transcripts.values()))}
    for tag, rows in frame_rows.items():
        out["by_subset_status"][tag] = dict(Counter(r["status"] for r in rows))
        out["qa_or_section_excluded_events"] += sum(1 for r in rows if r["status"] == "dropped:qa_or_section")
        for r in rows:
            if r["status"] == "dropped:speaker":
                out["dropped_speaker"][r["speaker_key"] or "none"] = out["dropped_speaker"].get(r["speaker_key"] or "none", 0) + 1
            if r["status"] != "kept":
                continue
            out["members_kept"] += r["n_members"]
            out["term_parse_failures_kept"] += r["n_term_fail"]
            for k, v in (("kept_by_speaker", r["speaker_key"]), ("kept_by_type", r["type_keys"]), ("kept_by_month", r["month"])):
                out[k][v] = out[k].get(v, 0) + 1
    return out


def late_overlap_s(hist_root: Path, keys_report: dict | None, data: dict) -> dict:
    """The id sets that were 'absent at q0302' and exist now (field-restricted id readers only; section 1.3: re-read by the census): S events whose event id, a member's market id or a
    member's ``negRiskMarketID`` they hold are dropped from the census, the screen and the rep (counted). CB12-M's SCREEN frame never drops an N event (the declared deviation)."""
    absent = list((keys_report or {}).get("sets_absent_at_q0302") or [])
    drop: set[str] = set()
    by_set: dict[str, int] = {}
    for rel in absent:
        p = c14.id_source_path(rel, Path(hist_root))
        if not p.is_file():
            continue
        cols = c14.read_id_columns(p)
        m_ids, e_ids = cols.get("market_id", set()), cols.get("event_id", set())
        n_ids = cols.get("neg_risk_market_id", set()) | cols.get("negRiskMarketID", set())
        root = rel.split("/", 1)[0]
        hit = set()
        for eid, ev in data["events"].items():
            if root == c14.S_EXEMPT_ROOT and ev.get("subset") == "N":
                continue
            if eid in e_ids or any(m["market_id"] in m_ids or (m.get("neg_risk_market_id") and m["neg_risk_market_id"] in n_ids) for m in data["members"].get(eid, [])):
                hit.add(eid)
        by_set[rel] = len(hit)
        drop |= hit
    for eid in drop:
        for k in ("events", "members", "map", "ct", "ct_rebased", "transcripts"):
            data[k].pop(eid, None)
    return {"dropped_events": len(drop), "by_set": by_set, "absent_at_q0302": absent}


def gates_s(data: dict, built: dict, *, n_draws: int = c14.GSP_DRAWS, seed: int = c14.SEED_GSP) -> dict:
    """GS (population) and GSP / GSP2 (power, feature-only latents; no outcome) on a loaded dataset's units: the census gates, recomputed by the screen on P alone when N is reported-only."""
    units, infos = built["units"], built["events"]
    events_units = {e for e, i in infos.items() if i["n_units"] > 0}
    aligned_events = sum(1 for i in infos.values() if i["aligned_checkpoints"] > 0)
    weeks = {data["events"][e]["week"] for e in events_units}
    words = {u["market_id"] for u in units}
    fills = s2_fills(units, data)
    gs_checks = {"events_with_unit": len(events_units) >= GS_MIN["events"], "iso_weeks": len(weeks) >= GS_MIN["weeks"], "words_with_units": len(words) >= GS_MIN["words"],
                 "alignment_share": bool(infos) and aligned_events / len(infos) >= GS_MIN["align_share"]}
    out: dict = {"GS": {"checks": gs_checks, "min": GS_MIN, "pass": all(gs_checks.values())}, "fills": fills, "events_units": events_units, "aligned_events": aligned_events, "weeks": weeks,
                 "words": words}
    if not out["GS"]["pass"]:
        out["GSP"] = {"pass": False, "note": "not computed (GS failed)"}
        out["GSP2"] = {"pass": False, "note": "not computed (GS failed)"}
        out["label_S1"] = out["label_S2"] = "not testable (population)"
        return out
    out["GSP"] = gsp_s1(units, n_draws=n_draws, seed=seed)
    out["GSP2"] = gsp_s2(fills["fills"], n_draws=n_draws, seed=seed)
    out["label_S1"] = None if out["GSP"]["pass"] else "not run (power)"
    out["label_S2"] = None if out["GSP2"]["pass"] else "not run (power)"
    return out


def census_s(hist_root: Path, *, model_path: Path, model_pin: str | None = None, subsets: tuple[str, ...] = SUBSETS, n_draws: int = c14.GSP_DRAWS, seed: int = c14.SEED_GSP,
             ledger_path: Path | None = None, git=None, keys_report: dict | None = None) -> dict:
    """q0319, counts only. N pieces refuse (NotNow) before ``T14_S_open``. No outcome file is opened (the loader never opens one and the census passes 'census' to every accessor); prices
    enter only through the units' usable-before-``t`` rules and transcripts only through ``CausalTranscript``. Writes no Y, slope or net; fills are print mechanics. Frames absent at
    q0302 are re-read (ids only) and their events dropped."""
    rdir = refuse_if_other_root(Path(hist_root) / FRAME_RUN)
    model = load_model(model_path, model_pin)
    if "N" in subsets:
        c14.s_open_status(ledger_path, git=git)
    data = load_dataset(rdir, subsets, job="census")
    late = late_overlap_s(Path(hist_root), keys_report, data)
    built = build_units(data, model)
    units, labels = built["units"], built["labels"]
    maps_all = {}
    trs_all = {}
    for tag in subsets:
        f = subset_files(rdir, tag)
        maps_all.update({r["event_id"]: r for r in c14.read_csv_gz(f["map"])})
        if (f["guarded"] / "transcripts.csv.gz").exists():
            trs_all.update({r["event_id"]: r for r in c14.read_csv_gz(f["guarded"] / "transcripts.csv.gz")})
    rep = frame_report_counts(data["frame_rows"], maps_all, trs_all)
    infos = built["events"]
    g = gates_s(data, built, n_draws=n_draws, seed=seed)
    events_units, aligned_events, weeks, words, fills = g["events_units"], g["aligned_events"], g["weeks"], g["words"], g["fills"]
    anchor_hist = Counter(n for i in infos.values() for n in i["anchor_counts"])
    qd = np.array([u["q"] - u["p_lag"] for u in units], float)
    first_seg = [c14.num(t["first_seg_s"]) for t in data["transcripts"].values()]
    base_seg = [c14.num(t["base_s"]) for t in data["transcripts"].values()]
    out: dict = {"version": "cb14-census-S-v1", "counts_only": True, "label": LABEL_S, "subsets": list(subsets), "frame": rep, "late_overlap": late, "events_loaded": len(data["events"]),
                 "events_with_unit": len(events_units),
                 "alignment": {"mapped_events_loaded": len(infos), "events_with_aligned_checkpoint": aligned_events, "success_share": (aligned_events / len(infos)) if infos else 0.0,
                               "anchor_count_distribution": {str(k): v for k, v in sorted(anchor_hist.items())}},
                 "units_by_label": dict(labels), "n_units": len(units), "n_words_with_units": len(words), "iso_weeks": len(weeks),
                 "q_minus_p_lag_quantiles": [float(x) for x in np.quantile(qd, [0.05, 0.25, 0.5, 0.75, 0.95])] if len(qd) else [],
                 "pre_roll": {"first_segment_offset_s_quantiles": _qs(first_seg), "first_speaker_offset_s_quantiles": _qs(base_seg)},
                 "s2": {"eligible_units": len(s2_eligible(units)), "eligible_words": fills["n_words"], "fills": len(fills["fills"]), "unreached_words": fills["n_unreached_words"]},
                 "GS": g["GS"], "GSP": g["GSP"], "GSP2": g["GSP2"], "label_S1": g["label_S1"], "label_S2": g["label_S2"]}
    return out


def _qs(vals: list[float]) -> list[float]:
    v = [x for x in vals if math.isfinite(x)]
    return [float(x) for x in np.quantile(v, [0.1, 0.5, 0.9])] if v else []


def holds_sign(units: list[dict], ymap: dict, key: str = "y", min_units: int = 30) -> bool:
    """Robustness sign check: the slope is positive on at least ``min_units`` units (unknown never counts as met)."""
    if len(units) < min_units:
        return False
    b = s1_slope(units, ymap, key)
    return bool(math.isfinite(b) and b > 0)


def s1_screen(data: dict, models: dict, ymap: dict, *, alpha_adv: float = c14.GATE_P, stage: int = 1, n_draws: int = SIGNFLIP_DRAWS, n_wild: int = c14.N_WILD, placebo: bool = True,
              label: str = LABEL_S) -> dict:
    """S1 on a loaded dataset: the headline slope (floor 0.30; p = max over the event, ISO-week and normalised-term ways), the binding event sign-flip calibration, joint clock attribution,
    +-2 min clock-shift check and the binding robustness list; 'reported' items are uncounted. ``models``: base, shrink5, shrink20, rebased."""
    cache: dict[str, dict] = {}

    def B(name: str, **kw) -> dict:
        if name not in cache:
            mdl = kw.pop("model", models["base"])
            cache[name] = build_units(data, mdl, **kw)
        return cache[name]

    base = B("base")
    units, lab = base["units"], base["labels"]
    lost = lab.get("no_price", 0) + lab.get("no_model", 0)
    avail = len(units) / (len(units) + lost) if (len(units) + lost) else 0.0
    res: dict = {"test": "S1", "label": label, "n": len(units), "availability_share": avail, "units_by_label": dict(lab)}
    if avail < c14.AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (availability)"}
    fit = s1_fit(units, ymap)
    if fit is None:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (units)"}
    cp = s1_cp(fit, n_wild=n_wild)
    floor_ok = bool(fit["b"] >= S1_FLOOR)
    res.update(effect=fit["b"], p=cp["p"], testable=cp["testable"], ways=cp["ways"], floor_ok=floor_ok, n_words=fit["n_words"], n_events=fit["n_events"], small_g_rules_hold=cp["small_g_rules_hold"])
    if not cp["testable"]:
        return {**res, "advance": False, "checks_ok": False, "verdict": "not testable (units / clusters)"}
    rob: dict = {}
    tags = set(data["tags"])
    if "P" in tags:
        rob["P_alone"] = holds_sign([u for u in units if u["subset"] == "P"], ymap)
    if "N" in tags:
        rob["N_alone"] = holds_sign([u for u in units if u["subset"] == "N"], ymap)
    rob["transcript_y"] = holds_sign(units, ymap, "y_tr")
    rob["e_ge_20min"] = holds_sign([u for u in units if u["e"] >= ROBUST_E_S], ymap)
    rob["checkpoint_10min"] = holds_sign(B("grid10", grid_s=CHECKPOINT_ALT_S)["units"], ymap)
    rob["shrinkage_5"] = holds_sign(B("shrink5", model=models["shrink5"])["units"], ymap)
    rob["shrinkage_20"] = holds_sign(B("shrink20", model=models["shrink20"])["units"], ymap)
    rob["prepared_only"] = holds_sign([u for u in units if u["cls"] == "prepared"], ymap)
    rob["late_start_dropped"] = holds_sign([u for u in units if not (u["first_anchor_J"] is not None and u["first_anchor_J"] - u["start"] > LATE_START_S)], ymap)
    rob["rebased_offsets"] = holds_sign(B("rebased", model=models["rebased"], rebase=True)["units"], ymap) if models.get("rebased") else None
    rob["unresolved_at_1"] = holds_sign(units, ymap, "y_wc")
    for way in ("event", "week", "term"):
        keep = c14.top_k_drop_mask(fit["v"], fit["cl"][way], c14.TOP_DROP)
        rob[f"top5_{way}_drop"] = s1_holds([u for u, k in zip(fit["units"], keep, strict=True) if k], ymap, c14.GATE_P, n_wild=n_wild)  # the p threshold 0.01 (as CB13 Stage 2)
    halves, quarters = c14.halves_and_quarters([u["t"] for u in units])
    rob["halves_sign"] = bool(halves) and all(holds_sign([u for u, h in zip(units, halves, strict=True) if h == k], ymap) for k in (0, 1))
    rob["leave_one_quarter_out_sign"] = bool(quarters) and all(holds_sign([u for u, q in zip(units, quarters, strict=True) if q != qq], ymap) for qq in sorted(set(quarters)))
    shift = {}
    for name, s in (("minus_2min", -SHIFT_S), ("plus_2min", SHIFT_S)):
        us = B(f"shift_{name}", shift_s=s)["units"]
        f2 = s1_fit(us, ymap)
        c2 = s1_cp(f2, n_wild=n_wild) if f2 else None
        shift[name] = {"n": len(us), "b": None if f2 is None else f2["b"], "p": None if c2 is None else c2["p"], "ok": bool(f2 is not None and c14.p_pass(c2, SHIFT_P) and f2["b"] > 0)}
    joint = s1_joint(units, ymap, fit["b"], n_wild=n_wild)
    plc = s1_signflip(units, ymap, n_draws=n_draws, n_wild=n_wild) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    shift_ok = all(v["ok"] for v in shift.values())
    checks_ok = bool(floor_ok and cp["small_g_rules_hold"] and rob_ok and shift_ok and joint["ok"] and (plc is None or plc["holds"]))  # every binding check but the primary p gate
    p_ok = bool(cp["testable"] and cp["p"] < alpha_adv)
    adv = bool(p_ok and checks_ok)
    res.update(robustness=rob, robustness_ok=rob_ok, clock_shift=shift, clock_shift_ok=shift_ok, joint=joint, placebo=plc, checks_ok=checks_ok, p_ok=p_ok, advance=adv)
    res["reported"] = {"by_band": band_slopes(units, ymap), "transcript_gamma_agreement": agreement(data, ymap),
                       "level_mean_y_minus_p_P": _level(units, ymap), "by_subset": {k: {"n": len(sub), "slope": s1_slope(sub, ymap) if len(sub) >= 30 else None}
                                                                                    for k in sorted(tags & set(SUBSETS)) for sub in [[u for u in units if u["subset"] == k]]}}
    res["verdict"] = "advance" if adv else "no advance"
    return res


def agreement(data: dict, ymap: dict) -> dict:
    """Transcript-Gamma agreement on clean words (< 95% -> the label 'settlement basis')."""
    pairs = [(r["y"], r["y_tr"]) for r in ymap.values() if r["kind"] == "clean"]
    share = sum(1 for a, b in pairs if a == b) / len(pairs) if pairs else math.nan
    return {"n_clean_words": len(pairs), "share": share, "label": "settlement basis" if (math.isfinite(share) and share < 0.95) else None}


def _level(units: list[dict], ymap: dict) -> float | None:
    us = [u for u in units if u["subset"] == "P"]
    if not us:
        return None
    w = word_weights(us)
    return float(np.average([ymap[u["market_id"]]["y"] - u["p"] for u in us], weights=w))


def s2_screen(data: dict, models: dict, ymap: dict, *, alpha_adv: float = c14.GATE_P, stage: int = 1, n_draws: int = c14.PLACEBO_DRAWS, n_wild: int = c14.N_WILD, placebo: bool = True,
              label: str = LABEL_S) -> dict:
    """S2 on a loaded dataset: event-mean net per filled share (floor +1.0c; p = max over event, week, term ways), the fill-time calibrated placebo, cost, trade-through, worst-case reach,
    +-2 min clock-shift, P / N and top-5 robustness. Reported: the taker variant, capacity and the event-level loss distribution."""
    base = build_units(data, models["base"])
    fl = s2_fills(base["units"], data, ymap=ymap)
    res: dict = {"test": "S2", "label": label, "n": len(fl["fills"]), "n_words": fl["n_words"], "n_unreached_words": fl["n_unreached_words"]}
    avail = 1.0 - fl["n_unreached_words"] / fl["n_words"] if fl["n_words"] else 0.0
    res["availability_share"] = avail
    if avail < c14.AVAIL_MIN:
        return {**res, "p": 1.0, "testable": False, "advance": False, "effect": None, "verdict": "not testable (availability)"}
    st, cp = s2_cp(fl["fills"], ymap, n_wild=n_wild)
    if st is None:
        return {**res, "p": 1.0, "testable": False, "advance": False, "checks_ok": False, "effect": None, "verdict": "not testable (no fills)"}
    floor_ok = bool(st["mean"] >= S2_FLOOR)
    res.update(effect=st["mean"], p=cp["p"], testable=cp["testable"], ways=cp["ways"], floor_ok=floor_ok, n_events=st["n_events"], small_g_rules_hold=cp["small_g_rules_hold"])
    if not cp["testable"]:
        return {**res, "advance": False, "checks_ok": False, "verdict": "not testable (units / clusters)"}

    def holds(fills: list[dict], *, adv_p: float, need_floor: bool = True) -> bool:
        s, c = s2_cp(fills, ymap, n_wild=n_wild)
        if s is None:
            return False
        return bool(c14.p_pass(c, adv_p) and (s["mean"] >= S2_FLOOR if need_floor else s["mean"] > 0))

    rob: dict = {}
    r_cost = s2_fills(base["units"], data, off_p=ASK_OFFSET_P_ROBUST, off_q=ASK_OFFSET_Q_ROBUST, ymap=ymap)["fills"]
    s_c = s2_stat(r_cost, ymap)
    rob["cost_ask_plus_0.5c_net_positive"] = bool(s_c and s_c["mean"] > 0)
    s_t = s2_stat(s2_fills(base["units"], data, through=TRADE_THROUGH_ROBUST, ymap=ymap)["fills"], ymap)
    rob["trade_through_2c_net_positive"] = bool(s_t and s_t["mean"] > 0)
    rob["worst_case_reach"] = holds(s2_fills(base["units"], data, ymap=ymap, reach_worst=True)["fills"], adv_p=c14.GATE_P)
    shift = {}
    for name, s in (("minus_2min", -SHIFT_S), ("plus_2min", SHIFT_S)):
        f2 = s2_fills(build_units(data, models["base"], shift_s=s)["units"], data, ymap=ymap)["fills"]
        s2_, c2 = s2_cp(f2, ymap, n_wild=n_wild)
        shift[name] = {"n_fills": len(f2), "mean": None if s2_ is None else s2_["mean"], "p": None if c2 is None else c2["p"], "ok": bool(s2_ and c14.p_pass(c2, SHIFT_P) and s2_["mean"] > 0)}
    for k in sorted(set(data["tags"]) & set(SUBSETS)):
        sub = [f for f in fl["fills"] if f["subset"] == k]
        s_k = s2_stat(sub, ymap)
        rob[f"{k}_alone_sign"] = bool(len(sub) >= 30 and s_k and s_k["mean"] > 0)
    for way in ("event", "term", "week"):
        keep = c14.top_k_drop_mask(st["v"], st["cl"][way], c14.TOP_DROP)
        rob[f"top5_{way}_drop"] = holds([f for f, k in zip(fl["fills"], keep, strict=True) if k], adv_p=c14.GATE_P)
    halves, quarters = c14.halves_and_quarters([f["t"] for f in fl["fills"]])  # section 2.6 (iii): sign by calendar half and leave-one-quarter-out sign (fill time)
    rob["halves_sign"] = bool(halves) and all(s2_sign([f for f, h in zip(fl["fills"], halves, strict=True) if h == k], ymap) for k in (0, 1))
    rob["leave_one_quarter_out_sign"] = bool(quarters) and all(s2_sign([f for f, q in zip(fl["fills"], quarters, strict=True) if q != qq], ymap) for qq in sorted(set(quarters)))
    plc = s2_placebo(fl["fills"], n_draws=n_draws, n_wild=n_wild) if placebo else None
    rob_ok = all(v is True for v in rob.values())
    shift_ok = all(v["ok"] for v in shift.values())
    checks_ok = bool(floor_ok and cp["small_g_rules_hold"] and rob_ok and shift_ok and (plc is None or plc["holds"]))  # every binding check but the primary p gate
    p_ok = bool(cp["testable"] and cp["p"] < alpha_adv)
    adv = bool(p_ok and checks_ok)
    ev_vals: dict[str, list[float]] = {}
    for f, n, w in zip(fl["fills"], st["net"], st["w"], strict=True):
        ev_vals.setdefault(f["event_id"], []).append(float(n * w))
    evv = np.array([sum(v) for v in ev_vals.values()], float)
    res.update(robustness=rob, robustness_ok=rob_ok, clock_shift=shift, clock_shift_ok=shift_ok, placebo=plc, checks_ok=checks_ok, p_ok=p_ok, advance=adv, verdict="advance" if adv else "no advance",
               reported={"capacity_filled_shares_per_event_mean": float(sum(f["size"] for f in fl["fills"]) / st["n_events"]), "event_net_quantiles": [float(x) for x in np.quantile(evv, [0.01, 0.05, 0.5])],
                         "taker_variant": taker_variant(base["units"], data, ymap), "events_without_fill": len({u["event_id"] for u in s2_eligible(base["units"])}) - st["n_events"]})
    return res


def taker_variant(units: list[dict], data: dict, ymap: dict) -> dict:
    """Reported (uncounted): buy NO at the minimum YES-terms print in ``[t, t + 2 min]`` when ``p_t - q_t >= 8c``; fee ``r a (1 - a)``, ``r = max(feeSchedule.rate, 0.05)``; first checkpoint per word."""
    nets, rate_by = [], {}
    for mems in data["members"].values():
        for m in mems:
            rate_by[m["market_id"]] = c14.num(m.get("fee_rate"))
    seen: set[str] = set()
    for u in sorted(s2_eligible(units), key=lambda x: x["t"]):
        if u["market_id"] in seen or u["p"] - u["q"] < 0.08:
            continue
        px = [p for ts, p, _ in data["tx"].get(u["market_id"], []) if u["t"] <= ts <= u["t"] + 120]
        if not px:
            continue
        seen.add(u["market_id"])
        a = 1.0 - min(px)
        nets.append((1.0 - ymap[u["market_id"]]["y"]) - a - c14.taker_rate(rate_by.get(u["market_id"]), 0.05) * a * (1.0 - a))
    return {"n": len(nets), "mean_net_per_share": float(np.mean(nets)) if nets else None}


def make_models(out_root: Path, fit_dir: Path, *, model_pin: str | None = None, rebased_pin: str | None = None) -> dict:
    """The primary model (pinned file), the shrinkage-5 / 20 variants (refit from the fit offsets) and the re-based model (pinned file)."""
    out_root = Path(out_root)
    base = load_model(out_root / MODEL_FILE, model_pin)
    reb = load_model(out_root / MODEL_REBASED_FILE, rebased_pin, what="re-based position model")
    fit = load_fit_transcripts(fit_dir)
    return {"base": base, "rebased": reb, "shrink5": fit_model(fit, shrink=SHRINK_ALT[0]), "shrink20": fit_model(fit, shrink=SHRINK_ALT[1])}


def screen_s(hist_root: Path, *, census: dict, out_root: Path, rules_sha: str = "", model_pin: str | None = None, rebased_pin: str | None = None, n_primary: dict | None = None,
             ledger_path: Path | None = None, git=None, n_draws: int = SIGNFLIP_DRAWS, n_wild: int = c14.N_WILD, placebo: bool = True, keys_report: dict | None = None,
             gsp_draws: int = c14.GSP_DRAWS) -> dict:
    """q0320: S1 and S2 on P (and N iff N is primary). N refuses before ``T14_S_open``; if the part-S rules commit post-dates the CB12-M Stage-1 result N is reported-only (descriptive lines,
    outside the tests) and the census gates GS / GSP / GSP2 are RECOMPUTED on P alone (feature-only; a test fails its gate if either reading fails it). Outcomes come only from the
    guarded files through ``open_guarded('screen')``."""
    lab1, lab2 = census.get("label_S1"), census.get("label_S2")
    if lab1 and lab2:
        return {"S1": not_run_result(lab1, "S1"), "S2": not_run_result(lab2, "S2"), "label": LABEL_S, "census_labels": [lab1, lab2]}
    rdir = refuse_if_other_root(Path(hist_root) / FRAME_RUN)
    ops = c14.s_open_status(ledger_path, git=git)
    nprim = n_primary if n_primary is not None else c14.n_primary_status(ops, rules_sha, git=git)
    models = make_models(out_root, rdir / "fit", model_pin=model_pin, rebased_pin=rebased_pin)
    tags = ("P", "N") if nprim["n_primary"] else ("P",)
    gates_p = None
    if not nprim["n_primary"]:
        dp = load_dataset(rdir, ("P",), job="census")
        late_overlap_s(Path(hist_root), keys_report, dp)
        gp = gates_s(dp, build_units(dp, models["base"]), n_draws=gsp_draws)
        gates_p = {k: gp[k] for k in ("GS", "GSP", "GSP2", "label_S1", "label_S2")}
        lab1, lab2 = lab1 or gp["label_S1"], lab2 or gp["label_S2"]
        if lab1 and lab2:
            out0 = {"S1": not_run_result(lab1, "S1"), "S2": not_run_result(lab2, "S2"), "label": LABEL_S, "census_labels": [census.get("label_S1"), census.get("label_S2")], "n_primary": nprim,
                    "gates_P_only": gates_p, "tags": ["P"]}
            return out0
    data = load_dataset(rdir, tags, job="screen")
    late = late_overlap_s(Path(hist_root), keys_report, data)
    outs = []
    for tag in tags:
        outs += c14.open_guarded(subset_files(rdir, tag)["outcomes"], "screen", ("screen", "rep"))
    ymap = build_ymap(data, outs)
    out: dict = {"label": LABEL_S, "n_primary": nprim, "tags": list(tags), "census_labels": [census.get("label_S1"), census.get("label_S2")], "gates_P_only": gates_p, "late_overlap": late}
    out["S1"] = not_run_result(lab1, "S1") if lab1 else s1_screen(data, models, ymap, n_draws=n_draws, n_wild=n_wild, placebo=placebo)
    out["S2"] = not_run_result(lab2, "S2") if lab2 else s2_screen(data, models, ymap, n_draws=n_draws, n_wild=n_wild, placebo=placebo)
    if not nprim["n_primary"]:
        dn = load_dataset(rdir, ("N",), job="screen")
        yn = build_ymap(dn, c14.open_guarded(subset_files(rdir, "N")["outcomes"], "screen", ("screen", "rep")))
        un = build_units(dn, models["base"])["units"]
        out["N_reported_only"] = {"note": "N is reported-only: the S rules part was committed at/after the CB12-M Stage-1 result", "n_units": len(un), "slope": s1_slope(un, yn) if len(un) >= 30 else None}
    return out


def rep_s(hist_root: Path, *, out_root: Path, tests: tuple[str, ...] = ("S1", "S2"), now: float, k2: int | None = None, model_pin: str | None = None, rebased_pin: str | None = None,
          n_draws: int = SIGNFLIP_DRAWS, n_wild: int = c14.N_WILD, placebo: bool = True, keys_report: dict | None = None) -> dict:
    """q0322: S1-rep / S2-rep on the post-freeze Stage-2 events (same frame, map, pinned model without refit, alignment and rules), only once q0321 has CLOSED the window (>= 100 resolved
    events with >= 1 aligned unit = ``T14_S2_end``, or the cap) AND the fixed post-close outcome wait (``S2_OUTCOME_WAIT_D``) is over (``STAGE2_STATUS_FINAL``); < 60 resolved events
    with a unit at the final lookup -> 'not run (power)'. ``stage2_early_alpha_ok`` = p < alpha / 4 (strict);
    ``stage2_pass_alpha_over_k`` = ``checks_ok`` and p < alpha / k2 (alpha / 4 while k2 is unknown); the CB14-wide ``stage2-final`` Holm can only add passes."""
    rdir = refuse_if_other_root(Path(hist_root) / FRAME_RUN)
    models = make_models(out_root, rdir / "fit", model_pin=model_pin, rebased_pin=rebased_pin)
    fin = manifest_done(subset_files(rdir, "S2")["manifest"], STAGE2_STATUS_FINAL)
    if not fin:
        raise NotNow(f"S Stage 2: the window has not closed (q0321 closes it at >= {S2_STOP_EVENTS} resolved events with a unit or at the cap {T14_S2_CAP}) or the {S2_OUTCOME_WAIT_D}-day "
                     "post-close outcome wait is not over; pending (never analysed with outcomes frozen at the closing pass)")
    store = subset_files(rdir, "S2")["frame"].parent / "fetch_partial.jsonl"
    prog = stage2_progress(rdir, models["base"], store)
    n_ev = prog["resolved_events_with_unit"]
    data = load_dataset(rdir, ("S2",), job="rep")
    late = late_overlap_s(Path(hist_root), keys_report, data)
    rs = resolution_state(store)
    mids = [m["market_id"] for ms in data["members"].values() for m in ms]
    out: dict = {"label": LABEL_S2, "k2": k2, "n_events_with_unit": prog["events_with_unit"], "n_resolved_events_with_unit": n_ev, "late_overlap": late,
                 "outcome_wait_d": S2_OUTCOME_WAIT_D, "members_unresolved_at_final_lookup": sum(1 for mid in mids if not rs.get(mid, False)), "members": len(mids)}
    if n_ev < REP_CAP_MIN_EVENTS:
        for t in tests:
            out[f"{t}_rep"] = {**not_run_result("not run (power)", f"{t}-rep"), "label": LABEL_S2, "n_events_with_unit": n_ev}
        return out
    ymap = build_ymap(data, c14.open_guarded(subset_files(rdir, "S2")["outcomes"], "rep", ("screen", "rep")))
    for t in tests:
        r = (s1_screen(data, models, ymap, alpha_adv=c14.EARLY_ALPHA2, stage=2, n_draws=n_draws, n_wild=n_wild, placebo=placebo, label=LABEL_S2) if t == "S1"
             else s2_screen(data, models, ymap, alpha_adv=c14.EARLY_ALPHA2, stage=2, n_draws=n_draws, n_wild=n_wild, placebo=placebo, label=LABEL_S2))
        r["stage2_early_alpha_ok"] = c14.early_stage2_ok(r.get("p") if r.get("testable") else None)
        r["stage2_pass_alpha_over_k"] = bool(r.get("checks_ok") and r.get("testable") and r.get("p", 1.0) < (c14.STAGE_ALPHA / k2 if k2 else c14.EARLY_ALPHA2))  # the CB14-wide stage2-final Holm can only add passes
        out[f"{t}_rep"] = r
    return out


# =====================================================================================================================================================
# Fetch jobs: shared machinery (resumable, one event / one transcript in memory at a time)
# =====================================================================================================================================================


def _open(hist_root: Path, run_id: str, transport, *, kind: str, label: str, params: dict, rules_sha: str, disk_cap: int, rps: float, factbase_rps: float, budget_min: float | None,
          now: float | None, sleep, live_check, wall_clock, snapshot_root, health_check, manifest_name: str | None = None):
    """(run, factbase limiter). Polymarket requests use ``fr.lim`` (<= 2 rps); Factbase requests use a second slower limiter (<= 0.5 rps) on the same transport / policy / sleep / yield."""
    fr = cm.open_run(Path(hist_root), run_id, transport, allowed_run_id=run_id, kind=kind, label=label, params={"evidence_role": c14.EVIDENCE_ROLE_HIST, **params}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    if manifest_name and manifest_name != "manifest.json":
        fr.mpath = fr.rdir / manifest_name
        fr.prior = json.loads(fr.mpath.read_text()) if fr.mpath.exists() else {}
        fr.counts = dict(fr.prior.get("counts") or {})
        fr.file_sha256 = dict(fr.prior.get("file_sha256") or {})
        fr.extra_state = dict(fr.prior.get("state") or {})
    fb = hb.Limiter(fr.pol, rps=min(factbase_rps, 0.5), sleep=sleep, live_check=live_check)
    return fr, fb


def _stop_result(fr, why: str) -> dict:
    mm = fr.manifest(why, {"transient": True})
    mm["status"] = IN_PROGRESS
    return mm


def _wcsv(fr, path: Path, header: list[str], rows: Iterable[list], *, guarded: bool = False) -> None:
    c14.assert_clean_columns(header, guarded=guarded)
    if guarded and Path(path).name not in c14.GUARDED_NAMES:
        raise Refused(f"{Path(path).name} is not a guarded file name")
    fr.budget.write_gz_csv(path, header, rows)
    fr.record_file(path)


def manifest_done(path: Path, status: str) -> dict | None:
    p = Path(path)
    man = json.loads(p.read_text()) if p.exists() else {}
    return man if man.get("status") == status and man.get("complete") is True and not man.get("stopped") else None


def frame_manifest(rdir: Path) -> dict | None:
    return manifest_done(Path(rdir) / "manifest.json", FRAME_STATUS)


def _partial_lines(path: Path) -> Iterable[dict]:
    if not Path(path).exists():
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def _repair_tail(path: Path) -> None:
    """A crash mid-line must not glue the next record onto the broken one."""
    p = Path(path)
    if p.exists() and p.stat().st_size:
        with p.open("rb+") as fh:
            fh.seek(-1, 2)
            if fh.read(1) != b"\n":
                fh.write(b"\n")


def _append(path: Path, rec: dict) -> None:
    with Path(path).open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")


def walk_factbase(fb, part: Path, stop_epoch: float, stop_fn, max_pages: int = FACTBASE_MAX_PAGES) -> dict:
    """Resumable newest-first walk of the Factbase search listing until a page holds a record older than ``stop_epoch`` (or the archive ends). Only records of keyword speakers are kept (public
    metadata: date, type, title, speaker id, url). Returns {rows, reached, pages, n_other, stopped}."""
    pages = {rec["page"]: rec for rec in _partial_lines(part)}
    _repair_tail(part)
    reached, stopped, page = False, None, 1
    while page <= max_pages:
        if page not in pages:
            stopped = stop_fn()
            if stopped:
                break
            st, data = fb.get(FACTBASE_SEARCH, factbase_search_params(page))
            if st != 200 or not isinstance(data, dict):
                raise cm.ApiError(f"factbase search status {st}")
            rows = parse_search_page(data)
            keep = [r for r in rows if r["speaker_key"]]
            ts = [r["date_epoch"] for r in rows]
            rec = {"page": page, "n_raw": len(data.get("data") or []), "rows": keep, "n_other": len(rows) - len(keep), "oldest": min(ts) if ts else None}
            _append(part, rec)
            pages[page] = rec
        rec = pages[page]
        if rec["n_raw"] == 0 or (rec["oldest"] is not None and rec["oldest"] < stop_epoch):
            reached = True
            break
        page += 1
    seen, rows = set(), []
    for pg in sorted(pages):
        if pg > page:
            continue
        for r in pages[pg]["rows"]:
            if r["record_id"] not in seen:
                seen.add(r["record_id"])
                rows.append(r)
    return {"rows": rows, "reached": reached, "pages": len(pages), "n_other": sum(p["n_other"] for p in pages.values()), "stopped": stopped}


def fit_window_counts(records: list[dict]) -> dict[str, int]:
    """Per speaker key: records of a mapped type dated in the fit window (the metadata count of the primary-speaker rule at frame time)."""
    lo, hi = _ep(T14_FIT[0]), _ep(T14_FIT[1])
    cnt: Counter = Counter()
    for r in records:
        if lo <= r["date_epoch"] < hi and r["type"] in TYPE_CLASS:
            cnt[r["speaker_key"]] += 1
    return dict(cnt)


def classify_events(parsed: list[tuple[dict, list[dict]]], keys_by_subset: dict[str, dict], series_dates: dict[str, list[float]], primary: set[str], records: list[dict]) -> dict:
    """Statuses (two passes: the series-date key also uses the starts of walked events dropped by a market / event / neg-risk key) and the transcript map of the kept events."""
    sd = {k: list(v) for k, v in series_dates.items()}
    empty = {"market": set(), "event": set(), "neg_risk_market": set(), "series": set()}
    for row, mems in parsed:
        keys = keys_by_subset.get(row["subset"], empty)
        row["key_series_cf"] = int(bool(row["series_id"] and row["series_id"] in keys["series"]))
        if row["series_id"] and math.isfinite(row["start_epoch"]) and key_drop(row, mems, keys):
            sd.setdefault(row["series_id"], []).append(row["start_epoch"])
    by_sp: dict[str, list[dict]] = {}
    for r in records:
        by_sp.setdefault(r["speaker_key"], []).append(r)
    maps: dict[str, dict] = {}
    for row, mems in parsed:
        row["status"], row["status_source"] = event_status_s(row, mems, keys_by_subset.get(row["subset"], empty), sd, primary)
        if row["status"] == "kept":
            m = map_event(row["title"], row["start_epoch"], row["speaker_key"], by_sp.get(row["speaker_key"], []))
            rec = m["record"] or {}
            maps[row["event_id"]] = {"event_id": row["event_id"], "subset": row["subset"], "speaker_key": row["speaker_key"], "type_keys": row["type_keys"], "status": m["status"], "reason": m["reason"],
                                     "n_candidates": m["n_candidates"], "record_id": rec.get("record_id", ""), "record_url": rec.get("url", ""), "record_date": rec.get("date", ""),
                                     "record_type": rec.get("type", ""), "record_title": rec.get("title", "")}
    return {"maps": maps, "series_dates_total": sum(len(v) for v in sd.values())}


def _rows(dicts: Iterable[dict], cols: list[str]) -> Iterable[list]:
    for d in dicts:
        yield ["" if d[c] is None or (isinstance(d[c], float) and not math.isfinite(d[c])) else d[c] for c in cols]


def load_series_dates_optional(keys_path: Path, rep: dict) -> tuple[dict[str, list[float]], str]:
    """The series-date key's excluded-event starts, from ``exclusion_series_dates.csv.gz`` next to the key file when q0302 produced one (sha256-verified by the CB12 loader); else only the
    starts of walked events dropped by a market / event key apply (recorded in the frame report: the key is partial, never silently off)."""
    p = Path(keys_path).with_name(c14.c12.SERIES_DATES_NAME)
    if p.exists():
        return c14.c12.load_series_dates(Path(keys_path), rep), "file"
    return {}, "in-frame only (no exclusion_series_dates.csv.gz next to the key file)"


def write_audit_sample(out_root: Path, rows: list[dict]) -> Path:
    out_root = c14.require_output_root(Path(out_root))
    out_root.mkdir(parents=True, exist_ok=True)
    c14.assert_clean_columns(AUDIT_COLUMNS)
    p = out_root / "s_map_audit_sample.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(AUDIT_COLUMNS)
        for r in rows:
            w.writerow([r[c] for c in AUDIT_COLUMNS])
    return p


def s_frame(hist_root: Path, transport, *, rules_sha: str, exclusion_keys_path: Path, now: float, out_root: Path | None = None, rps: float = 2.0, factbase_rps: float = 0.5,
            disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time,
            snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None,
            s_exempt_path: Path | None = None, registry_path: Path | None = None) -> dict:
    """q0312. Tag-100343 one-week end-date walk over [2024-11-01, 2026-03-01) (whitelisted fields; NO outcome stored; HOLDOUT-window events are discarded unseen), statuses (sports pins,
    occasion, keys with the N deviation, members, Q&A / section, primary speaker), the Factbase record walk and transcript map, subsets P / N and the blind GS0 audit sample."""
    rdir = c14.require_output_root(Path(hist_root) / FRAME_RUN)
    out_root = Path(out_root) if out_root is not None else c14.CB14_DIR
    st = c14.stall_of(rdir)
    if st:
        return st
    done = frame_manifest(rdir)
    if done:
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    pins = verify_pins(registry_path)
    ids, sets, krep, ksha = c14.load_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c14.UNVERIFIED:
        return c14.write_stall(rdir, c14.c9.STALL_DISJOINTNESS, "exclusion keys: more than 2% of ids without metadata")
    exempt = load_exempt(Path(s_exempt_path) if s_exempt_path else Path(exclusion_keys_path).with_name("s_exempt_ids.csv.gz"))
    series_file, sd_source = load_series_dates_optional(Path(exclusion_keys_path), krep)
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    rdir.mkdir(parents=True, exist_ok=True)
    fr, fb = _open(Path(hist_root), FRAME_RUN, transport, kind="cb14_s_frame", label="CB14-S frame", params={"tag_id": TAG_ID, "windows": [list(T14_P), list(T14_N)], "exclusion_keys_sha256": ksha},
                   rules_sha=rules_sha, disk_cap=disk_cap, rps=rps, factbase_rps=factbase_rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                   snapshot_root=snapshot_root, health_check=health_check)
    stats: dict = {}
    seen: set[str] = set()
    parsed: list[tuple[dict, list[dict]]] = []
    n_holdout = 0
    try:
        for a, b in week_windows(_ep(T14_P[0]), _ep(T14_N[1])):
            why = fr.stop_reason(should_stop)
            if why:
                return _stop_result(fr, why)
            for ev in walk_window_s(fr.lim, a, b, stats=stats):
                p = parse_event_s(ev)
                if p is None or p[0]["event_id"] in seen:
                    continue
                seen.add(p[0]["event_id"])
                if p[0]["subset"] == "HOLDOUT":
                    n_holdout += 1  # refused by date: nothing of it is stored
                    continue
                parsed.append(p)
        part = fr.rdir / "records_partial.jsonl"
        wk = walk_factbase(fb, part, _ep(T14_FIT[0]), lambda: fr.stop_reason(should_stop))
    except (cm.ApiError, RuntimeError) as exc:
        return _stop_result(fr, f"fetch_failed: {exc}"[:200])
    if wk["stopped"]:
        return _stop_result(fr, wk["stopped"])
    if not wk["reached"]:  # a declared source stall (counted "not testable (source)" by the runner), never a silently partial record list
        return c14.write_stall(rdir, c14.c9.STALL_NOT_RUN_SOURCE, f"the Factbase search walk stopped after {wk['pages']} pages (cap {FACTBASE_MAX_PAGES}) before reaching the fit-window start {T14_FIT[0]}")
    records = wk["rows"]
    counts_fit = fit_window_counts(records)
    primary = set(primary_speakers(counts_fit))
    keys_by = {tag: effective_keys(ids, sets, exempt, tag) for tag in SUBSETS}
    cl = classify_events(parsed, keys_by, series_file, primary, records)
    rows = sorted((r for r, _ in parsed), key=lambda r: r["event_id"])
    kept = {r["event_id"] for r in rows if r["status"] == "kept"}
    mems = [m for r, ms in sorted(parsed, key=lambda x: x[0]["event_id"]) if r["event_id"] in kept for m in sorted(ms, key=lambda x: x["market_id"])]
    map_rows = [cl["maps"][e] for e in sorted(cl["maps"])]
    report = {"pins": pins, "splits_of_capped_windows": stats.get("splits", 0), "holdout_window_events_discarded": n_holdout, "series_date_key": sd_source,
              "series_dates_events_total": cl["series_dates_total"], "factbase": {"pages": wk["pages"], "reached_fit_start": wk["reached"], "records_kept": len(records), "other_speaker_records": wk["n_other"]},
              "fit_window_counts_by_speaker": counts_fit, "primary_speakers": sorted(primary), "by_status": dict(Counter(f"{r['subset']}:{r['status']}" for r in rows)),
              "key_drop_source": dict(Counter(r["status_source"] for r in rows if r["status"] == "dropped:key")), "sports_by": {"tag": sum(r["sports_tag"] for r in rows), "regex": sum(r["sports_re"] for r in rows)},
              "full_series_counterfactual_drops": sum(r["key_series_cf"] for r in rows if r["status"] in ("kept", "dropped:key")),
              "map_status": dict(Counter(f"{m['status']}:{m['reason']}" for m in map_rows)), "n_kept_members": len(mems)}
    try:
        _wcsv(fr, rdir / "frame.csv.gz", EVENT_COLUMNS, _rows(rows, EVENT_COLUMNS))
        _wcsv(fr, rdir / "members.csv.gz", MEMBER_COLUMNS, _rows(mems, MEMBER_COLUMNS))
        _wcsv(fr, rdir / "map.csv.gz", MAP_COLUMNS, _rows(map_rows, MAP_COLUMNS))
        _wcsv(fr, rdir / "records.csv.gz", RECORD_COLUMNS, _rows(sorted(records, key=lambda r: (r["date_epoch"], r["record_id"])), RECORD_COLUMNS))
        (rdir / "frame_report.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=float))
        fr.record_file(rdir / "frame_report.json")
        audit = gs0_sample(map_rows_with_titles(map_rows, rows))
        write_audit_sample(out_root, audit)
        fr.counts.update(events=len(rows), kept=len(kept), mapped=sum(1 for m in map_rows if m["status"] == "mapped"), members_kept=len(mems), records=len(records), audit_sample=len(audit))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    (fr.rdir / "records_partial.jsonl").unlink(missing_ok=True)
    m = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m["status"] = FRAME_STATUS
    return m


def map_rows_with_titles(map_rows: list[dict], frame_rows: list[dict]) -> list[dict]:
    """Map rows joined with the event title and start (the blind audit sample's columns)."""
    by = {r["event_id"]: r for r in frame_rows}
    out = []
    for m in map_rows:
        e = by[m["event_id"]]
        out.append({**m, "event_title": e["title"], "start_utc": c14.iso(e["start_epoch"]), "record_date": m["record_date"], "record_title": m["record_title"], "record_type": m["record_type"]})
    return out


# =====================================================================================================================================================
# q0313 fit transcripts, q0314 the frozen position model
# =====================================================================================================================================================


def fit_term_matchers(members_path: Path) -> dict[str, dict]:
    """One matcher per normalised term of the frame members (frame text only): the union of its variants with the default rule booleans."""
    var: dict[str, list[str]] = {}
    for r in c14.read_csv_gz(members_path):
        t = r["term_norm"]
        if not t:
            continue
        lst = var.setdefault(t, [])
        for v in str(r["variants"]).split("|"):
            if v and v not in lst:
                lst.append(v)
    return {t: make_matcher(v) for t, v in sorted(var.items())}


def fetch_transcript(fb, url: str, matchers: dict[str, dict], speaker_key: str) -> dict:
    """One Factbase transcript page (about 2 MB) -> reduced numbers; the page and its text are dropped on return. Status 'ok', 'not_found' or 'not_timestamped'."""
    stt, body = c14.get_text(fb, urljoin(FACTBASE_BASE, url), {})
    if stt != 200:
        return {"status": "not_found", "n_stamps": 0, "last_s": None, "base_s": None, "first_seg_s": None, "first": {}}
    segs = parse_transcript_html(body)
    del body
    red = reduce_transcript(segs, matchers, speaker_key)
    del segs
    return {"status": "ok" if red["n_stamps"] >= TIMESTAMPED_MIN_STAMPS else "not_timestamped", **{k: red[k] for k in ("n_stamps", "last_s", "base_s", "first_seg_s", "first")}}


def s_fit_fetch(hist_root: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, factbase_rps: float = 0.5, disk_cap: int = int(FIT_OUTPUT_CAP_GB * 1024**3),
                budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
                data_dumps: Path | None = None, data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0313 (resumable, one 2 MB page in memory at a time): the Factbase transcripts of primary-speaker candidates dated in the fit window, reduced at parse to per-term first-mention
    offsets and the last offset (term list from frame text only). Nothing but numbers is stored. A fetch whose status is not '*_complete' is pending and never analysed partially."""
    rdir = c14.require_output_root(Path(hist_root) / FRAME_RUN)
    fdir = rdir / "fit"
    st = c14.stall_of(rdir)
    if st:
        return st
    if not frame_manifest(rdir):
        raise NotNow("q0313 waits for q0312 (s_frame) to finish")
    done = manifest_done(fdir / "manifest.json", FIT_FETCH_STATUS)
    if done:
        return {"stopped": None, "status": FIT_FETCH_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(fdir)
    if term:
        return term
    c14.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr, fb = _open(Path(hist_root), FIT_RUN, transport, kind="cb14_s_fit_fetch", label="CB14-S fit transcripts", params={"fit_window": list(T14_FIT)}, rules_sha=rules_sha, disk_cap=disk_cap,
                   rps=rps, factbase_rps=factbase_rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    records = [{**r, "date_epoch": float(r["date_epoch"])} for r in c14.read_csv_gz(rdir / "records.csv.gz")]
    primary = set(primary_speakers(fit_window_counts(records)))
    lo, hi = _ep(T14_FIT[0]), _ep(T14_FIT[1])
    todo = sorted((r for r in records if r["speaker_key"] in primary and r["type"] in TYPE_CLASS and lo <= r["date_epoch"] < hi), key=lambda r: (r["date_epoch"], r["record_id"]))
    matchers = fit_term_matchers(rdir / "members.csv.gz")
    part = fdir / "transcripts_partial.jsonl"
    have = {rec["record_id"] for rec in _partial_lines(part)}
    _repair_tail(part)
    try:
        for r in todo:
            if r["record_id"] in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                fr.counts["factbase_requests_session"] = fb.requests
                return _stop_result(fr, why)
            try:
                red = fetch_transcript(fb, r["url"], matchers, r["speaker_key"])
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[r["record_id"]] = fails.get(r["record_id"], 0) + 1
                if fails[r["record_id"]] < MAX_ITEM_ATTEMPTS:
                    return _stop_result(fr, f"fetch_failed {r['record_id']}: {exc}"[:200])
                red = {"status": "not_found", "n_stamps": 0, "last_s": None, "base_s": None, "first_seg_s": None, "first": {}}
            _append(part, {"record_id": r["record_id"], "speaker_key": r["speaker_key"], "type": r["type"], "date": r["date"], **red})
            have.add(r["record_id"])
        recs, offs = [], []
        meta = {r["record_id"]: r for r in todo}
        for rec in sorted(_partial_lines(part), key=lambda x: x["record_id"]):
            if rec["record_id"] not in meta:
                continue
            base = rec["base_s"] or 0
            last = rec["last_s"]
            recs.append([rec["record_id"], rec["speaker_key"], rec["type"], type_class_of(rec["type"]), rec["date"], rec["status"], rec["n_stamps"], "" if last is None else last, base,
                         "" if rec["first_seg_s"] is None else rec["first_seg_s"], "" if last is None else max(0, last - base), int(rec["status"] == "ok")])
            for term_, off in sorted(rec["first"].items()):
                offs.append([rec["record_id"], term_, off, max(0, off - base)])
        _wcsv(fr, fdir / "records.csv.gz", FIT_RECORD_COLUMNS, recs)
        _wcsv(fr, fdir / "offsets.csv.gz", FIT_OFFSET_COLUMNS, offs)
        fr.counts.update(records=len(recs), timestamped=sum(r[-1] for r in recs), offsets=len(offs), terms=len(matchers), factbase_requests_session=fb.requests)
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    part.unlink(missing_ok=True)
    m = fr.manifest(None, {"complete": True, "status": FIT_FETCH_STATUS})
    m["status"] = FIT_FETCH_STATUS
    return m


def s_fit(hist_root: Path, *, out_root: Path) -> dict:
    """q0314 (no network): the frozen position model (shrinkage 10 to the pooled curve, 1-minute grid to 180 min, per speaker, type class and term) from the fit offsets only, and the re-based
    second model. Refuses if ANY price, print, guarded or target file already exists under ``h14_speech``. Returns the sha256 of both files for the coordinator to pin in part S."""
    rdir = c14.require_output_root(Path(hist_root) / FRAME_RUN)
    out_root = c14.require_output_root(Path(out_root))
    bad = [p.relative_to(rdir).as_posix() for pat in ("prices_*.csv.gz", "tx_*.csv.gz", "markets_*.csv.gz", "manifest_*.json", "guarded_*/*", "stage2/*") for p in rdir.glob(pat)]
    if bad:
        raise Refused(f"q0314 refuses: price / print / guarded / target files already exist under h14_speech ({bad[:4]}); the model is fitted before any of them is read")
    fdir = rdir / "fit"
    c14.require_complete(fdir, (FIT_FETCH_STATUS,), "q0313 (s_fit_fetch)")
    fit = load_fit_transcripts(fdir)
    out: dict = {"status": FIT_STATUS, "complete": True, "n_fit_records": len(fit), "files": {}}
    for name, rebased in ((MODEL_FILE, False), (MODEL_REBASED_FILE, True)):
        model = fit_model(fit, rebased=rebased)
        text = model_text(model)
        p = out_root / name
        if p.exists() and p.read_text() != text:
            raise Refused(f"{p} exists with different content: a fitted model is never rewritten")
        out_root.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        out["files"][name] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "speakers": sorted(model["speakers"]), "below_minimum": model["speakers_below_minimum"]}
    out["model_sha256"] = out["files"][MODEL_FILE]["sha256"]
    out["model_rebased_sha256"] = out["files"][MODEL_REBASED_FILE]["sha256"]
    return out


# =====================================================================================================================================================
# q0317 / q0318 / q0321: target data (transcript reduction, 1-minute prices, transactions, Gamma outcomes to the guarded file)
# =====================================================================================================================================================


def _target_items(rdir: Path, tag: str, usable_months: set[str] | None = None) -> list[dict]:
    """The kept, mapped events of a subset with their members (event_id order). P events in a month whose 1-minute availability failed in the smoke are dropped (counted by the pre-gate)."""
    f = subset_files(rdir, tag)
    frame = read_frame(rdir, tag)
    maps = {r["event_id"]: r for r in c14.read_csv_gz(f["map"])}
    mem: dict[str, list[dict]] = {}
    for r in c14.read_csv_gz(f["members"]):
        mem.setdefault(r["event_id"], []).append(r)
    items = []
    for r in sorted(frame, key=lambda x: x["event_id"]):
        eid = r["event_id"]
        if r["status"] != "kept" or maps.get(eid, {}).get("status") != "mapped" or eid not in mem or not maps[eid].get("record_url"):
            continue
        if tag == "P" and usable_months is not None and r["month"] not in usable_months:
            continue
        items.append({"ev": r, "map": maps[eid], "members": sorted(mem[eid], key=lambda m: m["market_id"])})
    return items


def _member_matchers(members: list[dict]) -> dict[str, dict]:
    """One matcher per member (keyed by market id): its term variants with its own rule booleans (plural, possessive, compound)."""
    out = {}
    for m in members:
        vs = [v for v in str(m["variants"]).split("|") if v]
        if vs:
            out[m["market_id"]] = make_matcher(vs, bool(int(float(m["plural"] or 0))), bool(int(float(m["possessive"] or 0))), bool(int(float(m["compound"] or 0))))
    return out


def _outcome_row(m: dict, event_id: str, yes_index: int) -> dict:
    statuses = m.get("umaResolutionStatuses")
    return {"market_id": str(m["id"]), "event_id": event_id, "yes_index": yes_index, "outcome_prices": json.dumps(c14.c12.listish(m.get("outcomePrices"))),
            "uma_status": str(m.get("umaResolutionStatus") or (statuses if statuses else ""))}


def _lookup_outcomes(lim, batch: list[tuple[str, str, int]]) -> list[dict]:
    """Gamma outcomes for ``(market_id, event_id, yes_index)`` triples (closed=true first, the rest without it). A market Gamma does not return is a row with an empty outcome (scored 0.5, unclean)."""
    ids = [b[0] for b in batch]
    found: dict[str, dict] = {}
    for closed in (True, False):
        want = [i for i in ids if i not in found]
        if not want:
            break
        params: dict = {"id": want, "limit": GAMMA_LOOKUP_PER_REQUEST}
        if closed:
            params["closed"] = "true"
        st, data = lim.get(hb.GAMMA_MARKETS, params)
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma markets lookup status {st}")
        for m in data:
            if isinstance(m, dict) and m.get("id") is not None and str(m["id"]) in want:
                found[str(m["id"])] = m
    out = []
    for mid, eid, yi in batch:
        out.append(_outcome_row(found[mid], eid, yi) if mid in found else {"market_id": mid, "event_id": eid, "yes_index": yi, "outcome_prices": "", "uma_status": "not_found"})
    return out


def _fetch_market(fr, m: dict, start: float) -> dict:
    """One member: 1-minute prices-history over [start - 30 min, start + 5 h] and the newest-first prints (<= 2 pages) aggregated to transactions in that span. Raises on a failed call."""
    lo, hi = start - FETCH_BEFORE_S, start + FETCH_AFTER_S
    stp, data = fr.lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(lo), "endTs": int(hi), "fidelity": FIDELITY})
    if stp != 200:
        raise cm.ApiError(f"prices-history status {stp}")
    pts = [[int(h["t"]), float(h["p"])] for h in ((data or {}).get("history") or []) if isinstance(h, dict) and "t" in h and "p" in h and lo <= float(h["t"]) <= hi]
    prints, info = c14.c12.fetch_prints_paged(fr.lim, m["condition_id"], lo, limit=c14.DATA_PAGE_LIMIT, pages=c14.DATA_PAGES)
    rows, _ = c14.c12.aggregate_transactions(prints, int(float(m["yes_index"])))
    del prints
    tx = [[r["ts"], r["price"], r["size"], r["n_fills"]] for r in rows if lo <= r["ts"] <= hi]
    ok = c14.c12.reach_ok(info, lo)
    return {"k": "mk", "market_id": m["market_id"], "event_id": m["event_id"], "status": "ok", "points": pts, "tx": tx, "n_points": len(pts), "n_prints": info["n_prints"], "n_tx": len(tx),
            "oldest_ts": None if not math.isfinite(info["oldest_ts"]) else info["oldest_ts"], "truncated": int(bool(info["truncated"])), "reach_t0": int(ok)}


def resolved_flag(row: dict) -> bool:
    """True iff Gamma's row is a resolved outcome (clean 1/0 or 50-50). Only this boolean leaves the guarded store (the Stage-2 stop rule counts resolutions, never values)."""
    if not row.get("outcome_prices"):
        return False
    try:
        return outcome_y(row["outcome_prices"], row.get("uma_status"), int(float(row.get("yes_index") or 0)))[1] != "unclean"
    except (ValueError, TypeError, IndexError):
        return False


def resolution_state(part: Path) -> dict[str, bool]:
    """The latest resolution flag per market from the fetch store's 'rs' records."""
    out: dict[str, bool] = {}
    for rec in _partial_lines(part):
        if rec.get("k") == "rs":
            out[str(rec["market_id"])] = bool(rec.get("resolved"))
    return out


def _fetch_targets(fr, fb, items: list[dict], part: Path, should_stop, *, oc_part: Path, refetch_unresolved: bool = False) -> str | None:
    """Resumable fetch, one event / one member in memory at a time. Returns a stop reason (transient) or None when every item is complete. Record kinds in ``part``: 'tr' (reduced
    transcript, numbers only), 'mk' (one member's points and transactions), 'rs' (a market's resolution flag, no value). Gamma outcome rows ('oc') go ONLY to ``oc_part`` inside the
    subset's guarded directory. With ``refetch_unresolved`` (Stage 2, weekly) every market whose last flag is unresolved is looked up again (an unresolved word is never frozen at 0.5)."""
    _repair_tail(part)
    _repair_tail(oc_part)
    have_tr, have_mk = set(), set()
    for rec in _partial_lines(part):
        if rec.get("k") == "tr":
            have_tr.add(rec.get("event_id"))
        elif rec.get("k") == "mk":
            have_mk.add(rec.get("market_id"))
    rs_state = resolution_state(part)
    fails = fr.extra_state.setdefault("fails", {})

    def attempt(key: str, exc) -> bool:
        fails[key] = fails.get(key, 0) + 1
        return fails[key] < MAX_ITEM_ATTEMPTS

    for it in items:
        ev, mp, mems = it["ev"], it["map"], it["members"]
        eid = ev["event_id"]
        if eid not in have_tr:
            why = fr.stop_reason(should_stop)
            if why:
                return why
            try:
                red = fetch_transcript(fb, mp["record_url"], _member_matchers(mems), mp["speaker_key"])
            except (cm.ApiError, RuntimeError) as exc:
                if attempt("tr:" + eid, exc):
                    return f"fetch_failed transcript {eid}: {exc}"[:200]
                red = {"status": "not_found", "n_stamps": 0, "last_s": None, "base_s": None, "first_seg_s": None, "first": {}}
            _append(part, {"k": "tr", "event_id": eid, "record_url": mp["record_url"], **red})
            have_tr.add(eid)
        for m in mems:
            mid = m["market_id"]
            if mid in have_mk:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return why
            try:
                rec = _fetch_market(fr, m, float(ev["start_epoch"]))
            except (cm.ApiError, RuntimeError) as exc:
                if attempt("mk:" + mid, exc):
                    return f"fetch_failed {mid}: {exc}"[:200]
                rec = {"k": "mk", "market_id": mid, "event_id": eid, "status": UNAVAILABLE_NETWORK, "points": [], "tx": [], "n_points": 0, "n_prints": 0, "n_tx": 0, "oldest_ts": None,
                       "truncated": 1, "reach_t0": 0}
            _append(part, rec)
            have_mk.add(mid)
            del rec
    todo = [(m["market_id"], it["ev"]["event_id"], int(float(m["yes_index"]))) for it in items for m in it["members"]
            if m["market_id"] not in rs_state or (refetch_unresolved and not rs_state[m["market_id"]])]
    for i in range(0, len(todo), GAMMA_LOOKUP_PER_REQUEST):
        batch = todo[i:i + GAMMA_LOOKUP_PER_REQUEST]
        why = fr.stop_reason(should_stop)
        if why:
            return why
        try:
            rows = _lookup_outcomes(fr.lim, batch)
        except (cm.ApiError, RuntimeError) as exc:
            if attempt(f"oc:{i}", exc):
                return f"fetch_failed outcomes batch {i}: {exc}"[:200]
            rows = [{"market_id": a, "event_id": b, "yes_index": c, "outcome_prices": "", "uma_status": "unavailable (network)"} for a, b, c in batch]
        oc_part.parent.mkdir(parents=True, exist_ok=True)
        for r in rows:
            _append(oc_part, {"k": "oc", **r})
            _append(part, {"k": "rs", "market_id": r["market_id"], "resolved": resolved_flag(r)})
    return None


def _store(part: Path, kind: str) -> dict[str, dict]:
    key = "event_id" if kind == "tr" else "market_id"
    return {r[key]: r for r in _partial_lines(part) if r.get("k") == kind}


def oc_partial(rdir: Path, tag: str) -> Path:
    """The outcome store of a subset: inside its guarded directory (never next to the clean files)."""
    return subset_files(rdir, tag)["guarded"] / "outcomes_partial.jsonl"


def _write_target_outputs(fr, rdir: Path, tag: str, items: list[dict], part: Path) -> dict:
    """Write the subset's files from the partial store: prices / transactions / markets (clean columns), guarded transcripts + mentions, guarded outcomes (the LATEST lookup per market)."""
    f = subset_files(rdir, tag)
    trs, mks, ocs = _store(part, "tr"), _store(part, "mk"), _store(oc_partial(rdir, tag), "oc")
    mids = [m["market_id"] for it in items for m in it["members"]]
    _wcsv(fr, f["prices"], PRICE_COLUMNS, ([mid, a, b] for mid in mids if mid in mks for a, b in mks[mid]["points"]))
    _wcsv(fr, f["tx"], TX_COLUMNS, ([mid, *row] for mid in mids if mid in mks for row in mks[mid]["tx"]))
    _wcsv(fr, f["markets"], MARKET_COLUMNS, ([mks[mid][c] if mks[mid][c] is not None else "" for c in MARKET_COLUMNS] for mid in mids if mid in mks))
    g = f["guarded"]
    evs = [it["ev"]["event_id"] for it in items if it["ev"]["event_id"] in trs]
    _wcsv(fr, g / "transcripts.csv.gz", TRANSCRIPT_COLUMNS, ([trs[e][c] if trs[e].get(c) is not None else "" for c in TRANSCRIPT_COLUMNS] for e in evs))
    ment = []
    for it in items:
        t = trs.get(it["ev"]["event_id"])
        if t and t["status"] == "ok":
            ment += [[it["ev"]["event_id"], m["market_id"], t["first"].get(m["market_id"], "")] for m in it["members"]]
    _wcsv(fr, g / "mentions.csv.gz", MENTION_COLUMNS, ment)
    _wcsv(fr, f["outcomes"], OUTCOME_COLUMNS, ([ocs[mid][c] for c in OUTCOME_COLUMNS] for mid in mids if mid in ocs), guarded=True)
    stat = Counter(mks[mid]["status"] for mid in mids if mid in mks)
    return {"events": len(items), "transcripts_ok": sum(1 for e in evs if trs[e]["status"] == "ok"), "transcripts_not_ok": sum(1 for e in evs if trs[e]["status"] != "ok"), "members": len(mids),
            "markets_ok": stat["ok"], "markets_unavailable_network": stat[UNAVAILABLE_NETWORK], "markets_unreached": sum(1 for mid in mids if mid in mks and not mks[mid]["reach_t0"]),
            "points": sum(mks[m]["n_points"] for m in mids if m in mks), "transactions": sum(mks[m]["n_tx"] for m in mids if m in mks)}


def _check_pins(out_root: Path, model_pin: str | None, rebased_pin: str | None) -> dict:
    out_root = Path(out_root)
    return {"model": check_model_pin(out_root / MODEL_FILE, model_pin), "model_rebased": check_model_pin(out_root / MODEL_REBASED_FILE, rebased_pin,
                                                                                                         what="re-based position model")}


def _check_pregate(pregate_path: Path | None) -> None:
    if pregate_path is None:
        return
    p = Path(pregate_path)
    if not p.exists() or json.loads(p.read_text()).get("pass") is not True:
        raise Refused(f"the S pre-fetch gate GSC ({p}) is missing or did not PASS: q0317 / q0318 are never run (not testable (population))")


def s_data(hist_root: Path, transport, *, rules_sha: str, now: float, subset: str, rps: float = 2.0, factbase_rps: float = 0.5, disk_cap: int | None = None, budget_min: float | None = None,
           sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
           data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None, out_root: Path | None = None, model_pin: str | None = None, rebased_pin: str | None = None,
           smoke_path: Path | None = None, pregate_path: Path | None = None, ledger_path: Path | None = None, git=None) -> dict:
    """q0317 (subset 'P') / q0318 (subset 'N'): the target data of the kept, mapped events. Refuses unless the position model is pinned (sha256 in part S) and equals the file; N first
    needs ``T14_S_open`` (NotNow until then) and records whether N is primary (``n_primary_status``). Resumable; no outcome is opened, the Gamma outcomes go to the guarded file only."""
    if subset not in SUBSETS:
        raise Refused(f"subset {subset!r}: one of {SUBSETS}")
    rdir = c14.require_output_root(Path(hist_root) / FRAME_RUN)
    out_root = Path(out_root) if out_root is not None else c14.CB14_DIR
    status = DATA_STATUS_P if subset == "P" else DATA_STATUS_N
    f = subset_files(rdir, subset)
    npr = None
    if subset == "N":
        op = c14.s_open_status(ledger_path, git=git)
        npr = c14.n_primary_status(op, rules_sha, git=git)
    st = c14.stall_of(rdir)
    if st:
        return st
    if not frame_manifest(rdir):
        raise NotNow("q0317 / q0318 wait for q0312 (s_frame) to finish")
    c14.require_complete(rdir / "fit", (FIT_FETCH_STATUS,), "q0313 (s_fit_fetch)")
    _check_pins(out_root, model_pin, rebased_pin)
    _check_pregate(pregate_path)
    done = manifest_done(f["manifest"], status)
    if done:
        return {"stopped": None, "status": status, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    cap = int(DATA_OUTPUT_CAP_GB[subset] * 1024**3) if disk_cap is None else disk_cap
    c14.require_disk(data_dumps, data_dumps_cap_gb, cap, free_fn=free_fn)
    usable = None
    if subset == "P" and smoke_path is not None and Path(smoke_path).exists():
        usable = p_months_usable(json.loads(Path(smoke_path).read_text()))
    items = _target_items(rdir, subset, usable)
    fr, fb = _open(Path(hist_root), FRAME_RUN, transport, kind=f"cb14_s_data_{subset}", label=f"CB14-S data {subset}", params={"subset": subset, "fidelity": FIDELITY, "pages": c14.DATA_PAGES,
                   "window_s": [-FETCH_BEFORE_S, FETCH_AFTER_S]}, rules_sha=rules_sha, disk_cap=cap, rps=rps, factbase_rps=factbase_rps, budget_min=budget_min, now=now, sleep=sleep,
                   live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check, manifest_name=f["manifest"].name)
    part = rdir / f"data_{subset.lower()}_partial.jsonl"
    try:
        why = _fetch_targets(fr, fb, items, part, should_stop, oc_part=oc_partial(rdir, subset))
        fr.counts["factbase_requests_session"] = fb.requests
        if why:
            return _stop_result(fr, why)
        fr.counts.update(_write_target_outputs(fr, rdir, subset, items, part))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    part.unlink(missing_ok=True)
    oc_partial(rdir, subset).unlink(missing_ok=True)
    extra = {"complete": True, "status": status, "n_primary": npr}
    m = fr.manifest(None, extra)
    m["status"] = status
    return m


def _stage2_start(freeze_ts: float | None) -> float:
    if freeze_ts is None or not math.isfinite(freeze_ts):
        raise NotNow("S Stage 2: the S freeze time is not known yet (model_specs/cb14_v1.json); pending")
    return max(float(freeze_ts) + DAY, _ep(T14_S2_FLOOR))


def stage2_keys(rdir: Path, keys_path: Path, rep_exempt: dict | None = None) -> tuple[dict[str, set[str]], dict[str, list[float]], str]:
    """Stage-2 exclusion keys: every id of the exclusion-key file PLUS every event / market / neg-risk / series of CB14's own Stage-1 frame (all rows), no exemption for N's SCREEN ids."""
    ids, sets, krep, ksha = c14.load_keys(Path(keys_path))
    keys = effective_keys(ids, sets, {"market": set(), "event": set(), "series": set(), "neg_risk_market": set()}, "S2")
    sd, src = load_series_dates_optional(Path(keys_path), krep)
    sd = {k: list(v) for k, v in sd.items()}
    for r in c14.read_csv_gz(Path(rdir) / "frame.csv.gz"):
        keys["event"].add(r["event_id"])
        if r["series_id"]:
            keys["series"].add(r["series_id"])
            if r["start_epoch"] not in ("", None):
                sd.setdefault(r["series_id"], []).append(float(r["start_epoch"]))
    for r in c14.read_csv_gz(Path(rdir) / "members.csv.gz"):
        keys["market"].add(r["market_id"])
        if r["neg_risk_market_id"]:
            keys["neg_risk_market"].add(r["neg_risk_market_id"])
    return keys, sd, f"{ksha}|series_dates:{src}"


def s_stage2_data(hist_root: Path, transport, *, rules_sha: str, exclusion_keys_path: Path, now: float, freeze_ts: float | None, rps: float = 2.0, factbase_rps: float = 0.5,
                  disk_cap: int | None = None, budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None,
                  health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None, out_root: Path | None = None, model_pin: str | None = None,
                  rebased_pin: str | None = None) -> dict:
    """q0321 (re-queued weekly): post-freeze mention events (``startTime >= max(S freeze + 1 d, 2026-10-27)``), the same frame / map / model (no refit) / fetch / guards, into ``stage2/`` and
    ``guarded_s2/``. The frame is recomputed from the whole walk each run (cheap); per-event fetches persist in a store and are never repeated. Status ``s_stage2_collecting`` until
    the cap or ``S2_STOP_EVENTS`` resolved events with a unit, then ``s_stage2_window_closed`` (event set fixed; daily outcome re-fetches for ``S2_OUTCOME_WAIT_D`` days,
    ``stage2_post_close``), then ``s_stage2_outcomes_final``."""
    rdir = c14.require_output_root(Path(hist_root) / FRAME_RUN)
    out_root = Path(out_root) if out_root is not None else c14.CB14_DIR
    f = subset_files(rdir, "S2")
    start = _stage2_start(freeze_ts)
    cap_ts = _ep(T14_S2_CAP)
    if now < start:
        raise NotNow(f"S Stage 2 opens at {c14.iso(start)}; pending")
    st = c14.stall_of(rdir)
    if st:
        return st
    if not frame_manifest(rdir):
        raise Refused("S Stage 2 needs the Stage-1 frame (q0312) for the key drops")
    _check_pins(out_root, model_pin, rebased_pin)
    prior_m = json.loads(f["manifest"].read_text()) if f["manifest"].exists() else {}
    final = manifest_done(f["manifest"], STAGE2_STATUS_FINAL)
    if final:
        return {"stopped": None, "status": STAGE2_STATUS_FINAL, "complete": True, "counts": final.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    closed_at = c14.num((prior_m.get("state") or {}).get("closed_at"))
    if math.isfinite(closed_at):  # the window is closed: outcome re-fetches only (no new event), until the fixed post-close wait is over
        return stage2_post_close(hist_root, transport, rdir=rdir, closed_at=closed_at, prior=prior_m, now=now, rules_sha=rules_sha, rps=rps, factbase_rps=factbase_rps,
                                 disk_cap=disk_cap, budget_min=budget_min, sleep=sleep, live_check=live_check, should_stop=should_stop, wall_clock=wall_clock,
                                 snapshot_root=snapshot_root, health_check=health_check, data_dumps=data_dumps, data_dumps_cap_gb=data_dumps_cap_gb, free_fn=free_fn,
                                 out_root=out_root, model_pin=model_pin)
    gate = stage2_weekly_gate(f["manifest"], now, cap_ts)
    if gate is not None:
        return cm.idle(f["frame"].parent, gate, now)
    cap = int(DATA_OUTPUT_CAP_GB["S2"] * 1024**3) if disk_cap is None else disk_cap
    c14.require_disk(data_dumps, data_dumps_cap_gb, cap, free_fn=free_fn)
    pins = verify_pins()
    keys, sd, ksha = stage2_keys(rdir, Path(exclusion_keys_path))
    primary = set(primary_speakers(fit_window_counts([{**r, "date_epoch": float(r["date_epoch"])} for r in c14.read_csv_gz(rdir / "records.csv.gz")])))
    s2dir = f["frame"].parent
    s2dir.mkdir(parents=True, exist_ok=True)
    fr, fb = _open(Path(hist_root), FRAME_RUN, transport, kind="cb14_s_stage2", label="CB14-S Stage 2", params={"window": [c14.iso(start), c14.iso(min(now, cap_ts))], "keys": ksha, "fidelity": FIDELITY},
                   rules_sha=rules_sha, disk_cap=cap, rps=rps, factbase_rps=factbase_rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                   snapshot_root=snapshot_root, health_check=health_check, manifest_name=f["manifest"].name)
    prior_in_progress = (fr.prior or {}).get("status") == IN_PROGRESS
    rec_part = s2dir / "records_partial.jsonl"
    if not prior_in_progress:
        rec_part.unlink(missing_ok=True)  # a new weekly pass reads a fresh newest-first listing; a resumed pass keeps its pages
    store = s2dir / "fetch_partial.jsonl"
    stats: dict = {}
    parsed: list[tuple[dict, list[dict]]] = []
    seen: set[str] = set()
    try:
        for a, b in week_windows(start, min(now, cap_ts)):
            why = fr.stop_reason(should_stop)
            if why:
                return _stop_result(fr, why)
            for ev in walk_window_s(fr.lim, a, b, stats=stats):
                p = parse_event_s(ev)
                if p is None or p[0]["event_id"] in seen or not math.isfinite(p[0]["start_epoch"]) or p[0]["start_epoch"] < start:
                    continue
                p[0]["subset"] = "S2"
                seen.add(p[0]["event_id"])
                parsed.append(p)
        wk = walk_factbase(fb, rec_part, start - 2 * DAY, lambda: fr.stop_reason(should_stop))
    except (cm.ApiError, RuntimeError) as exc:
        return _stop_result(fr, f"fetch_failed: {exc}"[:200])
    if wk["stopped"]:
        return _stop_result(fr, wk["stopped"])
    fr.counts["factbase_reached_window_start"] = int(bool(wk["reached"]))
    records = wk["rows"]
    cl = classify_events(parsed, {"S2": keys}, sd, primary, records)
    rows = sorted((r for r, _ in parsed), key=lambda r: r["event_id"])
    kept = {r["event_id"] for r in rows if r["status"] == "kept"}
    mems = [m for r, ms in sorted(parsed, key=lambda x: x[0]["event_id"]) if r["event_id"] in kept for m in sorted(ms, key=lambda x: x["market_id"])]
    map_rows = [cl["maps"][e] for e in sorted(cl["maps"])]
    try:
        _wcsv(fr, f["frame"], EVENT_COLUMNS, _rows(rows, EVENT_COLUMNS))
        _wcsv(fr, f["members"], MEMBER_COLUMNS, _rows(mems, MEMBER_COLUMNS))
        _wcsv(fr, f["map"], MAP_COLUMNS, _rows(map_rows, MAP_COLUMNS))
        _wcsv(fr, s2dir / "records.csv.gz", RECORD_COLUMNS, _rows(sorted(records, key=lambda r: (r["date_epoch"], r["record_id"])), RECORD_COLUMNS))
        items = _target_items(rdir, "S2")
        why = _fetch_targets(fr, fb, items, store, should_stop, oc_part=oc_partial(rdir, "S2"), refetch_unresolved=True)
        fr.counts.update(events=len(rows), kept=len(kept), mapped=sum(1 for m in map_rows if m["status"] == "mapped"), factbase_requests_session=fb.requests)
        if why:
            return _stop_result(fr, why)
        fr.counts.update(_write_target_outputs(fr, rdir, "S2", items, store))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    prog = stage2_progress(rdir, load_model(Path(out_root) / MODEL_FILE, model_pin), store)
    fr.counts.update(prog)
    closed = bool(now >= cap_ts or prog["resolved_events_with_unit"] >= S2_STOP_EVENTS)
    status = STAGE2_STATUS_CLOSED if closed else STAGE2_STATUS_OPEN
    if closed:  # the event set is fixed from here; outcomes keep being re-fetched for S2_OUTCOME_WAIT_D (stage2_post_close)
        fr.extra_state["closed_at"] = now
        fr.extra_state["closed_by"] = "cap" if now >= cap_ts else "resolved events with a unit"
    m = fr.manifest(None, {"complete": False, "status": status, "pins": pins, "window_start": c14.iso(start), "window_cap": c14.iso(cap_ts), "last_pass_epoch": now,
                           "closed_by": fr.extra_state.get("closed_by") if closed else None,
                           "outcomes_final_due": c14.iso(now + S2_OUTCOME_WAIT_D * DAY) if closed else None})
    m["status"] = status
    return m


def stage2_post_close(hist_root: Path, transport, *, rdir: Path, closed_at: float, prior: dict, now: float, rules_sha: str, rps: float = 2.0, factbase_rps: float = 0.5,
                      disk_cap: int | None = None, budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time,
                      snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c14.DATA_DUMPS_CAP_GB, free_fn=None,
                      out_root: Path | None = None, model_pin: str | None = None) -> dict:
    """q0321 after the closing pass: NO new event; every member whose last lookup was unresolved is looked up again (at most once per ``S2_POST_CLOSE_EVERY_S``) and the guarded outcome
    file is rewritten (latest lookup per market). The first pass at or after ``closed_at + S2_OUTCOME_WAIT_D`` is final (``STAGE2_STATUS_FINAL``, complete): only then may q0322 run.
    An interrupted pass resumes at once."""
    f = subset_files(rdir, "S2")
    due = closed_at + S2_OUTCOME_WAIT_D * DAY
    last = c14.num(prior.get("last_pass_epoch"))
    if prior.get("status") == STAGE2_STATUS_CLOSED and now < due and math.isfinite(last) and now - last < S2_POST_CLOSE_EVERY_S:
        return cm.idle(f["frame"].parent, f"S Stage 2 closed; next outcome re-fetch at {c14.iso(last + S2_POST_CLOSE_EVERY_S)}, final at {c14.iso(due)}", now)
    cap = int(DATA_OUTPUT_CAP_GB["S2"] * 1024**3) if disk_cap is None else disk_cap
    c14.require_disk(data_dumps, data_dumps_cap_gb, cap, free_fn=free_fn)
    pins = verify_pins()
    fr, fb = _open(Path(hist_root), FRAME_RUN, transport, kind="cb14_s_stage2", label="CB14-S Stage 2 (post-close outcomes)", params={k: v for k, v in (prior.get("params") or {}).items() if k in ("window", "keys", "fidelity")},
                   rules_sha=rules_sha, disk_cap=cap, rps=rps, factbase_rps=factbase_rps, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                   snapshot_root=snapshot_root, health_check=health_check, manifest_name=f["manifest"].name)
    store = f["frame"].parent / "fetch_partial.jsonl"
    try:
        items = _target_items(rdir, "S2")
        why = _fetch_targets(fr, fb, items, store, should_stop, oc_part=oc_partial(rdir, "S2"), refetch_unresolved=True)
        if why:
            return _stop_result(fr, why)
        fr.counts.update(_write_target_outputs(fr, rdir, "S2", items, store))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    prog = stage2_progress(rdir, load_model(Path(out_root if out_root is not None else c14.CB14_DIR) / MODEL_FILE, model_pin), store)
    rs = resolution_state(store)
    mids = [m["market_id"] for it in items for m in it["members"]]
    fr.counts.update(prog, members=len(mids), members_unresolved=sum(1 for mid in mids if not rs.get(mid, False)))
    final = bool(now >= due)
    status = STAGE2_STATUS_FINAL if final else STAGE2_STATUS_CLOSED
    m = fr.manifest(None, {"complete": final, "status": status, "pins": pins, "last_pass_epoch": now, "closed_by": fr.extra_state.get("closed_by"), "outcomes_final_due": c14.iso(due),
                           "outcome_wait_d": S2_OUTCOME_WAIT_D})
    m["status"] = status
    return m


def stage2_weekly_gate(manifest_path: Path, now: float, cap_ts: float) -> str | None:
    """None if a Stage-2 pass may run now; else the idle reason. A pass runs at most once per ``S2_PASS_EVERY_S`` (weekly) after the last COMPLETED pass; an interrupted pass
    (``in_progress``) resumes at once; at or after the cap the closing pass runs at once."""
    p = Path(manifest_path)
    prior = json.loads(p.read_text()) if p.exists() else {}
    last = c14.num(prior.get("last_pass_epoch"))
    if prior.get("status") == STAGE2_STATUS_OPEN and math.isfinite(last) and now < cap_ts and now - last < S2_PASS_EVERY_S:
        return f"S Stage 2 is weekly: the next pass is due at {c14.iso(last + S2_PASS_EVERY_S)}"
    return None


def stage2_progress(rdir: Path, model: dict, store: Path) -> dict:
    """The stop-rule count (section 1.2 ``T14_S2_end``): Stage-2 events with a mapped, parsed transcript and >= 1 aligned unit (units need no outcome) whose members have ALL resolved
    (resolution flags of the store; no outcome value is read)."""
    data = load_dataset(Path(rdir), ("S2",), job="census")
    built = build_units(data, model)
    ev_units = sorted(e for e, i in built["events"].items() if i["n_units"] > 0)
    rs = resolution_state(store)
    resolved = [e for e in ev_units if all(rs.get(m["market_id"], False) for m in data["members"][e])]
    return {"events_with_unit": len(ev_units), "resolved_events_with_unit": len(resolved)}


# =====================================================================================================================================================
# Smoke (engineering criteria and counts only)
# =====================================================================================================================================================


def _chk(ok: bool, **detail) -> dict:
    return {"pass": bool(ok), **detail}


def smoke_offline(ctx: dict) -> dict:
    """Fixture checks, no network: refusals (N paths before ``T14_S_open``, HOLDOUT-window date, h12_say, forbidden columns), the registry / regex pins, the causal accessor, the alignment rule."""
    import tempfile  # noqa: PLC0415

    res: dict = {}
    refused = 0
    for bad_end in (_ep(T14_HOLDOUT[0]), _ep(T14_HOLDOUT[1]) - 1):
        try:
            guard_window(bad_end)
        except Refused:
            refused += 1
    try:
        c14.guard_input_path(Path("x/h12_say/events.csv.gz"))
    except Refused:
        refused += 1
    forb = 0
    for col in ("side", "proxyWallet", "user", "outcomePrices", "uma_status", "closedTime"):
        try:
            c14.assert_clean_columns([col])
        except Refused:
            forb += 1
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "LEDGER.md"
        empty.write_text("nothing here\n")
        try:
            c14.s_open_status(empty, git=lambda args: None)
            n_ref = False
        except NotNow:
            n_ref = True
    res["s_guards_fixture"] = _chk(refused == 3 and forb == 6 and n_ref, refused=refused, forbidden=forb, n_refused_before_open=n_ref)
    try:
        pins = verify_pins()
        res["s_pins"] = _chk(bool(pins.get("pins_ok")), registry_file_checked=pins.get("registry_file_checked"))
    except Refused as exc:
        res["s_pins"] = _chk(False, error=str(exc)[:160])
    ct = CausalTranscript(3600.0, {"a": 120.0, "b": 900.0, "c": None})
    seen = ct.offsets_upto(600.0)
    try:
        ct.full_offset("b")
        closed = False
    except Refused:
        closed = True
    res["s_causal_accessor"] = _chk(set(seen) == {"a"} and all(v <= 600.0 for v in seen.values()) and not ct.said_by("b", 600.0) and closed, offsets_after_e=0)
    one = align_fixed_point([(900.0, 100.0)], 1200.0)
    two = align_fixed_point([(900.0, 100.0), (910.0, 105.0)], 1200.0)
    late = align_fixed_point([(1100.0, 100.0), (1150.0, 110.0)], 1200.0)  # J > t - 1 min: ignored
    res["s_alignment_fixture"] = _chk((not one["aligned"]) and two["aligned"] and not late["aligned"], one_anchor=one["aligned"], two_anchors=two["aligned"], late_anchors=late["aligned"])
    return res


def smoke_online(lim, ctx: dict) -> dict:
    """<= 30 requests, counts only (no price, outcome or transcript text is stored): the tag-100343 week walk, one Factbase search + one out-of-window transcript parsed to >= 100 stamps, the
    term parser / matcher on 3 out-of-window events, the 1-minute availability rule on the P months (one out-of-frame event x 2 members per month; a month is usable iff both return rows)."""
    res: dict = {}
    r0 = lim.requests
    fb = ctx.get("factbase_lim") or lim
    a, b = _ep(SMOKE_TAG_WEEK[0]), _ep(SMOKE_TAG_WEEK[1])
    st, data = lim.get(c14.GAMMA_EVENTS, {"closed": "true", "tag_id": TAG_ID, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "order": "id", "ascending": "true", "limit": c14.GAMMA_PAGE, "offset": 0})
    evs = [x for x in data if isinstance(x, dict)] if st == 200 and isinstance(data, list) else []
    parsed = [p for p in (parse_event_s(e) for e in evs) if p]
    res["s_tag_walk"] = _chk(len(parsed) >= 3 and all(p[0]["subset"] == "" for p in parsed), events=len(parsed), http=st)
    # term parser and matcher on 3 out-of-window events
    parsed3 = [p for p in parsed if p[1] and p[0]["n_members"] >= MIN_MEMBERS][:3]
    n_terms = sum(1 for _, ms in parsed3 for m in ms if m["term_norm"])
    n_match_ok = sum(1 for _, ms in parsed3 for m in ms if m["variants"] and make_matcher(m["variants"].split("|"))["phrases"])
    res["s_term_matcher"] = _chk(len(parsed3) >= 3 and n_terms >= 15 and n_match_ok >= n_terms * 0.9, events=len(parsed3), terms=n_terms, matchers=n_match_ok)
    # Factbase: a search page, one out-of-window transcript
    stf, dataf = c14.get_text(fb, FACTBASE_SEARCH, factbase_search_params(1))
    recs = []
    if stf == 200:
        try:
            recs = parse_search_page(json.loads(dataf.decode("utf-8", "replace")))
        except ValueError:
            recs = []
    pick = next((r for r in recs if r["type"] in TYPE_CLASS), None)
    n_stamps = 0
    if pick is not None:
        stt, body = c14.get_text(fb, urljoin(FACTBASE_BASE, pick["url"]), {})
        if stt == 200:
            n_stamps = len(parse_transcript_html(body))
            del body
    res["s_factbase_transcript"] = _chk(bool(recs) and n_stamps >= SMOKE_MIN_STAMPS, records=len(recs), stamps=n_stamps)
    # 1-minute availability on the P months
    months, usable = {}, []
    for mon in P_MONTHS:
        lo = _ep(mon + "-15")
        stw, dw = lim.get(c14.GAMMA_EVENTS, {"closed": "true", "tag_id": TAG_ID, "end_date_min": cm.iso(lo), "end_date_max": cm.iso(lo + 2 * DAY), "order": "id", "ascending": "true", "limit": 40, "offset": 0})
        got = 0
        pe = None
        for e in (dw if stw == 200 and isinstance(dw, list) else []):
            p = parse_event_s(e) if isinstance(e, dict) else None
            if p and math.isfinite(p[0]["start_epoch"]) and len(p[1]) >= AVAIL_MEMBERS_PER_EVENT and (not p[0]["speaker_key"] or p[0]["sports_tag"] or p[0]["sports_re"]):
                pe = p
                break
        if pe is not None:
            s0 = pe[0]["start_epoch"]
            for m in pe[1][:AVAIL_MEMBERS_PER_EVENT]:
                sp, dp = lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(s0), "endTs": int(s0 + AVAIL_WINDOW_S), "fidelity": FIDELITY})
                if sp == 200 and isinstance(dp, dict) and len(dp.get("history") or []) > 0:
                    got += 1
        months[mon] = {"event_found": pe is not None, "members_with_rows": got}
        if pe is not None and got / AVAIL_MEMBERS_PER_EVENT >= AVAIL_MIN_FRACTION:
            usable.append(mon)
    res["s_availability_p_months"] = _chk(len(usable) >= AVAIL_MIN_MONTHS, months_usable=usable, months=months)
    res["_requests"] = {"pass": (lim.requests - r0) <= 30, "requests": lim.requests - r0}
    return res


def declared() -> dict:
    return {"family": "S", "label": LABEL_S, "label_stage2": LABEL_S2, "tag_id": TAG_ID,
            "windows": {"P": list(T14_P), "N": list(T14_N), "HOLDOUT_never_touched": list(T14_HOLDOUT), "fit": list(T14_FIT), "stage2": [T14_S2_FLOOR, T14_S2_CAP], "stage2_stop_events": S2_STOP_EVENTS,
                        "stage2_outcome_wait_d": S2_OUTCOME_WAIT_D, "stage2_post_close_every_s": S2_POST_CLOSE_EVERY_S, "stage2_pass_every_s": S2_PASS_EVERY_S},
            "pins": {"registry_file": S_SPORTS_REGISTRY_FILE_SHA256, "ids": S_SPORTS_IDS_SHA256, "slugs": S_SPORTS_SLUGS_SHA256, "broadcast_regex": S_BROADCAST_RE_SHA256,
                     "model_pin_file": MODEL_PIN_REL, "model_pin_note": "outside the rules hash; the S freeze entry carries s_model_sha256 / s_model_rebased_sha256"},
            "population": {"min_members": MIN_MEMBERS, "occasion_max_s": OCCASION_MAX_S, "primary_min_fit": PRIMARY_MIN_FIT, "timestamped_min_stamps": TIMESTAMPED_MIN_STAMPS,
                           "speaker_keywords": [list(x) for x in SPEAKER_KEYWORDS], "type_rules": [[k, list(v)] for k, v in TYPE_RULES], "type_class": TYPE_CLASS,
                           "gs0": {"n": GS0_N, "seed": GS0_SEED, "min_precision": GS0_MIN_PRECISION}},
            "prices": {"fidelity": FIDELITY, "point_lag_s": POINT_LAG_S, "p_t_max_age_s": P_T_MAX_AGE_S, "p_lag_back_s": P_LAG_BACK_S, "rising": [RISING_WINDOW_S, RISING_MIN], "p_range": [P_MIN, P_MAX],
                       "fetch_s": [-FETCH_BEFORE_S, FETCH_AFTER_S]},
            "alignment": {"anchor_hi": ANCHOR_HI, "anchor_lo": ANCHOR_LO, "anchor_back_s": ANCHOR_BACK_S, "anchor_lag_s": ANCHOR_LAG_S, "within_s": ANCHOR_WITHIN_S, "min_anchors": ANCHOR_MIN,
                          "max_iter": ALIGN_MAX_ITER, "checkpoint_s": CHECKPOINT_S, "min_e_s": MIN_E_S, "shift_s": SHIFT_S},
            "model": {"grid_min": MODEL_GRID_MIN, "shrink": SHRINK, "shrink_alt": list(SHRINK_ALT), "version": MODEL_VERSION},
            "tests": {"S1": {"floor": S1_FLOOR, "ways": ["event", "iso_week", "term"], "signflip_seed": c14.PLACEBO_SEEDS["S1_signflip"], "draws": SIGNFLIP_DRAWS, "joint_half": JOINT_HALF, "joint_p": JOINT_P,
                             "shift_p": SHIFT_P}, "S2": {"floor": S2_FLOOR, "ask": [ASK_OFFSET_P, ASK_OFFSET_Q], "through": TRADE_THROUGH, "fill_window_s": FILL_WINDOW_S, "fill_cap": FILL_CAP,
                                                         "min_e_s": S2_MIN_E_S, "placebo_seed": c14.PLACEBO_SEEDS["S2_calibrated"]}},
            "gates": {"GS": GS_MIN, "GSC": GSC_MIN, "GSP": {"seed": c14.SEED_GSP, "draws": c14.GSP_DRAWS, "loadings": list(GSP_LOADINGS), "mde_s1_max": MDE_S1_MAX, "mde_s2_max": MDE_S2_MAX}},
            "stage2": {"min_events": REP_MIN_EVENTS, "cap_min_events": REP_CAP_MIN_EVENTS}, "smoke_needs": list(SMOKE_NEEDS),
            "availability": {"events_per_month": AVAIL_EVENTS_PER_MONTH, "members_per_event": AVAIL_MEMBERS_PER_EVENT, "min_fraction": AVAIL_MIN_FRACTION, "window_s": AVAIL_WINDOW_S}}
