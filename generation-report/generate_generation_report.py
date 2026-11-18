#!/usr/bin/env python3
# =============================================================================
#  NRG Technologists - Solar Generation Report (PVsyst-style)
#  File: generate_generation_report.py        VERSION: v0.1  (2026-11-18)
#  Status: SAMPLE for owner review
#
#  What it does
#    Hour-by-hour simulation of a rooftop solar plant for a whole year
#    (8760 hours), the same way PVsyst works:
#      weather -> sun position -> light on the tilted panel -> row shading ->
#      angle (glass reflection) loss -> dust -> panel heat -> wiring ->
#      inverter -> grid.
#    Then repeats it for many tilts / directions to show the client how the
#    tilt changes the output, month by month.
#
#  Weather
#    Long-term monthly averages for the site (GHI, diffuse share, temperature)
#    are spread into hours with the sun's clear-sky shape. For the SAMPLE the
#    Vadodara values below are typical long-term figures (Meteonorm / NASA-SSE
#    range). For real projects, replace MONTHLY_CLIMATE with the site's
#    PVGIS / Meteonorm / NASA POWER monthly data.
#
#  Run:  python3 generate_generation_report.py
#  Needs: pvlib, pandas, numpy, matplotlib, reportlab
# =============================================================================

import os
import math
import numpy as np
import pandas as pd
import pvlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image, PageBreak,
                                KeepTogether)

VERSION = "v0.1"
REPORT_DATE = "18-Nov-2026"

# -----------------------------------------------------------------------------
# 1. PROJECT INPUTS  (everything a real project would change lives here)
# -----------------------------------------------------------------------------
PROJECT = {
    "client": "Sample Client (Demo)",
    "project": "100 kWp Rooftop Solar - Sample",
    "site": "Vadodara, Gujarat, India",
    "lat": 22.31, "lon": 73.18, "alt": 35, "tz": "Asia/Kolkata",
    "roof": "Flat RCC terrace, raised GI structure",
}

MODULE = {
    "name": "TOPCon mono-facial 620 Wp (generic)",
    "wp": 620.0,
    "length_m": 2.382, "width_m": 1.134,
    "eff": 0.2295,
    "gamma_pmax": -0.0029,       # -0.29 % per deg C
    "quality_gain": 0.004,       # +0.4 % positive power tolerance
    "lid": 0.005,                # 0.5 % light-induced degradation (n-type)
    "deg_year1": 0.010,          # 1.0 % first year (warranty)
    "deg_yearly": 0.004,         # 0.4 % per year after
}
N_MODULES = 162                  # 9 strings x 18 modules
STRINGS = "9 strings x 18 modules"
INVERTER = {"name": "String inverter 50 kW (generic)", "count": 2,
            "pac_kw": 50.0, "eta_nom": 0.985, "eta_euro": 0.982}

DESIGN_TILT = 10.0               # degrees
DESIGN_AZIMUTH = 180.0           # 180 = due south (pvlib convention)
ROWS_PER_TABLE = 2               # 2 panels up the slope, portrait
ALBEDO = 0.20

# Losses (fractions) - each one is explained in the report
LOSS = {
    "mismatch": 0.015,
    "dc_ohmic_stc": 0.015,       # 1.5 % at full power (falls with lower power)
    "ac_ohmic_stc": 0.005,
    "unavailability": 0.010,     # grid outages / maintenance
    "shade_electrical_factor": 1.5,  # portrait panels: a shadow on the bottom
                                     # cells hurts more than its area
}
# Dust (soiling) per month, for tilt >= 10 deg, cleaning every 15 days
SOILING_MONTHLY = [0.035, 0.035, 0.040, 0.050, 0.050, 0.025,
                   0.010, 0.010, 0.015, 0.030, 0.035, 0.035]

# Long-term monthly climate for the site (SAMPLE: Vadodara)
#   GHI kWh/m2/day, diffuse share, avg daily MIN temp C, avg daily MAX temp C
MONTHLY_CLIMATE = [
    (4.70, 0.30, 12.0, 29.0), (5.55, 0.30, 14.5, 32.0), (6.35, 0.32, 19.5, 36.5),
    (6.90, 0.34, 23.5, 40.0), (7.05, 0.36, 27.0, 41.0), (5.85, 0.48, 27.5, 37.0),
    (4.30, 0.62, 26.0, 32.5), (4.10, 0.62, 25.5, 31.5), (5.05, 0.50, 25.0, 33.0),
    (5.45, 0.35, 21.5, 35.5), (4.85, 0.30, 16.5, 32.5), (4.45, 0.30, 13.0, 30.0),
]
WIND_MS = 2.5

# Uncertainty used for P50 / P90
SIGMA = {"Year-to-year weather": 0.040, "Weather data source": 0.030,
         "Model & losses": 0.025}

# NRG's standard commitment
NRG_STANDARD_YIELD = 1450.0      # kWh per kWp per year

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
CHART_DIR = os.path.join(OUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# Brand colours
NAVY = "#14325C"
GREEN = "#2E8B57"
SUN = "#F2A900"
GREY = "#6B7280"
LIGHT = "#EEF3F8"

PNOM_KW = N_MODULES * MODULE["wp"] / 1000.0
TABLE_SLOPE_M = ROWS_PER_TABLE * MODULE["length_m"] + 0.02 * (ROWS_PER_TABLE - 1)


# -----------------------------------------------------------------------------
# 2. WEATHER: build 8760 hourly values from the monthly averages
# -----------------------------------------------------------------------------
def build_weather():
    loc = pvlib.location.Location(PROJECT["lat"], PROJECT["lon"], PROJECT["tz"],
                                  PROJECT["alt"])
    # mid-hour time stamps, non-leap year
    times = pd.date_range("2025-01-01 00:30", "2025-12-31 23:30", freq="h",
                          tz=PROJECT["tz"])
    sp = loc.get_solarposition(times)
    cs = loc.get_clearsky(times, model="ineichen", solar_position=sp)

    rng = np.random.default_rng(42)
    ghi = pd.Series(0.0, index=times)
    month = times.month
    for m in range(1, 13):
        gdaily = MONTHLY_CLIMATE[m - 1][0]
        mask = month == m
        cs_m = cs["ghi"][mask]
        # day-to-day variation (cloudier, more variable in monsoon)
        sig = 0.30 if m in (6, 7, 8, 9) else 0.08
        days = cs_m.index.day
        nd = DAYS_IN_MONTH[m - 1]
        f = np.clip(rng.lognormal(0, sig, nd), 0.25, 1.6)
        g = cs_m.values * f[days - 1]
        target = gdaily * nd * 1000.0           # Wh/m2 in the month
        for _ in range(6):                      # rescale, cap at 105 % clear sky
            g = g * target / g.sum()
            g = np.minimum(g, cs_m.values * 1.05)
        ghi[mask] = g * target / g.sum()

    # split into direct and diffuse (Erbs), then match the monthly diffuse share
    doy = times.dayofyear
    erbs = pvlib.irradiance.erbs(ghi, sp["apparent_zenith"], times)
    dhi = pd.Series(erbs["dhi"], index=times).fillna(0.0)
    for m in range(1, 13):
        mask = month == m
        kd_target = MONTHLY_CLIMATE[m - 1][1]
        cur = dhi[mask].sum() / max(ghi[mask].sum(), 1e-9)
        dhi[mask] = np.minimum(dhi[mask] * kd_target / cur, ghi[mask])
    cosz = np.cos(np.radians(sp["apparent_zenith"].clip(upper=89)))
    dni = ((ghi - dhi) / cosz).where(sp["apparent_zenith"] < 87, 0.0).clip(lower=0)
    dni = np.minimum(dni, cs["dni"] * 1.1 + 50)
    dhi = ghi - dni * cosz.where(sp["apparent_zenith"] < 87, 0.0)

    # temperature: daily cycle between the month's average min (about 6 am)
    # and average max (about 2:30 pm)
    hour = times.hour + 0.5
    tmin = np.array([MONTHLY_CLIMATE[m - 1][2] for m in month])
    tmax = np.array([MONTHLY_CLIMATE[m - 1][3] for m in month])
    tair = (tmin + tmax) / 2 + (tmax - tmin) / 2 * np.cos(
        2 * np.pi * (hour - 14.5) / 24)

    wx = pd.DataFrame({"ghi": ghi, "dni": dni, "dhi": dhi.clip(lower=0),
                       "tair": tair, "wind": WIND_MS}, index=times)
    return loc, sp, wx


# -----------------------------------------------------------------------------
# 3. ROW GEOMETRY: gap needed so rows don't shade each other 9 am - 3 pm in
#    mid-winter (21 Dec), plus a 0.6 m walkway for cleaning
# -----------------------------------------------------------------------------
def sun_at_solar_hour(lat, decl, hour_angle):
    la, de, h = map(math.radians, (lat, decl, hour_angle))
    sin_el = math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(h)
    el = math.asin(sin_el)
    cos_az = (math.sin(de) - math.sin(la) * sin_el) / (math.cos(la) * math.cos(el))
    az = math.degrees(math.acos(max(-1, min(1, cos_az))))   # from north
    if hour_angle > 0:
        az = 360 - az
    return math.degrees(el), az


def pitch_for_tilt(tilt, walkway=0.6):
    """Row pitch (front of one table to front of the next), metres."""
    L = TABLE_SLOPE_M
    b = math.radians(tilt)
    need = L * math.cos(b) + walkway
    if tilt > 0:
        el, az = sun_at_solar_hour(PROJECT["lat"], -23.44, -45)   # 9 am solar
        ap = math.atan(math.tan(math.radians(el)) /
                       abs(math.cos(math.radians(az - 180))))      # profile angle
        shadow_free = L * math.sin(ap + b) / math.sin(ap)
        need = max(need, shadow_free)
    return need


# -----------------------------------------------------------------------------
# 4. ONE FULL SIMULATION (one tilt / direction)
# -----------------------------------------------------------------------------
def simulate(loc, sp, wx, tilt, azimuth, pitch=None, soiling_mult=None,
             pnom_kw=PNOM_KW, inv_kw=None, rows_shading=True):
    if pitch is None:
        pitch = pitch_for_tilt(tilt)
    if soiling_mult is None:
        # flat panels hold dust and water; they get dirtier
        soiling_mult = 1.6 if tilt < 3 else (1.25 if tilt < 8 else 1.0)
    if inv_kw is None:
        inv_kw = INVERTER["count"] * INVERTER["pac_kw"] * pnom_kw / PNOM_KW

    zen, saz = sp["apparent_zenith"], sp["azimuth"]
    dni_extra = pvlib.irradiance.get_extra_radiation(wx.index)
    am = pvlib.atmosphere.get_relative_airmass(zen)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, zen, saz, wx["dni"], wx["ghi"], wx["dhi"],
        dni_extra=dni_extra, airmass=am, albedo=ALBEDO, model="perez")
    beam = poa["poa_direct"].fillna(0).clip(lower=0)
    sky = poa["poa_sky_diffuse"].fillna(0).clip(lower=0)
    gnd = poa["poa_ground_diffuse"].fillna(0).clip(lower=0)
    g_inc = beam + sky + gnd

    # --- near shading: rows shading rows -------------------------------
    L = TABLE_SLOPE_M
    b = math.radians(tilt)
    if rows_shading and tilt > 0:
        el = np.radians((90 - zen).clip(lower=0.5))
        daz = np.radians(saz - azimuth)
        cos_daz = np.cos(daz)
        ap = np.arctan(np.tan(el) / np.where(cos_daz > 0.02, cos_daz, np.nan))
        fs = 1 - pitch * np.sin(ap) / (L * np.sin(ap + b))
        fs = pd.Series(np.nan_to_num(fs, nan=0.0), index=wx.index).clip(0, 1)
        fs_el = (fs * LOSS["shade_electrical_factor"]).clip(0, 1)
        gcr = L / pitch
        mask_ang = pvlib.shading.masking_angle_passias(tilt, gcr)
        sky_loss = pvlib.shading.sky_diffuse_passias(mask_ang)
    else:
        fs_el = pd.Series(0.0, index=wx.index)
        sky_loss = 0.0
    beam_s = beam * (1 - fs_el)
    sky_s = sky * (1 - sky_loss)
    g_shaded = beam_s + sky_s + gnd

    # --- IAM: glass reflects more light when the sun is at a low angle ---
    aoi = pvlib.irradiance.aoi(tilt, azimuth, zen, saz)
    iam_b = pvlib.iam.ashrae(aoi, b=0.05)
    iam_d = pvlib.iam.marion_diffuse("ashrae", max(tilt, 0.01), b=0.05)
    g_iam = beam_s * iam_b + sky_s * float(iam_d["sky"]) + gnd * float(iam_d["ground"])

    # --- dust ---------------------------------------------------------------
    soil = pd.Series([SOILING_MONTHLY[m - 1] * soiling_mult
                      for m in wx.index.month], index=wx.index)
    g_eff = g_iam * (1 - soil)

    # --- PV array -------------------------------------------------------------
    p_stc = g_eff / 1000.0 * pnom_kw                       # kW at 25 C, no losses
    # low-light behaviour (ADR model, typical c-Si)
    adr = dict(k_a=99.924, k_d=-5.49097, tc_d=0.01918, k_rs=0.06999,
               k_rsh=0.26144)
    ge = g_eff.clip(lower=1.0)
    rel_irr = (pvlib.pvarray.pvefficiency_adr(ge, 25.0, **adr) /
               pvlib.pvarray.pvefficiency_adr(1000.0, 25.0, **adr))
    rel_irr = rel_irr.where(g_eff > 1.0, 0.0)
    p_irr = p_stc * rel_irr
    tcell = pvlib.temperature.pvsyst_cell(g_inc, wx["tair"], wx["wind"],
                                          u_c=29.0, u_v=0.0,
                                          module_efficiency=MODULE["eff"],
                                          alpha_absorption=0.9)
    p_temp = p_irr * (1 + MODULE["gamma_pmax"] * (tcell - 25.0))
    p_qual = p_temp * (1 + MODULE["quality_gain"])
    p_lid = p_qual * (1 - MODULE["lid"])
    p_mm = p_lid * (1 - LOSS["mismatch"])
    dc_ohm = LOSS["dc_ohmic_stc"] * (p_mm / pnom_kw)
    p_dc = p_mm * (1 - dc_ohm)

    # --- inverter (PVWatts efficiency curve), then clipping --------------------
    pdc0 = inv_kw / INVERTER["eta_nom"]
    zeta = (p_dc / pdc0).clip(lower=1e-6)
    eta = (INVERTER["eta_nom"] / 0.9637) * (-0.0162 * zeta - 0.0059 / zeta + 0.9858)
    eta = eta.clip(lower=0)
    p_ac_unclip = (p_dc * eta).where(p_dc > 0.002 * pdc0, 0.0)
    p_ac = p_ac_unclip.clip(upper=inv_kw)
    ac_ohm = LOSS["ac_ohmic_stc"] * (p_ac / inv_kw)
    p_ac2 = p_ac * (1 - ac_ohm)
    p_grid = p_ac2 * (1 - LOSS["unavailability"])

    h = pd.DataFrame({
        "ghi": wx["ghi"], "dhi": wx["dhi"], "tair": wx["tair"],
        "g_inc": g_inc, "g_shaded": g_shaded, "g_iam": g_iam, "g_eff": g_eff,
        "p_stc": p_stc, "p_irr": p_irr, "p_temp": p_temp, "p_qual": p_qual,
        "p_lid": p_lid, "p_mm": p_mm, "p_dc": p_dc, "p_ac_unclip": p_ac_unclip,
        "p_ac": p_ac, "p_ac2": p_ac2, "p_grid": p_grid, "tcell": tcell,
    })
    return h


def monthly_table(h, pnom_kw=PNOM_KW):
    m = h.resample("MS").sum() / 1000.0          # kWh/m2 or MWh
    m["tair"] = h["tair"].resample("MS").mean()
    m.index = MONTHS
    out = pd.DataFrame({
        "GlobHor": m["ghi"], "DiffHor": m["dhi"], "T_Amb": m["tair"],
        "GlobInc": m["g_inc"], "GlobEff": m["g_eff"],
        "EArray": m["p_dc"], "E_Grid": m["p_grid"],
    })
    out["PR"] = out["E_Grid"] / (out["GlobInc"] * pnom_kw / 1000.0)
    out["Yield/day"] = out["E_Grid"] * 1000 / pnom_kw / DAYS_IN_MONTH
    return out


def loss_chain(h):
    s = h.sum() / 1000.0
    rows = []
    rows.append(("Sunlight on flat ground (GHI)", s["ghi"], "kWh/m2", None))
    rows.append(("Extra sunlight from tilting the panels", s["g_inc"], "kWh/m2",
                 s["g_inc"] / s["ghi"] - 1))
    rows.append(("Row-to-row shading (near shading)", s["g_shaded"], "kWh/m2",
                 s["g_shaded"] / s["g_inc"] - 1))
    rows.append(("Glass reflection at low sun angles (IAM)", s["g_iam"], "kWh/m2",
                 s["g_iam"] / s["g_shaded"] - 1))
    rows.append(("Dust on panels (soiling)", s["g_eff"], "kWh/m2",
                 s["g_eff"] / s["g_iam"] - 1))
    rows.append(("= Sunlight reaching the cells x panel area -> energy at "
                 "standard 25 C (STC)", s["p_stc"], "MWh", None))
    rows.append(("Low-light performance (irradiance level)", s["p_irr"], "MWh",
                 s["p_irr"] / s["p_stc"] - 1))
    rows.append(("Panel heat (temperature)", s["p_temp"], "MWh",
                 s["p_temp"] / s["p_irr"] - 1))
    rows.append(("Module quality (positive power tolerance)", s["p_qual"], "MWh",
                 s["p_qual"] / s["p_temp"] - 1))
    rows.append(("Light-induced degradation (LID)", s["p_lid"], "MWh",
                 s["p_lid"] / s["p_qual"] - 1))
    rows.append(("Mismatch between panels", s["p_mm"], "MWh",
                 s["p_mm"] / s["p_lid"] - 1))
    rows.append(("DC cable loss (ohmic)", s["p_dc"], "MWh",
                 s["p_dc"] / s["p_mm"] - 1))
    rows.append(("= DC energy at inverter input", s["p_dc"], "MWh", None))
    rows.append(("Inverter conversion efficiency", s["p_ac_unclip"], "MWh",
                 s["p_ac_unclip"] / s["p_dc"] - 1))
    rows.append(("Inverter over-power (clipping)", s["p_ac"], "MWh",
                 s["p_ac"] / s["p_ac_unclip"] - 1))
    rows.append(("AC cable loss", s["p_ac2"], "MWh",
                 s["p_ac2"] / s["p_ac"] - 1))
    rows.append(("Grid outages / maintenance (unavailability)", s["p_grid"],
                 "MWh", s["p_grid"] / s["p_ac2"] - 1))
    rows.append(("= ENERGY EXPORTED TO GRID / USED ON SITE", s["p_grid"], "MWh",
                 None))
    return rows


# -----------------------------------------------------------------------------
# 5. CHARTS
# -----------------------------------------------------------------------------
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#9CA3AF", "axes.titleweight": "bold",
                     "axes.titlesize": 10})


def chart_monthly_energy(mt, path):
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
    bars = ax.bar(MONTHS, mt["E_Grid"], color=GREEN, width=0.65)
    for b_, v in zip(bars, mt["E_Grid"]):
        ax.text(b_.get_x() + b_.get_width() / 2, v + 0.15, f"{v:.1f}",
                ha="center", va="bottom", fontsize=7.5, color="#111827")
    ax.set_ylabel("MWh (thousand units)")
    ax.set_title("Electricity produced each month (year 1)")
    ax.set_ylim(0, mt["E_Grid"].max() * 1.18)
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_normalized(h, mt, path):
    """PVsyst-style: kWh/kWp/day split into useful energy, system loss and
    collection loss."""
    m = h.resample("MS").sum()
    d = np.array(DAYS_IN_MONTH)
    yr = m["g_inc"].values / 1000 / d                    # reference yield
    ya = m["p_dc"].values / PNOM_KW / d                  # array yield
    yf = m["p_grid"].values / PNOM_KW / d                # final yield
    lc = yr - ya
    ls = ya - yf
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
    ax.bar(MONTHS, yf, color=GREEN, label=f"Useful energy  Yf = "
           f"{mt['E_Grid'].sum()*1000/PNOM_KW/365:.2f} kWh/kWp/day")
    ax.bar(MONTHS, ls, bottom=yf, color=SUN, label=f"Inverter & AC losses  "
           f"Ls = {ls.mean():.2f}")
    ax.bar(MONTHS, lc, bottom=yf + ls, color="#C0392B",
           label=f"Panel-side losses  Lc = {lc.mean():.2f}")
    ax.set_ylabel("kWh per kWp per day")
    ax.set_title("Normalised production per installed kWp")
    ax.legend(fontsize=7, loc="upper right", frameon=False)
    ax.set_ylim(0, yr.max() * 1.35)
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_pr(mt, path):
    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=200)
    ax.bar(MONTHS, mt["PR"] * 100, color=NAVY, width=0.6)
    pr_y = mt["E_Grid"].sum() / (mt["GlobInc"].sum() * PNOM_KW / 1000)
    ax.axhline(pr_y * 100, color=SUN, lw=1.5, ls="--")
    ax.text(-0.5, 89.5, f"--- Year PR {pr_y*100:.1f} %", ha="left",
            color="#92400E", fontsize=8)
    for i, v in enumerate(mt["PR"] * 100):
        ax.text(i, v - 3.5, f"{v:.0f}", ha="center", color="white", fontsize=7)
    ax.set_ylim(60, 92)
    ax.set_ylabel("Performance ratio %")
    ax.set_title("Performance ratio (PR) by month - lower in hot months")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_sunpath(path):
    """Sun height through the day on the key dates (solar time)."""
    loc_lat = PROJECT["lat"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=200)
    days = [("21 Jun (longest day)", 172, "#C0392B"),
            ("21 Mar / 23 Sep", 80, SUN),
            ("21 Dec (shortest day)", 355, NAVY)]
    for name, doy, c in days:
        decl = math.degrees(pvlib.solarposition.declination_spencer71(doy))
        hrs, el = [], []
        for ha in np.arange(-110, 110.5, 0.5):
            e, _ = sun_at_solar_hour(loc_lat, decl, ha)
            if e > 0:
                hrs.append(12 + ha / 15)
                el.append(e)
        ax.plot(hrs, el, color=c, lw=2, label=name)
        e_noon, a_noon = sun_at_solar_hour(loc_lat, decl, 0.0001)
        side = "north" if (a_noon < 90 or a_noon > 270) else "south"
        ax.annotate(f"noon {e_noon:.0f} deg, {side}", (12, e_noon),
                    xytext=(0, 4), textcoords="offset points", ha="center",
                    fontsize=7, color=c)
    ax.axhspan(0, 15, color="#F3F4F6", zorder=0)
    ax.text(9.2, 5, "weak morning / evening sun (below 15 deg)", fontsize=6.5,
            color=GREY)
    ax.set_xlim(5.5, 18.5)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(6, 19))
    ax.set_xticklabels([f"{h}h" for h in range(6, 19)])
    ax.set_xlabel("Solar time (local clock is about 35 minutes later)")
    ax.set_ylabel("Sun height (deg)")
    ax.set_title(f"How high the sun gets at the site (lat {loc_lat:.1f} N)")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_tilt_annual(tilt_df, path):
    fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
    x = tilt_df["Tilt"].values
    y = tilt_df["Yield"].values
    ax.plot(x, y, "-o", color=NAVY, lw=2, ms=4)
    best = tilt_df.loc[tilt_df["Yield"].idxmax()]
    ax.plot([DESIGN_TILT], tilt_df.set_index("Tilt").loc[DESIGN_TILT, "Yield"],
            "o", ms=10, mfc="none", mec=GREEN, mew=2)
    ax.annotate(f"Proposed {DESIGN_TILT:.0f} deg", (DESIGN_TILT,
                tilt_df.set_index("Tilt").loc[DESIGN_TILT, "Yield"]),
                xytext=(6, -18), textcoords="offset points", color=GREEN,
                fontsize=8)
    ax.annotate(f"Highest per kWp: {best['Tilt']:.0f} deg", (best["Tilt"],
                best["Yield"]), xytext=(0, 10), textcoords="offset points",
                ha="center", color=NAVY, fontsize=8)
    ax.set_xlabel("Panel tilt (deg), facing south")
    ax.set_ylabel("Units per kWp per year")
    ax.set_title("How tilt changes yearly output per kWp (south facing)")
    ax.set_ylim(y.min() * 0.97, y.max() * 1.02)
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_tilt_monthly(monthly_by_tilt, path):
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=200)
    cols = {0: "#9CA3AF", 10: GREEN, 20: SUN, 30: "#C0392B"}
    for t, c in cols.items():
        ax.plot(MONTHS, monthly_by_tilt[t] / PNOM_KW * 1000 /
                np.array(DAYS_IN_MONTH), "-o", ms=3, lw=2 if t == 10 else 1.4,
                color=c, label=f"{t} deg")
    ax.set_ylabel("Units per kWp per day")
    ax.set_title("Month by month: higher tilt wins in winter, "
                 "low tilt wins in summer")
    ax.legend(fontsize=7.5, frameon=False, ncol=4, loc="upper right")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_loss_waterfall(rows, path):
    items = [(r[0], r[3]) for r in rows if r[3] is not None and r[3] < 0]
    items = sorted(items, key=lambda r: r[1])
    labels = [i[0].split(" (")[0] for i in items]
    vals = [abs(i[1]) * 100 for i in items]
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=200)
    ax.barh(labels[::-1], vals[::-1], color="#C0392B", height=0.6)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.08, i, f"{v:.1f} %", va="center", fontsize=7.5)
    ax.set_xlabel("Loss, % of energy at that stage")
    ax.set_title("Where the energy goes - losses, largest first")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.tick_params(axis="y", labelsize=7.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# -----------------------------------------------------------------------------
# 6. PDF
# -----------------------------------------------------------------------------
styles = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15,
                         textColor=colors.HexColor(NAVY), spaceAfter=6,
                         spaceBefore=2),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5,
                         textColor=colors.HexColor(NAVY), spaceBefore=8,
                         spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                           leading=12.5, spaceAfter=4),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.8,
                            leading=10, textColor=colors.HexColor("#374151")),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8,
                           leading=10),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8,
                            leading=10),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8,
                            leading=10, textColor=colors.white),
    "kpi_v": ParagraphStyle("kpi_v", fontName="Helvetica-Bold", fontSize=15,
                            leading=18, alignment=TA_CENTER,
                            textColor=colors.HexColor(NAVY)),
    "kpi_l": ParagraphStyle("kpi_l", fontName="Helvetica", fontSize=7.5,
                            leading=9.5, alignment=TA_CENTER,
                            textColor=colors.HexColor(GREY)),
    "callout": ParagraphStyle("callout", fontName="Helvetica", fontSize=9,
                              leading=12.5, textColor=colors.HexColor("#1F2937"),
                              backColor=colors.HexColor("#FFF7E0"),
                              borderColor=colors.HexColor(SUN), borderWidth=0.8,
                              borderPadding=6, spaceBefore=6, spaceAfter=8),
}


def P(t, s="body"):
    return Paragraph(t, styles[s])


def grid_table(data, col_widths, header_rows=1, zebra=True, bold_last=False,
               align_right_from=1, font=8):
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    st = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", font),
        ("FONT", (0, 0), (-1, header_rows - 1), "Helvetica-Bold", font),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor(NAVY)),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]
    if zebra:
        for r in range(header_rows, len(data)):
            if (r - header_rows) % 2 == 1:
                st.append(("BACKGROUND", (0, r), (-1, r),
                           colors.HexColor(LIGHT)))
    if bold_last:
        st.append(("FONT", (0, -1), (-1, -1), "Helvetica-Bold", font))
        st.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DCE7F3")))
    t.setStyle(TableStyle(st))
    return t


def on_page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(NAVY))
    canvas.rect(0, h - 16 * mm, w, 16 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor(SUN))
    canvas.rect(0, h - 17.2 * mm, w, 1.2 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(15 * mm, h - 10.5 * mm, "NRG Technologists")
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(w - 15 * mm, h - 7.5 * mm,
                           "Solar Generation Report (hourly simulation)")
    canvas.drawRightString(w - 15 * mm, h - 12 * mm,
                           f"{PROJECT['project']}  |  {PROJECT['site']}")
    canvas.setFillColor(colors.HexColor(GREY))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(15 * mm, 9 * mm,
                      f"Generation Report {VERSION}  |  {REPORT_DATE}  |  "
                      "SAMPLE - typical weather values, not site-measured")
    canvas.drawRightString(w - 15 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def kpi_row(items):
    cells = [[P(v, "kpi_v") for v, _ in items], [P(l, "kpi_l") for _, l in items]]
    w = 180 * mm / len(items)
    t = Table(cells, colWidths=[w] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(LIGHT)),
        ("LINEABOVE", (0, 0), (-1, 0), 2, colors.HexColor(GREEN)),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
    ]))
    return t


def build_pdf(path, ctx):
    doc = BaseDocTemplate(path, pagesize=A4, leftMargin=15 * mm,
                          rightMargin=15 * mm, topMargin=22 * mm,
                          bottomMargin=15 * mm,
                          title=f"Solar Generation Report {VERSION}",
                          author="NRG Technologists")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
    W = doc.width
    mt, rows, tilt_df = ctx["mt"], ctx["rows"], ctx["tilt_df"]
    e_year = mt["E_Grid"].sum()
    spec = e_year * 1000 / PNOM_KW
    pr_y = e_year / (mt["GlobInc"].sum() * PNOM_KW / 1000)
    s = []

    # ---------------- Page 1: summary ----------------
    s.append(P("Solar Generation Report", "h1"))
    s.append(P(f"<b>{PROJECT['client']}</b> &nbsp;|&nbsp; {PROJECT['project']}"
               f" &nbsp;|&nbsp; {PROJECT['site']}"))
    s.append(Spacer(1, 4))
    s.append(kpi_row([
        (f"{PNOM_KW:.2f} kWp", "Installed DC capacity"),
        (f"{e_year*1000:,.0f}", "Units (kWh) in year 1"),
        (f"{spec:,.0f}", "Units per kWp per year"),
        (f"{pr_y*100:.1f} %", "Performance ratio (PR)"),
    ]))
    s.append(Spacer(1, 8))
    s.append(P("What this report tells you", "h2"))
    s.append(P(
        "This report works out, hour by hour for a full year, how much "
        "electricity the proposed solar plant will produce at this site. It "
        "starts from long-term sunshine and temperature data for the location, "
        "follows the sunlight onto the tilted panels, and then takes away every "
        "real-world loss - shading between rows, reflection off the glass, "
        "dust, panel heat, cable and inverter losses, and grid outages. "
        "The same method is used by PVsyst, the industry-standard design "
        "software. Section 5 shows how changing the panel tilt or direction "
        "would change the output, so the choice of tilt is clear."))
    s.append(P("System at a glance", "h2"))
    sysdata = [
        ["Item", "Value", "Item", "Value"],
        ["Location", f"{PROJECT['lat']:.2f} N, {PROJECT['lon']:.2f} E",
         "Panels", f"{N_MODULES} x {MODULE['wp']:.0f} Wp"],
        ["Altitude", f"{PROJECT['alt']} m", "Panel type", "TOPCon, mono-facial"],
        ["Roof", "Flat RCC, raised GI", "Stringing", STRINGS],
        ["Tilt / direction", f"{DESIGN_TILT:.0f} deg, facing due south",
         "Inverters", f"{INVERTER['count']} x {INVERTER['pac_kw']:.0f} kW"],
        ["Table layout", f"{ROWS_PER_TABLE} panels up the slope, portrait",
         "DC : AC ratio", f"{PNOM_KW/(INVERTER['count']*INVERTER['pac_kw']):.2f}"],
        ["Row pitch", f"{ctx['pitch']:.2f} m (front to front)",
         "Ground reflection", f"{ALBEDO:.2f} (concrete terrace)"],
    ]
    s.append(grid_table(sysdata, [28 * mm, 62 * mm, 28 * mm, 62 * mm],
                        align_right_from=9))
    s.append(Spacer(1, 6))
    s.append(Image(ctx["c_month"], width=W, height=W * 2.9 / 7.2))
    p90 = ctx["p90"]
    s.append(P(
        f"<b>Expected (P50):</b> {e_year*1000:,.0f} units in year 1 "
        f"({spec:,.0f} units/kWp). &nbsp; <b>Safe figure (P90):</b> "
        f"{e_year*1000*p90:,.0f} units ({spec*p90:,.0f} units/kWp) - production "
        f"will be above this in 9 years out of 10. &nbsp; NRG's standard "
        f"commitment of <b>{NRG_STANDARD_YIELD:,.0f} units/kWp</b> "
        f"= {NRG_STANDARD_YIELD*PNOM_KW:,.0f} units/year sits "
        f"{(1-NRG_STANDARD_YIELD/spec)*100:.1f} % below the expected value.",
        "callout"))
    tq = tilt_df.set_index("Tilt")
    qt = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    qdata = [["Tilt (facing south)"] + [f"{t:.0f} deg" for t in qt],
             ["Units per kWp / year"] + [f"{tq.loc[t,'Yield']:,.0f}" for t in qt],
             [f"vs {DESIGN_TILT:.0f} deg"] +
             [f"{(tq.loc[t,'Yield']/tq.loc[DESIGN_TILT,'Yield']-1)*100:+.1f} %"
              for t in qt]]
    s.append(P("Effect of tilt at a glance (details in section 5)", "h2"))
    qtab = grid_table(qdata, [40 * mm] + [20 * mm] * 7, zebra=True)
    ci = qt.index(DESIGN_TILT) + 1
    qtab.setStyle(TableStyle([("BACKGROUND", (ci, 1), (ci, -1),
                               colors.HexColor("#D1FAE5")),
                              ("FONT", (ci, 1), (ci, -1), "Helvetica-Bold", 8)]))
    s.append(qtab)

    s.append(PageBreak())
    # ---------------- Page 2: site & weather ----------------
    s.append(P("1. Site and weather data", "h1"))
    s.append(P(
        "Solar output depends first on how much sunlight falls on the site "
        "(GHI - global horizontal irradiation) and how much of it is "
        "<i>diffuse</i> (scattered by clouds and haze). In the monsoon "
        "(June-September) more than half of the light is diffuse, so tilting "
        "the panels helps much less in those months. Temperature matters "
        "because hot panels produce less."))
    wdata = [["Month", "GHI\nkWh/m2", "Diffuse\nkWh/m2", "Diffuse\nshare",
              "Avg temp\nC", "Sun hours*\nper day"]]
    for mo in MONTHS:
        r = mt.loc[mo]
        wdata.append([mo, f"{r['GlobHor']:.1f}", f"{r['DiffHor']:.1f}",
                      f"{r['DiffHor']/r['GlobHor']*100:.0f} %",
                      f"{r['T_Amb']:.1f}",
                      f"{r['GlobHor']/DAYS_IN_MONTH[MONTHS.index(mo)]:.2f}"])
    wdata.append(["Year", f"{mt['GlobHor'].sum():.0f}",
                  f"{mt['DiffHor'].sum():.0f}",
                  f"{mt['DiffHor'].sum()/mt['GlobHor'].sum()*100:.0f} %",
                  f"{mt['T_Amb'].mean():.1f}",
                  f"{mt['GlobHor'].sum()/365:.2f}"])
    s.append(grid_table(wdata, [22 * mm] + [31.6 * mm] * 5, bold_last=True))
    s.append(P("* 'Peak sun hours' = kWh/m2 per day, i.e. hours of full "
               "1000 W/m2 sunshine.", "small"))
    s.append(Spacer(1, 6))
    s.append(Image(ctx["c_sun"], width=W, height=W * 3.0 / 7.2))
    s.append(P(
        "Weather source for this sample: typical long-term monthly values for "
        "Vadodara (Meteonorm / NASA-SSE range), spread into 8,760 hourly values "
        "using the clear-sky shape of the sun with realistic cloudy and clear "
        "days. For a client report the site's own PVGIS or Meteonorm data "
        "is used.", "small"))

    s.append(PageBreak())
    # ---------------- Page 3: main results ----------------
    s.append(P("2. Month-by-month results", "h1"))
    s.append(P(
        "<b>GlobInc</b> is sunlight on the tilted panel, <b>GlobEff</b> is what "
        "is left after shading, glass reflection and dust. <b>EArray</b> is DC "
        "energy from the panels, <b>E_Grid</b> is the AC energy delivered. "
        "<b>PR</b> (performance ratio) is the share of the sunlight's potential "
        "that becomes useful electricity - a well-built plant in Gujarat "
        "achieves 76-82 %."))
    rdata = [["Month", "GlobHor\nkWh/m2", "DiffHor\nkWh/m2", "T_Amb\nC",
              "GlobInc\nkWh/m2", "GlobEff\nkWh/m2", "EArray\nkWh",
              "E_Grid\nkWh", "Units/kWp\n/day", "PR"]]
    for mo in MONTHS:
        r = mt.loc[mo]
        rdata.append([mo, f"{r['GlobHor']:.1f}", f"{r['DiffHor']:.1f}",
                      f"{r['T_Amb']:.1f}", f"{r['GlobInc']:.1f}",
                      f"{r['GlobEff']:.1f}", f"{r['EArray']*1000:,.0f}",
                      f"{r['E_Grid']*1000:,.0f}", f"{r['Yield/day']:.2f}",
                      f"{r['PR']*100:.1f} %"])
    rdata.append(["Year", f"{mt['GlobHor'].sum():.0f}",
                  f"{mt['DiffHor'].sum():.0f}", f"{mt['T_Amb'].mean():.1f}",
                  f"{mt['GlobInc'].sum():.0f}", f"{mt['GlobEff'].sum():.0f}",
                  f"{mt['EArray'].sum()*1000:,.0f}",
                  f"{mt['E_Grid'].sum()*1000:,.0f}",
                  f"{spec/365:.2f}", f"{pr_y*100:.1f} %"])
    s.append(grid_table(rdata, [13 * mm] + [18.5 * mm] * 9, bold_last=True,
                        font=7.6))
    s.append(Spacer(1, 6))
    s.append(Image(ctx["c_norm"], width=W, height=W * 2.9 / 7.2))
    s.append(Image(ctx["c_pr"], width=W, height=W * 2.4 / 7.2))

    s.append(PageBreak())
    # ---------------- Page 4: loss diagram ----------------
    s.append(P("3. Loss diagram - from sunlight to units", "h1"))
    s.append(P(
        "Every step below is calculated for each of the 8,760 hours of the "
        "year and added up. Percentages are relative to the energy at that "
        "step (the way PVsyst shows them)."))
    ldata = [["Step", "Change", "Result"]]
    for name, val, unit, pct in rows:
        is_total = name.startswith("=") or pct is None
        pct_s = "" if pct is None else f"{pct*100:+.1f} %"
        val_s = (f"{val:,.0f} {unit}" if unit == "kWh/m2"
                 else f"{val*1000:,.0f} kWh")
        ldata.append([P(("<b>%s</b>" % name) if is_total else name, "cell"),
                      pct_s, val_s])
    lt = grid_table(ldata, [118 * mm, 25 * mm, 37 * mm], zebra=False)
    extra = []
    for i, (name, val, unit, pct) in enumerate(rows, start=1):
        if pct is None:
            extra.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(LIGHT)))
        elif pct < 0:
            extra.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#B91C1C")))
        else:
            extra.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor(GREEN)))
    lt.setStyle(TableStyle(extra))
    s.append(lt)
    s.append(Spacer(1, 6))
    s.append(Image(ctx["c_loss"], width=W, height=W * 3.0 / 7.2))

    s.append(PageBreak())
    # ---------------- Page 5: losses explained ----------------
    s.append(P("4. Every loss explained, and what we do about it", "h1"))
    pct = {r[0]: r[3] for r in rows}

    def lp(key):
        v = pct.get(key)
        return "" if v is None else f"{v*100:+.1f} %"
    exp = [
        ["Loss", "Value", "What it means", "How NRG reduces it"],
        ["Row-to-row shading", lp("Row-to-row shading (near shading)"),
         "In winter mornings and evenings the sun is low and one row can "
         "shade the bottom of the next row.",
         "Row gap is designed so there is no shading 9 am - 3 pm even on 21 "
         "December."],
        ["Glass reflection (IAM)", lp("Glass reflection at low sun angles (IAM)"),
         "When sunlight hits the glass at a slant, part of it bounces off.",
         "Anti-reflective coated glass; correct tilt."],
        ["Dust (soiling)", lp("Dust on panels (soiling)"),
         "Dust, bird droppings and pollution block light. Highest in "
         "Mar-May, lowest in the monsoon.",
         "Cleaning every 15 days (weekly cleaning roughly halves this "
         "loss). A tilt of 10 deg or more lets rain wash the panels."],
        ["Low-light performance", lp("Low-light performance (irradiance level)"),
         "Panels are a little less efficient in weak light (mornings, "
         "evenings, cloudy days).", "Quality TOPCon cells with good "
         "low-light response."],
        ["Panel heat", lp("Panel heat (temperature)"),
         "Panels lose about 0.29 % of power for every 1 C above 25 C. On a "
         "May afternoon cells reach 60-65 C.",
         "Raised GI structure lets air flow under the panels; TOPCon has a "
         "lower heat loss than older PERC panels."],
        ["Module quality", lp("Module quality (positive power tolerance)"),
         "Panels are sold with 0 to +5 W tolerance, so they deliver slightly "
         "more than the label.", "Tier-1 makes, flash-test reports checked."],
        ["LID", lp("Light-induced degradation (LID)"),
         "A small one-time drop in the first hours of sunlight.",
         "n-type TOPCon has very low LID."],
        ["Mismatch", lp("Mismatch between panels"),
         "No two panels are identical; the weakest panel in a string drags "
         "the others down slightly.", "Panels sorted by current; strings "
         "of equal length and direction."],
        ["DC cable loss", lp("DC cable loss (ohmic)"),
         "Electricity heats the cables between panels and inverter.",
         "4 / 6 sq mm solar cable sized for under 1.5 % drop."],
        ["Inverter efficiency", lp("Inverter conversion efficiency"),
         "Converting DC to AC loses 1.5-2 % as heat.",
         f"Inverters with {INVERTER['eta_euro']*100:.1f} % Euro efficiency."],
        ["Inverter clipping", lp("Inverter over-power (clipping)"),
         "If the panels produce more than the inverter's rating, the "
         "extra is cut off.", "DC:AC ratio chosen so clipping stays small."],
        ["AC cable loss", lp("AC cable loss"),
         "Loss in the cable from inverter to the main panel.",
         "Cable sized for under 0.5 % drop."],
        ["Unavailability", lp("Grid outages / maintenance (unavailability)"),
         "When the grid trips the inverter must switch off (safety rule), "
         "so solar is lost during outages.", "Remote monitoring and quick "
         "service response."],
    ]
    et = [[P(c, "cellh") for c in exp[0]]]
    for row in exp[1:]:
        et.append([P(row[0], "cell"), P(f"<b>{row[1]}</b>", "cell"),
                   P(row[2], "cell"), P(row[3], "cell")])
    t = Table(et, colWidths=[30 * mm, 15 * mm, 72 * mm, 63 * mm], repeatRows=1)
    tst = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
           ("VALIGN", (0, 0), (-1, -1), "TOP"),
           ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
           ("TOPPADDING", (0, 0), (-1, -1), 3),
           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    t.setStyle(TableStyle(tst))
    s.append(t)
    s.append(Spacer(1, 6))
    s.append(P(
        "<b>Not included</b> (site specific, checked during survey): shade "
        "from water tanks, parapets, lift rooms, trees or nearby buildings "
        "(far shading) - none assumed here; bifacial gain (mono-facial panels); "
        "export limits set by the DISCOM; snow (not applicable).", "small"))

    s.append(PageBreak())
    # ---------------- Page 6: tilt study ----------------
    s.append(P("5. How tilt and direction change the output", "h1"))
    s.append(P(
        f"The plant was simulated again at every tilt from 0 deg (flat) to "
        f"30 deg, all facing south, with rows spaced so they don't shade each "
        f"other. The site is at {PROJECT['lat']:.1f} deg N, so the highest "
        f"<i>per-kWp</i> output is at a tilt of about "
        f"{ctx['best_tilt']:.0f} deg - but the curve is very flat near the top."))
    s.append(Image(ctx["c_tilt"], width=W, height=W * 2.8 / 7.2))
    base = tilt_df.set_index("Tilt").loc[DESIGN_TILT, "Yield"]
    tdata = [["Tilt (south)", "Units/kWp\n/year", f"vs {DESIGN_TILT:.0f} deg",
              "Row pitch\nm", f"kWp that fit on\n{ctx['roof_area']:,.0f} m2 roof*",
              "Roof output\nunits/yr", f"Roof vs\n{DESIGN_TILT:.0f} deg"]]
    rbase = tilt_df.set_index("Tilt").loc[DESIGN_TILT, "RoofEnergy"]
    for _, r in tilt_df.iterrows():
        tdata.append([f"{r['Tilt']:.0f} deg", f"{r['Yield']:,.0f}",
                      f"{(r['Yield']/base-1)*100:+.1f} %",
                      f"{r['Pitch']:.2f}", f"{r['RoofKWp']:.1f}",
                      f"{r['RoofEnergy']:,.0f}",
                      f"{(r['RoofEnergy']/rbase-1)*100:+.1f} %"])
    tt = grid_table(tdata, [22 * mm, 24 * mm, 22 * mm, 22 * mm, 30 * mm,
                            32 * mm, 28 * mm], font=7.8)
    idx = list(tilt_df["Tilt"]).index(DESIGN_TILT) + 1
    tt.setStyle(TableStyle([("BACKGROUND", (0, idx), (-1, idx),
                             colors.HexColor("#D1FAE5")),
                            ("FONT", (0, idx), (-1, idx), "Helvetica-Bold",
                             7.8)]))
    s.append(tt)
    s.append(P(f"* Per {ctx['roof_area']:,.0f} m2 of usable terrace. Row pitch "
               "keeps rows shadow-free 9 am - 3 pm on 21 December, with at "
               "least a 0.6 m walkway for cleaning. Extra dust loss is "
               "included for flat (x1.6) and 5 deg (x1.25) panels. "
               "Steeper panels cast longer "
               "shadows, so rows must be further apart and fewer panels fit "
               "on the same roof.", "small"))
    tb = tilt_df.set_index("Tilt")
    best = ctx["best_tilt"]
    s.append(P(
        f"<b>What this means:</b> going from {DESIGN_TILT:.0f} deg to "
        f"{best:.0f} deg adds only {(tb.loc[best,'Yield']/base-1)*100:.1f} % "
        f"per kWp, but the same roof then holds "
        f"{(1-tb.loc[best,'RoofKWp']/tb.loc[DESIGN_TILT,'RoofKWp'])*100:.0f} % "
        f"fewer panels, so the roof as a whole produces "
        f"{(1-tb.loc[best,'RoofEnergy']/rbase)*100:.0f} % <b>less</b>. A steeper "
        f"table is also taller, catches more wind (heavier structure, higher "
        f"cost) and is harder to clean.<br/><br/>"
        f"Very low tilts (0-5 deg) squeeze more panels onto a crowded roof, "
        f"but each panel produces {(1-tb.loc[0.0,'Yield']/base)*100:.0f} % "
        f"(flat) to {(1-tb.loc[5.0,'Yield']/base)*100:.0f} % (5 deg) less. "
        f"Below about 10 deg rain does not wash the panels; dust and water "
        f"collect at the bottom edge, causing stains and hot spots, and "
        f"cleaning is needed more often. "
        f"<b>{DESIGN_TILT:.0f}-12 deg is the best balance on a terrace.</b>",
        "callout"))

    s.append(PageBreak())
    s.append(P("5b. Month by month - where tilt gains and loses", "h1"))
    s.append(Image(ctx["c_tiltm"], width=W, height=W * 3.0 / 7.2))
    mbt = ctx["monthly_by_tilt"]
    mdata = [["Month"] + [f"{t} deg\nunits" for t in ctx["tilt_cols"]] +
             [f"{t} deg vs\n{DESIGN_TILT:.0f} deg" for t in ctx["tilt_cols"]
              if t != DESIGN_TILT]]
    for i, mo in enumerate(MONTHS):
        row = [mo] + [f"{mbt[t][i]*1000:,.0f}" for t in ctx["tilt_cols"]]
        row += [f"{(mbt[t][i]/mbt[DESIGN_TILT][i]-1)*100:+.0f} %"
                for t in ctx["tilt_cols"] if t != DESIGN_TILT]
        mdata.append(row)
    row = ["Year"] + [f"{mbt[t].sum()*1000:,.0f}" for t in ctx["tilt_cols"]]
    row += [f"{(mbt[t].sum()/mbt[DESIGN_TILT].sum()-1)*100:+.1f} %"
            for t in ctx["tilt_cols"] if t != DESIGN_TILT]
    mdata.append(row)
    n = len(mdata[0])
    s.append(grid_table(mdata, [14 * mm] + [(W - 14 * mm) / (n - 1)] * (n - 1),
                        bold_last=True, font=7.4))
    s.append(P(f"Same {PNOM_KW:.2f} kWp at every tilt, rows spaced shadow-free.",
               "small"))
    win = [MONTHS.index(m) for m in ("Nov", "Dec", "Jan", "Feb")]
    summ = [MONTHS.index(m) for m in ("Apr", "May", "Jun", "Jul", "Aug")]
    g30 = mbt[30] / mbt[DESIGN_TILT] - 1
    g20 = mbt[20] / mbt[DESIGN_TILT] - 1
    s.append(P(
        f"In winter (Nov-Feb) the sun is low in the south, so steeper panels "
        f"face it better: 20 deg gives up to {g20[win].max()*100:.0f} % and "
        f"30 deg up to {g30[win].max()*100:.0f} % more than "
        f"{DESIGN_TILT:.0f} deg. In summer and monsoon (Apr-Aug) the sun is "
        f"almost overhead at noon and much of the light is diffuse, so steep "
        f"panels produce less (30 deg down to {g30[summ].min()*100:.0f} %). "
        f"Over the year these mostly cancel out, which is why the yearly "
        f"difference is small.", "body"))
    s.append(P("Direction (all at the proposed tilt)", "h2"))
    od = ctx["orient_df"]
    obase = od.iloc[0]["Yield"]
    odata = [["Direction", "Units/kWp/year", "vs due south"]]
    for _, r in od.iterrows():
        odata.append([r["Name"], f"{r['Yield']:,.0f}",
                      f"{(r['Yield']/obase-1)*100:+.1f} %"])
    s.append(grid_table(odata, [80 * mm, 50 * mm, 50 * mm]))
    se = od.set_index("Name").iloc[1]["Yield"] / obase - 1
    s.append(P(
        f"At a low tilt the direction matters little - panels turned 45 deg "
        f"from south lose only {abs(se)*100:.1f} %. Panels are laid square to "
        f"the building for a neat, strong structure, even if the building is "
        f"not exactly facing south. East-West 'tent' layouts produce less per "
        f"kWp but can fit more panels on a small roof.", "body"))

    s.append(PageBreak())
    # ---------------- Page 7: 25 year + P50/P90 ----------------
    s.append(P("6. Long-term output (25 years)", "h1"))
    s.append(P(
        f"Panels slowly lose power with age. The panel warranty allows "
        f"{MODULE['deg_year1']*100:.1f} % in the first year and "
        f"{MODULE['deg_yearly']*100:.1f} % per year after that. "
        "<b>P50</b> is the expected value (50 % chance of more). <b>P90</b> is "
        "a conservative value that production exceeds in 9 years out of 10 - "
        "banks and careful buyers plan on P90."))
    sig = math.sqrt(sum(v ** 2 for v in SIGMA.values()))
    udata = [["Uncertainty", "Value"]] + \
        [[k, f"{v*100:.1f} %"] for k, v in SIGMA.items()] + \
        [["Combined", f"{sig*100:.1f} %"]]
    s.append(grid_table(udata, [70 * mm, 30 * mm], bold_last=True))
    s.append(Spacer(1, 4))
    yd = [["Year", "P50 units", "P90 units", "Units/kWp (P50)", "Year",
           "P50 units", "P90 units", "Units/kWp (P50)"]]
    life = ctx["life"]
    for i in range(13):
        a = life[i]
        b_ = life[i + 13] if i + 13 < len(life) else None
        row = [str(a[0]), f"{a[1]:,.0f}", f"{a[2]:,.0f}", f"{a[1]/PNOM_KW:,.0f}"]
        if b_:
            row += [str(b_[0]), f"{b_[1]:,.0f}", f"{b_[2]:,.0f}",
                    f"{b_[1]/PNOM_KW:,.0f}"]
        else:
            tot50 = sum(x[1] for x in life)
            tot90 = sum(x[2] for x in life)
            row += ["25 yrs", f"{tot50/1e6:,.2f} million",
                    f"{tot90/1e6:,.2f} million", ""]
        yd.append(row)
    s.append(grid_table(yd, [13 * mm, 24 * mm, 24 * mm, 29 * mm, 13 * mm,
                             24 * mm, 24 * mm, 29 * mm], font=7.6))

    s.append(P("7. Assumptions used in this simulation", "h2"))
    adata = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Model", "Hourly, 8,760 h, Perez sky", "Panel heat model",
         "PVsyst, Uc = 29 W/m2K (free air)"],
        ["Temp. coefficient", f"{MODULE['gamma_pmax']*100:.2f} %/C",
         "IAM", "ASHRAE, b0 = 0.05"],
        ["Mismatch", f"{LOSS['mismatch']*100:.1f} %", "LID",
         f"{MODULE['lid']*100:.1f} %"],
        ["DC cable loss", f"{LOSS['dc_ohmic_stc']*100:.1f} % at STC",
         "AC cable loss", f"{LOSS['ac_ohmic_stc']*100:.1f} % at STC"],
        ["Dust", "1-5 % by month, 15-day cleaning", "Unavailability",
         f"{LOSS['unavailability']*100:.1f} %"],
        ["Inverter", f"{INVERTER['eta_nom']*100:.1f} % max efficiency",
         "Ground reflection", f"{ALBEDO:.2f}"],
    ]
    s.append(grid_table(adata, [30 * mm, 60 * mm, 30 * mm, 60 * mm],
                        align_right_from=9))
    s.append(Spacer(1, 6))
    s.append(P(
        "<b>Note:</b> Actual generation will vary with the weather of each "
        "year, grid availability, cleaning frequency and shade from objects "
        "on or near the roof. Figures are estimates, not a guarantee, "
        "unless stated in the contract. Prepared by NRG Technologists.",
        "small"))
    doc.build(s)


# -----------------------------------------------------------------------------
# 7. MAIN
# -----------------------------------------------------------------------------
def main():
    loc, sp, wx = build_weather()

    pitch = pitch_for_tilt(DESIGN_TILT)
    h = simulate(loc, sp, wx, DESIGN_TILT, DESIGN_AZIMUTH, pitch=pitch)
    mt = monthly_table(h)
    rows = loss_chain(h)

    # tilt study (south)
    roof_area = 1000.0                       # m2 of usable terrace
    tilts = [0, 5, 10, 15, 20, 22, 25, 30]
    tilt_rows, monthly_by_tilt = [], {}
    for t in tilts:
        pt = pitch_for_tilt(t)
        ht = simulate(loc, sp, wx, t, 180.0, pitch=pt)
        e = ht["p_grid"].sum() / 1000.0                    # MWh for PNOM
        monthly_by_tilt[t] = ht["p_grid"].resample("MS").sum().values / 1000.0
        # panels per m2 of roof = panels in one table cross-section per
        # metre of row length, divided by the row pitch
        per_m_row = ROWS_PER_TABLE / (MODULE["width_m"] + 0.02)
        kwp_fit = roof_area * per_m_row / pt * MODULE["wp"] / 1000.0
        yld = e * 1000 / PNOM_KW
        tilt_rows.append({"Tilt": float(t), "Yield": yld, "Pitch": pt,
                          "RoofKWp": kwp_fit, "RoofEnergy": yld * kwp_fit})
    tilt_df = pd.DataFrame(tilt_rows)
    best_tilt = float(tilt_df.loc[tilt_df["Yield"].idxmax(), "Tilt"])

    # orientation study at design tilt
    orients = [("Due south (proposed)", 180), ("South-east (135 deg)", 135),
               ("South-west (225 deg)", 225), ("East (90 deg)", 90),
               ("West (270 deg)", 270)]
    od = []
    for name, az in orients:
        ho = simulate(loc, sp, wx, DESIGN_TILT, az, pitch=pitch)
        od.append({"Name": name, "Yield": ho["p_grid"].sum() / PNOM_KW})
    # East-West tent (half each way)
    he = simulate(loc, sp, wx, DESIGN_TILT, 90, rows_shading=False)
    hw = simulate(loc, sp, wx, DESIGN_TILT, 270, rows_shading=False)
    od.append({"Name": "East-West tent (half each way)",
               "Yield": (he["p_grid"].sum() + hw["p_grid"].sum()) / 2 / PNOM_KW})
    orient_df = pd.DataFrame(od)

    # 25-year P50 / P90
    sig = math.sqrt(sum(v ** 2 for v in SIGMA.values()))
    p90 = 1 - 1.2816 * sig
    e1 = mt["E_Grid"].sum() * 1000
    life = []
    for y in range(1, 26):
        f = 1.0 if y == 1 else (1 - MODULE["deg_year1"]) * \
            (1 - MODULE["deg_yearly"]) ** (y - 2)
        life.append((y, e1 * f, e1 * f * p90))

    # charts
    c = lambda n: os.path.join(CHART_DIR, n)
    chart_monthly_energy(mt, c("monthly_energy.png"))
    chart_normalized(h, mt, c("normalized.png"))
    chart_pr(mt, c("pr.png"))
    chart_sunpath(c("sunpath.png"))
    chart_tilt_annual(tilt_df, c("tilt_annual.png"))
    chart_tilt_monthly(monthly_by_tilt, c("tilt_monthly.png"))
    chart_loss_waterfall(rows, c("losses.png"))

    ctx = dict(mt=mt, rows=rows, tilt_df=tilt_df, best_tilt=best_tilt,
               orient_df=orient_df, monthly_by_tilt=monthly_by_tilt,
               tilt_cols=[0, 10, 20, 30], pitch=pitch, p90=p90, life=life,
               roof_area=roof_area,
               c_month=c("monthly_energy.png"), c_norm=c("normalized.png"),
               c_pr=c("pr.png"), c_sun=c("sunpath.png"),
               c_tilt=c("tilt_annual.png"), c_tiltm=c("tilt_monthly.png"),
               c_loss=c("losses.png"))
    pdf = os.path.join(OUT_DIR, f"Sample 100 kWp Vadodara - Generation Report "
                                f"{VERSION}.pdf")
    build_pdf(pdf, ctx)

    # console summary
    pd.set_option("display.width", 160)
    print(mt.round(2))
    for r in rows:
        print(f"{r[0][:60]:60s} {'' if r[3] is None else f'{r[3]*100:+.2f}%':>8}"
              f"  {r[1]:,.1f}")
    print(tilt_df.round(2))
    print(orient_df.round(1))
    print("P90 factor", round(p90, 3), "->", pdf)


if __name__ == "__main__":
    main()
