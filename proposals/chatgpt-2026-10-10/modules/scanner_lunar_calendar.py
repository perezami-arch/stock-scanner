"""Jerusalem calendar feature extraction; adapted from lunar sidecar 0.1.0.

No broker/model/network access. Source levels and trade rules are never changed.
The astronomical sample belongs to the Hebrew day; it is NOT sampled at scan time.
"""
from __future__ import annotations

from bisect import bisect_left
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import math
from pathlib import Path

VERSION = 'jerusalem-lunar-sidecar-0.1.0'
BOUNDARY = 'start_sunset < decision_utc <= end_sunset'
DATA_FIELDS = ('lunar_hebrew_date', 'lunar_hebrew_year', 'lunar_hebrew_day',
               'lunar_civil_daylight_date', 'lunar_phase_deg', 'lunar_phase_sin',
               'lunar_phase_cos', 'lunar_illuminated_percent', 'lunar_waxing',
               'lunar_days_since_astronomical_new_moon', 'lunar_start_sunset_utc',
               'lunar_end_sunset_utc', 'lunar_sample_utc', 'lunar_calendar_file',
               'lunar_calendar_sha256')


def timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Timestamp must include UTC offset; date-only/naive time rejected')
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(row, *keys):
    for key in keys:
        if row.get(key) not in ('', None):
            value = float(row[key])
            if not math.isfinite(value):
                raise ValueError(f'Non-finite calendar value: {key}')
            return value
    raise ValueError(f'Missing calendar value: {keys}')


@dataclass(frozen=True)
class Day:
    start: datetime
    end: datetime
    sample: datetime
    values: dict
    calendar_file: str
    calendar_sha256: str


class JerusalemCalendar:
    """Loads the two existing research CSV schemas; gaps remain explicit."""

    def __init__(self, paths):
        self.days = []
        self.sources = []
        for path in map(Path, paths):
            sha = digest(path)
            count = 0
            with path.open(encoding='utf-8-sig', newline='') as fh:
                for row in csv.DictReader(fh):
                    start, end = timestamp(row['start_sunset_utc']), timestamp(row['end_sunset_utc'])
                    sample = timestamp(row['lunar_sample_utc'])
                    if not start < sample <= end or not 20 * 3600 < (end - start).total_seconds() < 28 * 3600:
                        raise ValueError(f'Invalid sunset interval/sample in {path.name}')
                    if sample - start != timedelta(seconds=1):
                        raise ValueError('This feature version requires the opening-sunset + 1 second convention')
                    phase = number(row, 'phase_deg')
                    illum = number(row, 'illuminated_percent')
                    age = number(row, 'days_since_new_moon', 'days_since_astronomical_new_moon')
                    hday = int(row['hebrew_day'])
                    waxing = str(row['waxing']).lower()
                    if not 0 <= phase < 360 or not 0 <= illum <= 100 or not 0 <= age < 35:
                        raise ValueError(f'Invalid lunar values in {path.name}')
                    if not 1 <= hday <= 30 or waxing not in ('true', 'false'):
                        raise ValueError(f'Invalid Hebrew day/waxing in {path.name}')
                    values = {
                        'lunar_hebrew_date': row['hebrew_date'],
                        'lunar_hebrew_year': int(row['hebrew_year']),
                        'lunar_hebrew_day': hday,
                        'lunar_civil_daylight_date': row['civil_daylight_date'],
                        'lunar_phase_deg': phase,
                        'lunar_phase_sin': math.sin(math.radians(phase)),
                        'lunar_phase_cos': math.cos(math.radians(phase)),
                        'lunar_illuminated_percent': illum,
                        'lunar_waxing': waxing == 'true',
                        'lunar_days_since_astronomical_new_moon': age,
                    }
                    self.days.append(Day(start, end, sample, values, path.name, sha))
                    count += 1
            self.sources.append({'file': str(path.resolve()), 'sha256': sha, 'rows': count})
        self.days.sort(key=lambda day: day.start)
        if not self.days:
            raise ValueError('Calendar is empty')
        for a, b in zip(self.days, self.days[1:]):
            if b.start < a.end:
                raise ValueError('Overlapping calendar intervals; choose one source for each day')
        self.starts = [day.start for day in self.days]

    def features(self, decision):
        decision = timestamp(decision)
        result = {'lunar_feature_version': VERSION, 'lunar_weight': 0,
                  'lunar_mode': 'recording_only', 'lunar_location': 'Jerusalem',
                  'lunar_timezone': 'Asia/Jerusalem', 'lunar_boundary_rule': BOUNDARY,
                  'lunar_sample_rule': 'opening sunset + 1 second; daily snapshot, not scan-time phase',
                  'lunar_status': 'out_of_calendar_coverage'}
        result.update(dict.fromkeys(DATA_FIELDS))
        # bisect_left assigns the exact boundary to the PREVIOUS Hebrew day.
        pos = bisect_left(self.starts, decision) - 1
        if pos < 0 or decision > self.days[pos].end:
            return result
        day = self.days[pos]
        result.update(lunar_start_sunset_utc=iso(day.start), lunar_end_sunset_utc=iso(day.end),
                      lunar_sample_utc=iso(day.sample), lunar_calendar_file=day.calendar_file,
                      lunar_calendar_sha256=day.calendar_sha256)
        if decision < day.sample:
            result['lunar_status'] = 'sample_not_yet_available'
            return result
        result.update(day.values)
        result['lunar_status'] = 'ok'
        return result
