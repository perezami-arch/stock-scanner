#!/usr/bin/env python3
"""Extend the Jerusalem sunset/lunar calendar one month at a time.

Public Hebcal sunset/date API + pinned JPL DE440s, no market/provider secrets.
Existing months are never replaced. Each new month records source hashes.
"""
import argparse
import calendar
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen

EPHEMERIS_URL = 'https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp'
EPHEMERIS_SHA = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'


def generate(year, month, directory, ephemeris, sources=None):
    from skyfield.api import load, load_file
    from skyfield import almanac
    import skyfield
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    destination = directory/f'jerusalem-lunar-daily-{year:04d}-{month:02d}.csv'
    if destination.exists():
        return destination
    first = date(year, month, 1); last = date(year, month, calendar.monthrange(year, month)[1])
    start = first-timedelta(days=1)
    urls = {'sunsets': f'https://www.hebcal.com/zmanim?cfg=json&geonameid=281184&start={start}&end={last}&sec=1&ue=off',
            'dates': f'https://www.hebcal.com/converter?cfg=json&start={first}&end={last}&g2h=1&strict=1'}
    raw = {}
    for key, url in urls.items():
        if sources:
            raw[key] = Path(sources[key]).read_bytes()
        else:
            with urlopen(url, timeout=45) as response:
                raw[key] = response.read()
    sun, hebrew = [json.loads(raw[k].decode('utf-8-sig')) for k in ('sunsets', 'dates')]
    if sun['location'].get('geonameid') != 281184 or sun['location']['tzid'] != 'Asia/Jerusalem':
        raise ValueError('Unexpected sunset location')
    ephemeris = Path(ephemeris)
    if not ephemeris.exists():
        ephemeris.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(EPHEMERIS_URL, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != EPHEMERIS_SHA:
            raise ValueError('JPL ephemeris checksum mismatch')
        ephemeris.write_bytes(data)
    if hashlib.sha256(ephemeris.read_bytes()).hexdigest() != EPHEMERIS_SHA:
        raise ValueError('JPL ephemeris checksum mismatch')
    ts = load.timescale(builtin=True); eph = load_file(str(ephemeris))
    parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
    try:
        events, codes = almanac.find_discrete(ts.from_datetime(datetime.combine(first-timedelta(days=40), datetime.min.time(), timezone.utc)),
                                              ts.from_datetime(datetime.combine(last+timedelta(days=1), datetime.min.time(), timezone.utc)),
                                              almanac.moon_phases(eph))
        new_moons = [t.utc_datetime() for t,c in zip(events,codes) if c == 0]
        rows = []
        for i in range((last-first).days+1):
            d = first+timedelta(days=i); prior = d-timedelta(days=1)
            begin = parse(sun['times']['sunset'][str(prior)]); end = parse(sun['times']['sunset'][str(d)])
            sample = begin+timedelta(seconds=1); t = ts.from_datetime(sample)
            h = hebrew['hdates'][str(d)]
            phase = float(almanac.moon_phase(eph,t).degrees)
            moon = eph['earth'].at(t).observe(eph['moon']).apparent()
            rows.append(dict(civil_daylight_date=str(d), hebrew_date=h['hebrew'], hebrew_year=h['hy'],
                             hebrew_month=h['hm'], hebrew_day=h['hd'], start_sunset_utc=begin.isoformat(),
                             end_sunset_utc=end.isoformat(), lunar_sample_utc=sample.isoformat(), phase_deg=round(phase,6),
                             illuminated_percent=round(float(moon.fraction_illuminated(eph['sun']))*100,6),
                             waxing=phase < 180, days_since_new_moon=round((sample-max(n for n in new_moons if n <= sample)).total_seconds()/86400,6)))
    finally:
        eph.close()
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8-sig', newline='', suffix='.csv', dir=directory, delete=False) as f:
        tmp = Path(f.name); writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'modules'))
    from scanner_lunar_calendar import JerusalemCalendar
    try:
        JerusalemCalendar([tmp])
        for key, data in raw.items():
            (directory/f'{year:04d}-{month:02d}-{key}.source.json').write_bytes(data)
        metadata = dict(location='Jerusalem / Asia/Jerusalem', rows=len(rows), ephemeris_sha256=EPHEMERIS_SHA,
                        skyfield_version=skyfield.__version__, sources=urls,
                        source_sha256={k: hashlib.sha256(v).hexdigest() for k,v in raw.items()},
                        boundary='start_sunset < timestamp <= end_sunset', sample='opening sunset + 1 second',
                        validation='schema and boundaries checked; October pilot independently cross-checked against 2net and NASA')
        destination.with_suffix('.metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(destination)
    finally:
        if tmp.exists(): tmp.unlink()
    return destination


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--month', default=date.today().strftime('%Y-%m'))
    ap.add_argument('--directory', default='/workspace/research/jewish-lunar/data')
    ap.add_argument('--ephemeris', default='/workspace/research/jewish-lunar/ephemeris/de440s.bsp')
    a = ap.parse_args(); year, month = map(int, a.month.split('-'))
    print(generate(year, month, a.directory, a.ephemeris))


if __name__ == '__main__': main()
