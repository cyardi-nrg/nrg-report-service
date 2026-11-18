# Design Lab worker v1.5.0 (2026-10-31) — expected generation, month by month.
#
# Owner's own ask: "expected generation from the system ... month wise ...
# on the lines of PVsyst ... SAM from the US govt". NREL's SAM simulation
# engine (PySAM, free and open source — no MCP needed) runs right here on
# the Mac, hour by hour over a typical year:
#   * weather: PVGIS typical meteorological year (EU JRC — free, no key,
#     covers India) for the site's latitude / longitude; downloaded once
#     per site and kept in ~/.designlab/weather;
#   * each roof face is simulated as its own array with its own kWp,
#     tilt and direction (PVWatts v8 model): flush sheets as roof-mounted,
#     tables on flat roofs as open-rack; premium (TOPCon-class) modules;
#   * losses 14 % (soiling, wiring, mismatch, availability ...) and an
#     inverter of 96 % — editable later; shade is already left out by the
#     layout's shade check, so no extra shading loss is added.
# Returns month-wise units, the year, units per kWp and performance ratio.
import json
import math
import os
import re

import requests

CACHE = os.path.join(os.path.expanduser('~'), '.designlab', 'weather')
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DEFAULT_SITE = (22.3072, 73.1812, 'Vadodara (default — no site location given)')
LOSSES = 14.0
INV_EFF = 96.0
AZ = {'S': 180.0, 'N': 0.0, 'E': 90.0, 'W': 270.0}


def site_location(project: dict | None, marks: dict | None) -> tuple[float, float, str]:
    """Latitude / longitude: typed in Site & marks, else from the project's Google Maps link, else Vadodara."""
    m = marks or {}
    if m.get('lat') and m.get('lon'):
        return float(m['lat']), float(m['lon']), 'site location from Site & marks'
    url = (project or {}).get('google_maps_url') or ''
    for pat in (r'@(-?\d+\.\d+),(-?\d+\.\d+)', r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', r'[?&](?:q|ll|query)=(-?\d+\.\d+),\s*(-?\d+\.\d+)'):
        g = re.search(pat, url)
        if g:
            return float(g.group(1)), float(g.group(2)), "site location from the project's Google Maps link"
    return DEFAULT_SITE


def tmy(lat: float, lon: float) -> dict:
    """PVGIS typical year → PySAM solar_resource_data (local standard time, India +5:30)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'pvgis_tmy_{lat:.2f}_{lon:.2f}.json')
    if not os.path.exists(path):
        r = requests.get('https://re.jrc.ec.europa.eu/api/v5_2/tmy', params={'lat': round(lat, 4), 'lon': round(lon, 4), 'outputformat': 'json'}, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f'PVGIS weather for {lat:.3f}, {lon:.3f} could not be downloaded ({r.status_code}).')
        open(path, 'w').write(r.text)
    data = json.load(open(path))
    rows = data['outputs']['tmy_hourly']
    elev = float(data['inputs']['location'].get('elevation') or 50)
    return to_resource(rows, lat, lon, elev, tz=5.5)


def to_resource(rows: list, lat: float, lon: float, elev: float, tz: float) -> dict:
    """PVGIS rows (UTC 'YYYYMMDD:HHMM', G(h), Gb(n), Gd(h), T2m, WS10m) → SAM data, shifted to local standard time
    and put in calendar order starting 1 January 00:xx."""
    shift = int(math.floor(tz))
    extra = int(round((tz - shift) * 60))
    n = len(rows)
    out = {k: [] for k in ('year', 'month', 'day', 'hour', 'minute', 'gh', 'dn', 'df', 'tdry', 'wspd')}
    for i in range(n):
        r = rows[(i - shift) % n]                              # local hour i ← UTC hour i - shift
        t = rows[i]['time(UTC)']
        out['year'].append(2023); out['month'].append(int(t[4:6])); out['day'].append(int(t[6:8]))
        out['hour'].append(int(t[9:11])); out['minute'].append((int(t[11:13]) + extra) % 60)
        out['gh'].append(float(r['G(h)'])); out['dn'].append(float(r['Gb(n)'])); out['df'].append(float(r['Gd(h)']))
        out['tdry'].append(float(r['T2m'])); out['wspd'].append(float(r['WS10m']))
    out.update({'lat': lat, 'lon': lon, 'tz': tz, 'elev': elev})
    return out


def simulate(arrays: list, resource: dict) -> dict:
    """arrays: [{name, kwp, tilt, facing ('S'/'N'/'E'/'W'), mount ('roof' | 'rack')}] → month-wise + yearly."""
    import PySAM.Pvwattsv8 as pv
    monthly = [0.0] * 12
    per_array = []
    poa_w = [0.0] * 12          # kWp-weighted plane-of-array sunshine, for the performance ratio
    kwp_total = 0.0
    for a in arrays:
        if a['kwp'] <= 0:
            continue
        m = pv.default('PVWattsNone')
        m.SolarResource.solar_resource_data = resource
        sd = m.SystemDesign
        sd.system_capacity = float(a['kwp'])
        sd.tilt = float(a['tilt'])
        sd.azimuth = AZ.get(a.get('facing', 'S'), 180.0)
        sd.array_type = 1.0 if a.get('mount') == 'roof' else 0.0   # 1 = fixed roof mount (flush), 0 = fixed open rack
        sd.module_type = 1.0                                       # premium (TOPCon / mono PERC class)
        sd.losses = LOSSES
        sd.inv_eff = INV_EFF
        sd.dc_ac_ratio = 1.2
        sd.gcr = 0.4
        m.execute()
        mo = list(m.Outputs.ac_monthly)
        per_array.append({'name': a['name'], 'kwp': a['kwp'], 'tilt': a['tilt'], 'facing': a.get('facing'), 'annualKwh': round(sum(mo)),
                          'kwhPerKwp': round(sum(mo) / a['kwp'])})
        monthly = [x + y for x, y in zip(monthly, mo)]
        poa_w = [x + y * a['kwp'] for x, y in zip(poa_w, m.Outputs.poa_monthly)]
        kwp_total += a['kwp']
    annual = sum(monthly)
    poa_year = sum(poa_w) / kwp_total if kwp_total else 0              # kWh/m² in the plane of the panels
    return {
        'monthlyKwh': [round(x) for x in monthly], 'annualKwh': round(annual),
        'kwhPerKwp': round(annual / kwp_total) if kwp_total else 0,
        'pr': round(annual / (kwp_total * poa_year), 3) if kwp_total and poa_year else None,
        'arrays': per_array, 'model': f'NREL SAM (PySAM) PVWatts v8 · losses {LOSSES:g} % · inverter {INV_EFF:g} %',
    }


def chart(result: dict, title: str, subtitle: str, out_path: str) -> None:
    """Month-wise bar chart + table (PNG), in the drawings' style."""
    from PIL import Image, ImageDraw
    from .render import font, INK, MUTED, TEAL
    W, H = 1800, 1150
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    d.text((60, 40), title, fill=INK, font=font(40, True))
    d.text((60, 100), subtitle, fill=MUTED, font=font(24))
    mo = result['monthlyKwh']
    top = max(mo) * 1.15 or 1
    x0, y0, cw, ch = 140, 190, 1580, 560
    for k in range(6):
        y = y0 + ch - ch * k / 5
        d.line([x0, y, x0 + cw, y], fill=(226, 232, 240), width=2)
        d.text((x0 - 14, y), f'{top * k / 5 / 1000:,.0f}k' if top >= 5000 else f'{top * k / 5:,.0f}', fill=MUTED, font=font(20), anchor='rm')
    bw = cw / 12
    for i, v in enumerate(mo):
        bh = ch * v / top
        d.rectangle([x0 + i * bw + 14, y0 + ch - bh, x0 + (i + 1) * bw - 14, y0 + ch], fill=TEAL)
        d.text((x0 + i * bw + bw / 2, y0 + ch - bh - 8), f'{v:,}', fill=INK, font=font(19, True), anchor='md')
        d.text((x0 + i * bw + bw / 2, y0 + ch + 14), MONTHS[i], fill=INK, font=font(22), anchor='mt')
    d.text((60, y0 + ch / 2), 'units', fill=MUTED, font=font(20), anchor='lm')
    y = y0 + ch + 80
    d.text((60, y), f"Year: {result['annualKwh']:,} units  ·  {result['kwhPerKwp']:,} units per kWp"
                    + (f"  ·  performance ratio {result['pr'] * 100:.0f} %" if result.get('pr') else ''), fill=INK, font=font(30, True))
    y += 60
    for a in result['arrays']:
        d.text((60, y), f"{a['name']}: {a['kwp']} kWp, tilt {a['tilt']}°, facing {a['facing']} → {a['annualKwh']:,} units ({a['kwhPerKwp']:,} per kWp)", fill=INK, font=font(22))
        y += 34
    d.text((60, H - 92), f"{result['model']} · {result.get('weather', '')}.", fill=MUTED, font=font(19))
    d.text((60, H - 62), 'Estimates for a typical year — actual output varies with the weather, dust and upkeep.', fill=MUTED, font=font(19))
    img.save(out_path, optimize=True)
