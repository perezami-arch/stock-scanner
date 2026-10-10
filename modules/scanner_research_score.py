"""Experimental, direction-aware research overlay. No network or trading calls.

Initial weights/rules are hypotheses, not fitted coefficients or probabilities.
Missing component allocation goes back to the baseline; it is never redistributed.
See research/jewish-lunar/INTEGRATION.he.md for formulas and source boundaries.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from scanner_lunar_calendar import JerusalemCalendar, iso, timestamp

VERSION = 'gann-tekuna-overlay-0.2.0'
RESEARCH_BASIS = 'gann-jewish-research.md sections 7-11; H1/H2/H3'
DEFAULT_WEIGHT = 0.30
WEIGHTS = dict(lunar_calendar=0.20, gann=0.15, fibonacci=0.15,
               elliott=0.15, candles=0.10, volume=0.10, confluence=0.15)
PARAMETERS = dict(near_level_atr=1.0, gann_time_window_bars=3,
                  volume_confirmation_ratio=1.2, provisional_strength=0.5,
                  clock_rule='H3-phase-relation-v1 (our unvalidated operationalization)',
                  asset_period='confirmed Gann swing duration in completed bars',
                  relative_volume_baseline='median of 20 preceding completed bars')
SOURCES = dict(lunar_calendar=['TEKUNAH-RELATIONS', 'GANN-TIME-PRICE', 'H3-TWO-CLOCKS'],
               gann=['GANN-TIME-PRICE'], fibonacci=['TECH-FIB'],
               elliott=['TECH-ELLIOTT'], candles=['TECH-CANDLES'],
               volume=['GANN-TIME-PRICE', 'TECH-PARTICIPATION'],
               confluence=['H2-PRICE-RESPONSE', 'H3-TWO-CLOCKS', 'JOINT-HYPOTHESIS'])
IMPULSE_SCORES = {'1': 50, '2': 100, '3': 50, '4': 90, '5': 10}
VOLUME_FAMILIES = {'volume_exhaustion', 'effort_result', 'wave_volume_dominance',
                   'climax', 'momentum_divergence'}


def num(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def clip(value, lo=0.0, hi=1.0):
    return min(hi, max(lo, value))


def validate_weight(weight):
    value = num(weight)
    if value is None or not 0 <= value <= 1:
        raise ValueError('research weight must be a finite fraction in [0, 1]')
    return value


def component(score, reason, **evidence):
    return dict(score=score, status='available' if score is not None else 'missing',
                reason=reason, evidence=evidence)


def near(distance):
    return clip(1 - max(0, distance) / PARAMETERS['near_level_atr'])


def geometry_at_cutoff(bars, cutoff, asset, direction):
    """Recompute both sides from their own closed-bar view, never from LONG CSV fields."""
    import scanner_geometry as GEO
    clock_asset = 'stock' if asset in ('stock', 'etf') else asset
    return GEO.geometry_columns(bars, cutoff, clock_asset, direction, intraday=False)


def _candles(geo, direction):
    bias = geo.get('candle_bias_last')
    if bias not in ('bullish', 'bearish', 'mixed', 'neutral', 'none'):
        return component(None, 'candle classification unavailable')
    aligned = 'bullish' if direction == 'LONG' else 'bearish'
    score = 100.0 if bias == aligned else 0.0 if bias in ('bullish', 'bearish') else 50.0
    return component(score, 'last closed candle, relative to trade direction', bias=bias,
                     patterns=geo.get('candle_patterns_last'), context=geo.get('candle_context'))


def _volume(levels, geo):
    signals = ((levels.get('waves') or {}).get('signals')) or {}
    families = {}
    for side in ('start', 'end'):
        count = num(signals.get(f'wave_{side}_n'))
        raw = signals.get(f'wave_{side}_families')
        if count is None or count < 0 or count != int(count):
            return component(None, 'wave family count unavailable')
        names = {s.strip() for s in str(raw or '').split(',') if s.strip()}
        if len(names) != count or names - VOLUME_FAMILIES - {'elliott_context'}:
            return component(None, 'wave family names/count mismatch')
        families[side] = sorted(names & VOLUME_FAMILIES)  # Elliott already has its own budget.
    rv = num(geo.get('candle_vol_ratio20_median'))
    if rv is None or rv < 0:
        return component(None, 'relative volume against prior-20 median unavailable')
    difference = clip(len(families['start']) - len(families['end']), -2, 2)
    strength = clip(rv / PARAMETERS['volume_confirmation_ratio'])
    score = 50 + 25 * difference * strength
    return component(score, 'start minus end families; Elliott excluded; RVOL attenuates evidence',
                     families=families, relative_volume=rv, relative_volume_baseline=PARAMETERS['relative_volume_baseline'],
                     rsi14=num(signals.get('rsi14')),
                     cci20=num(signals.get('cci20')), crsi=num(signals.get('crsi')))


def _elliott(levels, direction):
    view = (((levels.get('elliott') or {}).get('v2') or {}).get('views') or {}).get(direction)
    if not isinstance(view, dict):
        return component(None, 'Elliott v2 direction view unavailable')
    state = view.get('state')
    if state == 'none':
        return component(50.0, 'computed: no valid Elliott count', state=state)
    if state not in ('impulse_confirmed', 'impulse_provisional', 'abc_confirmed', 'abc_provisional'):
        return component(None, 'unrecognized Elliott state')
    points = view.get('pivots') or []
    last_bar = levels['data']['last_bar'][:10]
    for point in points:
        if not point.get('date') or point['date'][:10] > last_bar:
            return component(None, 'pivot outside visible bars')
        confirmed = point.get('confirmed_at')
        if confirmed and confirmed[:10] > last_bar:
            return component(None, 'pivot not confirmed at cutoff')
        if not confirmed and not point.get('provisional'):
            return component(None, 'pivot confirmation metadata missing')
    if not points:
        return component(None, 'Elliott count has no pivots')
    endpoint = str(points[-1].get('label'))
    provisional = state.endswith('_provisional') or bool(view.get('provisional')) or any(p.get('provisional') for p in points)
    if state.startswith('impulse'):
        score = IMPULSE_SCORES.get(endpoint)
    elif endpoint == 'C':
        score = 90 if view.get('context') in ('W2', 'W4') else 60
    else:
        score = 25 if endpoint in ('A', 'B') else None
    if score is None:
        return component(None, 'unrecognized wave endpoint')
    if view.get('beyond_target'):
        score = min(score, 50)
    if provisional:
        score = 50 + PARAMETERS['provisional_strength'] * (score - 50)
    return component(float(score), 'versioned endpoint heuristic; provisional evidence discounted',
                     state=state, endpoint=endpoint, context=view.get('context'), provisional=provisional,
                     beyond_target=view.get('beyond_target'))


def _fibonacci(levels, geo, direction, close, atr):
    fib = (levels.get('fib') or {}).get('v2') or {}
    if fib.get('view') != direction or fib.get('stale') is not False or close is None or atr is None:
        return component(None, 'usable direction-specific Fibonacci v2 / ATR unavailable')
    last_bar = levels['data']['last_bar'][:10]
    confirmed = (levels.get('pivots') or {}).get('confirmed') or []
    for name in ('origin', 'end'):
        anchor = fib.get(name) or {}
        price = num(anchor.get('price'))
        matching = [p for p in confirmed if p.get('date') == anchor.get('date') and
                    price is not None and num(p.get('price')) is not None and
                    abs(num(p['price']) - price) <= 1e-4]
        if not any(p.get('confirmed_at') and p['confirmed_at'][:10] <= last_bar for p in matching):
            return component(None, 'Fibonacci anchor not present in confirmed pivot snapshot')
    retracements = [num((fib.get('levels') or {}).get(k)) for k in ('0.382', '0.5', '0.618', '0.786')]
    if any(v is None or v <= 0 for v in retracements):
        return component(None, 'incomplete Fibonacci retracements')
    side = 'below' if direction == 'LONG' else 'above'
    eligible = [v for v in retracements if (v <= close if direction == 'LONG' else v >= close)]
    distance = min((abs(close - v) / atr for v in eligible), default=None)
    retrace_proximity = near(distance) if distance is not None else 0.0
    if 'exp_spiral_arc_above' not in geo or 'exp_spiral_arc_below' not in geo:
        return component(None, 'spiral calculation unavailable')
    arc = num(geo.get(f'exp_spiral_arc_{side}'))
    arc_distance = abs(close - arc) / atr if arc is not None else None
    arc_proximity = near(arc_distance) if arc_distance is not None else 0.0
    return component(50 + 50 * (0.75 * retrace_proximity + 0.25 * arc_proximity),
                     'directional retracement proximity (75%) and spiral proximity (25%); 1 ATR window',
                     retracement_distance_atr=distance, spiral_distance_atr=arc_distance,
                     reanchored=fib.get('reanchored'))


def _gann(geo, direction, close, atr):
    bars = num(geo.get('exp_gann_next_time_bars'))
    if bars is None or bars < 1 or close is None or atr is None:
        return component(None, 'Gann anchor / future bar count / ATR unavailable')
    side = 'below' if direction == 'LONG' else 'above'
    distances = []
    for kind in ('level', 'angle'):
        value = num(geo.get(f'exp_gann_{kind}_{side}'))
        distances.append(abs(close - value) / atr if value is not None else None)
    if all(d is None for d in distances):
        return component(None, 'directional Gann price references unavailable')
    proximity = sum(near(d) if d is not None else 0 for d in distances) / 2
    time_proximity = clip(1 - (bars - 1) / PARAMETERS['gann_time_window_bars'])
    return component(50 + 50 * proximity * (0.5 + 0.5 * time_proximity),
                     'directional box/angle proximity with future bar-distance timing',
                     level_distance_atr=distances[0], angle_distance_atr=distances[1], next_time_bars=bars,
                     calendar_date_not_used=True)


def _clock_pair(lunar, geo):
    """H3 features, with one declared experimental phase relation.

    Angular equality across two normalized clocks is OUR hypothesis, not a
    formula in Gann/Vital. No bullish/bearish coefficient is assigned to a moon half.
    """
    if lunar.get('lunar_status') != 'ok':
        return dict(status='missing', reason=lunar.get('lunar_status', 'calendar unavailable'))
    phase = num(lunar.get('lunar_phase_deg'))
    period = num(geo.get('exp_gann_box_bars'))
    age = num(geo.get('exp_gann_origin_age_bars'))
    end_age = num(geo.get('exp_gann_end_age_bars'))
    if phase is None or not 0 <= phase < 360:
        return dict(status='missing', reason='invalid astronomical phase')
    if period is None or age is None or end_age is None or period < 1 or age < period or end_age < 0:
        return dict(status='missing', reason='confirmed asset clock unavailable')
    if any(v != int(v) for v in (period, age, end_age)) or age - end_age != period:
        return dict(status='missing', reason='inconsistent asset bar clock')
    last_bar = geo.get('geo_last_bar')
    anchors = {}
    for name in ('origin', 'end'):
        date = geo.get(f'exp_anchor_{name}_date')
        confirmation = geo.get(f'exp_anchor_{name}_confirmed_at')
        if not isinstance(date, str) or not isinstance(confirmation, str) or not isinstance(last_bar, str):
            return dict(status='missing', reason='anchor availability metadata missing')
        if not date <= confirmation <= last_bar:
            return dict(status='missing', reason='asset anchor unavailable at cutoff')
        anchors[name] = dict(date=date, confirmed_at=confirmation)
    asset_phase = 360 * (age % period) / period
    difference = (phase - asset_phase + 180) % 360 - 180
    relation = clip((1 + math.cos(math.radians(difference))) / 2)
    return dict(status='ok', rule=PARAMETERS['clock_rule'], astronomical_phase_deg=phase,
                asset_phase_deg=asset_phase, phase_difference_deg=difference, relation_strength=relation,
                asset_period_bars=period, bars_since_origin=age, bars_since_end=end_age, anchors=anchors,
                astronomical_clock_sample_utc=lunar.get('lunar_sample_utc'), asset_clock_last_bar=last_bar,
                direction_prior='none; market response supplies trade direction',
                hebrew_day_role='Jerusalem sunset assignment and research context only')


def _lunar(clocks, blocks):
    if clocks['status'] != 'ok':
        return component(None, clocks['reason'])
    scores = [blocks[k]['score'] for k in ('candles', 'volume')]
    if any(s is None for s in scores):
        return component(None, 'H3 needs an observed candle and volume response')
    response = sum(scores) / len(scores)
    return component(50 + (response - 50) * clocks['relation_strength'],
                     'H3 experimental two-clock relation conditioned on observed price/volume response',
                     clocks=clocks, market_response=response)


def _confluence(clocks, blocks):
    keys = ('gann', 'fibonacci', 'elliott', 'candles', 'volume')
    if clocks['status'] != 'ok' or any(blocks[k]['score'] is None for k in keys):
        return component(None, 'H2/H3 joint rule needs technical families and both clocks')
    geometry = sum(blocks[k]['score'] for k in ('gann', 'fibonacci', 'elliott')) / 3
    agreement = min(geometry, blocks['candles']['score'], blocks['volume']['score'])
    return component(50 + (agreement - 50) * clocks['relation_strength'],
                     'H2/H3: weakest technical group conditioned on the declared two-clock relation',
                     geometry_group=geometry, technical_agreement=agreement, clocks=clocks,
                     fib_elliott_role='modern price-context tools; not attributed to Gann or Sefer HaTekunah')


def blend(base_score, blocks, weight=DEFAULT_WEIGHT):
    weight = validate_weight(weight)
    base = num(base_score)
    valid_base = base is not None and 0 <= base <= 100
    complete = {}
    coverage = weighted_sum = adjustment = 0.0
    for key, share in WEIGHTS.items():
        block = dict(blocks.get(key) or component(None, 'component unavailable'))
        score = num(block.get('score'))
        if score is not None and not 0 <= score <= 100:
            raise ValueError(f'component score outside [0, 100]: {key}')
        available = score is not None
        if available:
            coverage += share
            weighted_sum += share * score
        delta = weight * share * (score - base) if available and valid_base else 0.0
        adjustment += delta
        block.update(score=score, share_of_research=share, allocated_total_weight=weight * share,
                     effective_total_weight=weight * share if available and valid_base else 0.0,
                     contribution_points=delta, source_ids=SOURCES[key])
        complete[key] = block
    coverage = min(1.0, coverage)
    effective = weight * coverage if valid_base else 0.0
    # research_score is a display-only average. It is NEVER substituted in a full-weight blend when coverage < 1.
    return dict(version=VERSION, validation_status='experimental_unvalidated', configured_weight=weight,
                baseline_score=base, research_score=weighted_sum / coverage if coverage else None,
                coverage=coverage, effective_research_weight=effective, effective_baseline_weight=1-effective,
                score=round(base + adjustment, 4) if valid_base else base,
                delta_points=adjustment if valid_base else 0.0, components=complete,
                status='invalid_baseline' if not valid_base else 'disabled' if weight == 0 else
                       'unavailable' if not coverage else 'complete' if coverage >= 1 - 1e-9 else 'partial')


class ResearchScorer:
    def __init__(self, calendar_paths=None, weight=DEFAULT_WEIGHT):
        self.weight = validate_weight(weight)
        if calendar_paths is None:
            here = Path(__file__).resolve().parent
            directory = (here.parent if here.name == 'modules' else here) / 'research' / 'jewish-lunar' / 'data'
            calendar_paths = sorted(directory.glob('jerusalem-lunar-daily-*.csv'))
        paths = list(calendar_paths)
        self.calendar = JerusalemCalendar(paths) if paths else None
        self.config = dict(version=VERSION, research_basis=RESEARCH_BASIS, weight=self.weight, components=WEIGHTS, parameters=PARAMETERS,
                           impulse_scores=IMPULSE_SCORES, missing_policy='return allocation to baseline')
        self.config_sha256 = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()

    def manifest(self):
        modules = Path(__file__).resolve().parent
        return dict(config=self.config, config_sha256=self.config_sha256,
                    scorer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    dependency_sha256={name: hashlib.sha256((modules / name).read_bytes()).hexdigest()
                                       for name in ('scanner_lunar_calendar.py', 'scanner_geometry.py',
                                                    'scanner_elliott_v2.py', 'scanner_waves.py')},
                    calendar_sources=self.calendar.sources if self.calendar else [],
                    validation_status='experimental_unvalidated', integration_base_commit='b399f53e08bb078aa95108170903b6b07b862a3a')

    def evaluate(self, candidate, levels, bars=None, geometry=None):
        base = candidate.get('baseline_score', candidate.get('unified_score'))
        direction = candidate['direction']
        if direction not in ('LONG', 'SHORT') or levels.get('direction') != direction:
            raise ValueError('candidate and levels direction mismatch')
        if levels.get('symbol') != candidate['t'] or levels.get('asset') != candidate.get('asset'):
            raise ValueError('candidate and levels identity mismatch')
        cutoff = iso(timestamp(levels['data']['cutoff_utc']))
        baseline_basis = candidate.get('baseline_rank_basis', candidate.get('rank_basis', ''))
        lunar = self.calendar.features(cutoff) if self.calendar else {'lunar_status': 'calendar_not_configured'}
        # This calendar helper only extracts features; weights live exclusively in this overlay.
        lunar.pop('lunar_weight', None)
        lunar.pop('lunar_mode', None)
        errors = []
        geo = geometry
        if geo is None:
            try:
                geo = geometry_at_cutoff(bars, cutoff, candidate['asset'], direction) if bars is not None else {}
            except Exception as exc:
                errors.append(f'geometry: {type(exc).__name__}: {exc}')
                geo = {}
        if geo.get('geo_direction_view') != direction or geo.get('geo_last_bar') != levels['data']['last_bar'][:10]:
            errors.append('geometry direction / last bar mismatch or missing')
            geo = {}
        atr = num((levels.get('technical') or {}).get('atr14_wilder'))
        atr = atr if atr is not None and atr > 0 else None
        close = num((levels.get('technical') or {}).get('last_close'))
        blocks = dict(candles=_candles(geo, direction), volume=_volume(levels, geo),
                      elliott=_elliott(levels, direction), fibonacci=_fibonacci(levels, geo, direction, close, atr),
                      gann=_gann(geo, direction, close, atr))
        clocks = _clock_pair(lunar, geo)
        blocks['lunar_calendar'] = _lunar(clocks, blocks)
        blocks['confluence'] = _confluence(clocks, blocks)
        if 'raw fallback' in baseline_basis:
            blocks = {k: component(None, 'baseline is raw momentum, not a 0-100 percentile') for k in WEIGHTS}
        result = blend(base, blocks, self.weight)
        result.update(run_id=levels.get('run_id'), ticker=candidate['t'], asset=candidate['asset'], direction=direction,
                      decision_utc=cutoff, last_bar_date=levels['data']['last_bar'],
                      baseline_basis=baseline_basis, config_sha256=self.config_sha256,
                      lunar=lunar, clocks=clocks, research_basis=RESEARCH_BASIS, errors=errors)
        return result

    def apply(self, candidate, levels, bars=None, geometry=None):
        """One permitted mutation point: scores/metadata only, before selection and levels hashing."""
        result = self.evaluate(candidate, levels, bars, geometry)
        candidate.setdefault('baseline_score', candidate.get('unified_score'))
        candidate.setdefault('baseline_rank_basis', candidate.get('rank_basis'))
        active = result['effective_research_weight'] > 0
        basis = (f"{VERSION}; base={result['effective_baseline_weight']:.1%}, research={result['effective_research_weight']:.1%}"
                 if active else candidate['baseline_rank_basis'])
        candidate.update(unified_score=result['score'], rank_score=result['score'], rank_basis=basis,
                         research_score=result['research_score'], research_delta=result['delta_points'],
                         research_coverage=result['coverage'], research_effective_weight=result['effective_research_weight'],
                         research_status=result['status'], research_version=VERSION)
        levels.setdefault('score', {}).update(value=result['score'], basis=basis, baseline=result['baseline_score'])
        levels.setdefault('context', {}).update(rank_score=result['score'], rank_basis=basis)
        levels['research_score'] = result
        return result
