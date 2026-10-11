"""D120 pairing population: fee category, dependence groups and screen-then-activate draws.

Pure and deterministic: no network, clock, SQL or file access. Every value is read from the
original-frame Gamma market row (pre-t0 frame metadata). Category comes only from ``feeType``
through a frozen, versioned prefix table, never from question text; dependence groups come only
from event ids, event/series slugs and ``negRiskMarketID`` of the same row, plus an optional
frozen slug-token table for common underlyings that is applied to series/event slugs only.

The dependence group is an attribute of a member, never part of its stratum key: siblings may
share a stratum, and the draw then screens at most one member per group (a shared claim set across
all drawn strata), so no two screened members, and therefore no two activated members, share a
group. "Group-disjoint" is not "independent": all origins of one run share run-level shocks.
"""

import re
from dataclasses import asdict, dataclass
from fractions import Fraction
from heapq import nsmallest

from astrolabe.feature_store.admission import content_hash

FACTS_VERSION = 'fs2-pairing-row-facts-v1'
FEE_CATEGORY_MAP_VERSION = 'fs2-fee-category-map-v1'
# Ordered (prefix, category); the first prefix of the lower-cased feeType wins.
FEE_CATEGORY_PREFIXES = (
    ('sports', 'sports'), ('politics', 'politics'), ('crypto', 'crypto'),
    ('weather', 'weather'), ('finance', 'finance'), ('economics', 'economics'),
    ('culture', 'culture'), ('tech', 'tech'), ('mentions', 'mentions'),
)
FEE_CATEGORIES = tuple(c for _, c in FEE_CATEGORY_PREFIXES)
UNKNOWN_CATEGORY = 'unknown'
OTHER_PREFIX = 'other:'
# Stratum value for a member's category in the v5 selection: prefixed so that a literal source
# value can never collide with the missing-category stratum (selection.py literal guard).
STRATUM_CATEGORY_PREFIX = 'fee:'
MAX_TEXT = 256
MAX_LINKS = 64

UNDERLYING_TABLE_VERSION = 'fs2-underlying-slug-tokens-v1'
# Exact '-'-separated tokens of event/series slugs only (never question text).
UNDERLYING_TOKENS = {
    'btc': 'btc', 'bitcoin': 'btc', 'eth': 'eth', 'ethereum': 'eth',
    'sol': 'sol', 'solana': 'sol', 'xrp': 'xrp', 'ripple': 'xrp',
    'doge': 'doge', 'dogecoin': 'doge',
}
GROUPING_VERSION = 'fs2-dependence-groups-v2'
# v2 (pre-freeze, stricter): parentEventId is an event id and is unioned with event ids.
GROUPING_LINKS = ('event_ids', 'parent_event_ids', 'series_slugs', 'neg_risk_market_id')

DESIGN_VERSION = 'fs2-pairing-design-v1'
CATEGORY_POLICY_EXCLUDED = 'category_excluded_by_population_policy'
_TOKEN = re.compile('[a-z0-9]+')


def fee_category(fee_type):
    """Frozen v1 prefix map. Missing/empty/invalid -> ``unknown``; unmatched -> ``other:<raw>``."""
    if not isinstance(fee_type, str) or not fee_type.strip() or len(fee_type) > MAX_TEXT:
        return UNKNOWN_CATEGORY
    lowered = fee_type.lower()
    for prefix, category in FEE_CATEGORY_PREFIXES:
        if lowered.startswith(prefix):
            return category
    return OTHER_PREFIX + fee_type


def _text(value):
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        text = str(value)
        if text and len(text) <= MAX_TEXT:
            return text
    return None


def row_facts(row):
    """Group/category facts of one original Gamma market row; invalid entries are counted."""
    if not isinstance(row, dict):
        raise ValueError('original source row required')
    events = row.get('events')
    invalid = 0
    event_ids, event_slugs, series_ids, series_slugs, parents = set(), set(), set(), set(), set()
    if events is not None and not isinstance(events, list):
        events, invalid = [], invalid + 1
    for event in (events or [])[:MAX_LINKS]:
        if not isinstance(event, dict):
            invalid += 1
            continue
        for key, target in (('id', event_ids), ('slug', event_slugs),
                            ('parentEventId', parents)):
            value = event.get(key)
            if value is None:
                continue
            text = _text(value)
            if text is None:
                invalid += 1
            else:
                target.add(text)
        series = event.get('series')
        if series is not None and not isinstance(series, list):
            invalid += 1
            continue
        for item in (series or [])[:MAX_LINKS]:
            if not isinstance(item, dict):
                invalid += 1
                continue
            for key, target in (('id', series_ids), ('slug', series_slugs)):
                value = item.get(key)
                if value is None:
                    continue
                text = _text(value)
                if text is None:
                    invalid += 1
                else:
                    target.add(text)
    if isinstance(events, list) and len(events) > MAX_LINKS:
        invalid += 1
    neg = row.get('negRiskMarketID')
    neg_text = _text(neg) if neg not in (None, '') else None
    if neg not in (None, '') and neg_text is None:
        invalid += 1
    fee = row.get('feeType')
    return {
        'version': FACTS_VERSION, 'fee_type': fee if _text(fee) is not None else None,
        'fee_category': fee_category(fee), 'fee_category_map': FEE_CATEGORY_MAP_VERSION,
        'event_ids': sorted(event_ids), 'event_slugs': sorted(event_slugs),
        'series_ids': sorted(series_ids), 'series_slugs': sorted(series_slugs),
        'parent_event_ids': sorted(parents), 'neg_risk_market_id': neg_text,
        'invalid_entries': invalid,
    }


def underlyings(facts, table=None):
    """Underlying tokens named by event/series slugs only; never question text."""
    table = UNDERLYING_TOKENS if table is None else table
    found = set()
    for slug in (*facts['series_slugs'], *facts['event_slugs']):
        for token in _TOKEN.findall(slug.lower()):
            if token in table:
                found.add(table[token])
    return sorted(found)


def dependence_groups(facts_by_market, *, underlying=True):
    """Union-find over market, event id (incl. parentEventId), series slug, negRiskMarketID
    (and underlying) nodes.

    Every event and series of a row is linked, not only the first. The group id is the smallest
    market id of its component, so it is independent of input order.
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for market, facts in facts_by_market.items():
        node = 'm:' + market
        find(node)
        for event in (*facts['event_ids'], *facts.get('parent_event_ids', ())):
            union(node, 'e:' + event)
        for slug in facts['series_slugs']:
            union(node, 's:' + slug)
        if facts['neg_risk_market_id'] is not None:
            union(node, 'n:' + facts['neg_risk_market_id'])
        if underlying:
            for token in underlyings(facts):
                union(node, 'u:' + token)
    components = {}
    for market in facts_by_market:
        components.setdefault(find('m:' + market), []).append(market)
    result = {}
    for markets in components.values():
        label = 'g:' + min(markets, key=lambda m: (len(m), m))
        for market in markets:
            result[market] = label
    return result


def grouping_policy(underlying=True):
    return {'version': GROUPING_VERSION, 'links': list(GROUPING_LINKS),
            'all_events_and_series_per_row': True,
            'underlying_table': ({'version': UNDERLYING_TABLE_VERSION,
                                  'tokens': dict(sorted(UNDERLYING_TOKENS.items())),
                                  'applies_to': 'event and series slugs only'}
                                 if underlying else None),
            'group_id': 'smallest market id (length, then text) of the connected component',
            'semantics': 'dependence attribute; never part of the stratum key'}


@dataclass(frozen=True)
class PairingDesign:
    """Screen-then-activate shape. Scheduled arm is a parameter kept at 0 for D120."""

    strata: int
    screen_per_stratum: int
    min_groups_per_stratum: int = 8
    pairs_per_stratum: int = 1
    scheduled_per_stratum: int = 0
    activate_screened: bool = False
    exclude_categories: tuple[str, ...] = ()
    underlying_grouping: bool = True
    version: str = DESIGN_VERSION

    def __post_init__(self):
        for value, low, high in ((self.strata, 1, 64), (self.screen_per_stratum, 2, 64),
                                 (self.min_groups_per_stratum, 2, 64),
                                 (self.pairs_per_stratum, 1, 1),
                                 (self.scheduled_per_stratum, 0, 0)):
            if type(value) is not int or not low <= value <= high:
                raise ValueError('bounded explicit pairing design required')
        if self.activate_screened is not False or type(self.underlying_grouping) is not bool:
            raise ValueError('D120 activates only drawn pairs; screened members stay unactivated')
        if (not isinstance(self.exclude_categories, tuple)
                or len(set(self.exclude_categories)) != len(self.exclude_categories)
                or any(not isinstance(c, str) or not c or len(c) > MAX_TEXT
                       for c in self.exclude_categories)
                or list(self.exclude_categories) != sorted(self.exclude_categories)):
            raise ValueError('sorted unique explicit category exclusion list required')
        if self.version != DESIGN_VERSION:
            raise ValueError('unknown pairing design')

    @property
    def screened_slots(self):
        return self.strata * self.screen_per_stratum

    @property
    def origin_slots(self):
        return self.strata * self.pairs_per_stratum * 2

    @property
    def category_policy(self):
        return ('all' if not self.exclude_categories
                else 'all_except:' + ','.join(self.exclude_categories))

    def as_dict(self):
        value = asdict(self)
        value['exclude_categories'] = list(self.exclude_categories)
        return value


def design_from_dict(value):
    return PairingDesign(**{**value, 'exclude_categories': tuple(value['exclude_categories'])})


def _rank(seed, domain, *parts):
    return content_hash({'seed': seed, 'domain': domain, 'parts': list(parts)})


def _probability(value):
    from .sampling import _probability_fraction

    return _probability_fraction(Fraction(value))


def screen_draw(seed, strata, design):
    """First stage, before any book read.

    ``strata``: stratum key -> {'fields': ..., 'groups': {group: [market ids]}} over eligible
    members. Drawable strata have at least ``min_groups_per_stratum`` groups. ``strata`` drawable
    strata are drawn uniformly without replacement (seeded ranking); drawn strata are processed in
    that ranking order and each screens up to ``screen_per_stratum`` groups in seeded group order,
    skipping groups claimed by an earlier stratum, one seeded member per group.
    """
    if type(design) is not PairingDesign:
        raise ValueError('explicit pairing design required')
    drawable = sorted(k for k, s in strata.items()
                      if len(s['groups']) >= design.min_groups_per_stratum)
    order = nsmallest(design.strata, drawable,
                      key=lambda k: (_rank(seed, 'pairing_stratum_v1', k), k))
    stage = (Fraction(len(order), len(drawable)) if drawable else None)
    claimed, picks, reports = set(), [], []
    for position, key in enumerate(order):
        groups = strata[key]['groups']
        available = sorted(g for g in groups if g not in claimed)
        chosen = nsmallest(design.screen_per_stratum, available,
                           key=lambda g: (_rank(seed, 'pairing_group_v1', key, g), g))
        group_probability = (Fraction(len(chosen), len(available)) if available else None)
        for group in chosen:
            members = sorted(groups[group])
            market = min(members, key=lambda m: (_rank(seed, 'pairing_member_v1', key, group, m),
                                                 m))
            conditional = group_probability * Fraction(1, len(members))
            picks.append({
                'market_id': market, 'stratum': key, 'dependence_group': group,
                'stratum_order': position,
                'stratum_inclusion_probability': _probability(stage),
                'group_inclusion_probability_given_available': _probability(group_probability),
                'member_inclusion_probability_given_group': _probability(
                    Fraction(1, len(members))),
                'conditional_market_inclusion_probability': _probability(conditional),
                'inclusion_probability': _probability(stage * conditional),
                'available_groups': len(available), 'claimed_before': len(groups) - len(available),
                'group_members_in_stratum': len(members),
            })
        claimed.update(chosen)
        reports.append({'stratum': key, 'stratum_order': position, 'groups': len(groups),
                        'available_groups': len(available), 'screened': len(chosen)})
    return {'drawable_strata': drawable, 'drawn_strata': order,
            'stratum_inclusion_probability': _probability(stage) if stage is not None else None,
            'screened': picks, 'drawn_reports': reports}


def role_draw(seed, screened, states, design):
    """Second stage after screening, per drawn stratum in first-stage order.

    ``screened``: list of {'market_id', 'stratum', 'stratum_order', 'dependence_group'};
    ``states``: market -> {'state': triggered|untriggered|unavailable|not_assessed,
    'evidence_id'}. The trigger is the first available triggered member by seeded hash; the
    control is the first available untriggered member. A trigger without a control activates
    nothing (``control_scarcity``). Roles are fixed here and never relabelled later.
    """
    if type(design) is not PairingDesign:
        raise ValueError('explicit pairing design required')
    by_stratum = {}
    for row in screened:
        by_stratum.setdefault((row['stratum_order'], row['stratum']), []).append(row)
    assignments, reports = [], []
    for (position, key), rows in sorted(by_stratum.items()):
        pools = {name: sorted(r['market_id'] for r in rows
                              if states[r['market_id']]['state'] == name)
                 for name in ('triggered', 'untriggered', 'unavailable', 'not_assessed')}

        def first(pool, arm, key=key):
            return min(pool, key=lambda m: (_rank(seed, 'pairing_' + arm + '_v1', key, m), m))

        trigger = first(pools['triggered'], 'trigger') if pools['triggered'] else None
        control = first(pools['untriggered'], 'control') if pools['untriggered'] else None
        state = ('paired' if trigger and control else
                 'control_scarcity' if trigger else
                 'no_trigger')
        if state == 'paired':
            tid = states[trigger]['evidence_id']
            assignments.append({
                'market_id': trigger, 'arm': 'triggered', 'stratum': key, 'trigger_id': tid,
                'matched_trigger_ids': [],
                'conditional_role_probability': _probability(Fraction(1, len(pools['triggered']))),
                'conditional_matching_probability': None})
            assignments.append({
                'market_id': control, 'arm': 'control', 'stratum': key, 'trigger_id': None,
                'matched_trigger_ids': [tid],
                'conditional_role_probability': _probability(
                    Fraction(1, len(pools['untriggered']))),
                'conditional_matching_probability': _probability(
                    Fraction(1, len(pools['untriggered'])))})
        reports.append({
            'stratum': key, 'stratum_order': position, 'screened': len(rows),
            **{name + '_pool': len(pool) for name, pool in pools.items()},
            'pair_state': state, 'triggers_in_scope': min(len(pools['triggered']),
                                                          design.pairs_per_stratum),
            'pairs_drawn': int(state == 'paired'),
            'scheduled_count': design.scheduled_per_stratum,
        })
    triggers = sum(r['triggers_in_scope'] for r in reports)
    pairs = sum(r['pairs_drawn'] for r in reports)
    return {'assignments': assignments, 'strata': reports,
            'triggers_in_scope': triggers, 'pairs_drawn': pairs,
            'fill': _probability(Fraction(pairs, triggers)) if triggers else None,
            'strata_with_trigger': sum(r['triggered_pool'] > 0 for r in reports),
            'control_scarcity_strata': sum(r['pair_state'] == 'control_scarcity'
                                           for r in reports)}
