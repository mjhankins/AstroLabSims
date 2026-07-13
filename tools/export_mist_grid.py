#!/usr/bin/env python3
"""
export_mist_grid.py — build isochrone_grid.js for the AstroLabSims cluster-photometry activity.

WHAT THIS DOES
  Uses Tim Morton's `isochrones` package (v2.x) to pull the MIST v1.2 (vvcrit=0.4)
  model grid + Bessell UBVRI bolometric corrections, then exports a compact,
  app-ready JavaScript data file (~0.5–1 MB), following the jacoby_atlas.js pattern:

    window.ISO_GRID = {
      meta:    {...citations...},
      fehs:    [-0.5, 0.0, 0.25],
      logAges: [6.80, 6.85, ..., 10.15],          # 0.05 dex steps
      iso:     { "<feh>": { "<logAge>": [[B-V, V, U-B, V-R, V-I, mass], ... xN] } },
      zams:    { "<feh>": [[B-V, V, mass], ...] } # composite zero-age main sequence
    }

  Every isochrone is resampled to exactly N points uniformly in EEP, so the app
  can interpolate between adjacent grid ages point-by-point (keeping the smooth
  0.01-dex slider feel).

HOW TO RUN (one time, on your own machine)
  pip install isochrones
  python export_mist_grid.py
  -> writes isochrone_grid.js next to this script; upload it or commit it to the repo.

NOTES
  * FIRST RUN downloads the MIST grid tarball + BC tables from waps.cfa.harvard.edu
    into ~/.isochrones (several GB of disk, and it takes a while). Later runs are fast.
  * All three [Fe/H] values come from the same tarball — no savings from dropping any.
  * The script prints a self-verification block at the end; please paste that output
    back to Claude along with the file.
"""

import json
import numpy as np

LOG_AGES = np.round(np.arange(6.80, 10.1501, 0.05), 2)
FEHS = [-0.5, 0.0, 0.25]
N_PTS = 110                 # points per isochrone after EEP resampling
KEEP_PHASES = (0, 2, 3)     # MS, subgiant/RGB, core-He burning (drop PMS & AGB/WD)
BANDS = ["U", "B", "V", "R", "I"]

print("Loading MIST interpolator (first run triggers the big download)...")
from isochrones import get_ichrone
mist = get_ichrone("mist", bands=BANDS)

def band_col(df, b):
    for c in (f"{b}_mag", b):
        if c in df.columns:
            return c
    raise KeyError(f"no column for band {b}; columns = {list(df.columns)}")

def one_iso(logage, feh):
    df = mist.isochrone(logage, feh, distance=10.0)   # 10 pc -> absolute magnitudes
    if "phase" in df.columns:
        df = df[df["phase"].isin(KEEP_PHASES)]
    df = df.sort_values("eep")
    if len(df) < 8:
        return None
    U, B, V, R, I = (df[band_col(df, b)].values for b in BANDS)
    mass = df["initial_mass"].values if "initial_mass" in df.columns else df["mass"].values
    eep = df["eep"].values
    # resample to N_PTS uniform in EEP
    e2 = np.linspace(eep[0], eep[-1], N_PTS)
    def rs(a): return np.interp(e2, eep, a)
    U, B, V, R, I, mass = map(rs, (U, B, V, R, I, mass))
    pts = np.column_stack([B - V, V, U - B, V - R, V - I, mass])
    return np.round(pts, 3)

def composite_zams(feh):
    """ZAMS(mass) = the point where each mass bin FIRST appears on the MS,
       scanning grid ages young -> old."""
    bins = np.geomspace(0.15, 25.0, 140)
    got = {}
    for la in LOG_AGES:
        df = mist.isochrone(la, feh, distance=10.0)
        if "phase" in df.columns:
            df = df[df["phase"] == 0]
        if len(df) == 0:
            continue
        m = (df["initial_mass"] if "initial_mass" in df.columns else df["mass"]).values
        BV = (df[band_col(df, "B")] - df[band_col(df, "V")]).values
        V = df[band_col(df, "V")].values
        idx = np.digitize(m, bins)
        for i, k in enumerate(idx):
            if k not in got:
                got[k] = (BV[i], V[i], m[i])
    pts = sorted(got.values(), key=lambda p: p[0])            # blue -> red
    return [[round(a, 3), round(b, 3), round(c, 3)] for a, b, c in pts]

iso, zams = {}, {}
for feh in FEHS:
    key = f"{feh:g}"
    iso[key] = {}
    for la in LOG_AGES:
        pts = one_iso(la, feh)
        if pts is not None:
            iso[key][f"{la:.2f}"] = pts.tolist()
    zams[key] = composite_zams(feh)
    print(f"[Fe/H]={feh:+.2f}: {len(iso[key])} isochrones, ZAMS {len(zams[key])} pts")

out = {
    "meta": {
        "source": "MIST v1.2, v/vcrit=0.4 (Choi et al. 2016, ApJ 823, 102; Dotter 2016, ApJS 222, 8), "
                  "Bessell UBVRI synthetic photometry, exported via the `isochrones` package "
                  "(Morton 2015, ascl:1503.010)",
        "columns_iso": ["B-V", "V(abs)", "U-B", "V-R", "V-I", "initial_mass"],
        "columns_zams": ["B-V", "V(abs)", "initial_mass"],
        "phases_kept": "MS, SGB/RGB, core-He (MIST phase 0,2,3)",
        "n_pts_per_iso": N_PTS,
    },
    "fehs": FEHS,
    "logAges": [float(a) for a in LOG_AGES],
    "iso": iso,
    "zams": zams,
}
js = "window.ISO_GRID=" + json.dumps(out, separators=(",", ":")) + ";\n"
with open("isochrone_grid.js", "w") as f:
    f.write(js)

# ---------------- self-verification ----------------
print("\n================ VERIFICATION (paste this back to Claude) ================")
print(f"file size: {len(js)/1e6:.2f} MB; ages per feh:",
      {k: len(v) for k, v in iso.items()})
g = np.array(iso["0"]["9.60"]) if "9.60" in iso["0"] else None
if g is not None:
    ms = g[g[:, 1] > 2.0]  # rough MS portion
    print(f"logAge 9.60 solar: turnoff ~ bluest MS point B-V={ms[:,0].min():+.3f}"
          f" (expect ~ +0.4 to +0.5)")
z = np.array(zams["0"])
i = np.argmin(np.abs(z[:, 0] - 0.65))
print(f"solar ZAMS at B-V=0.65: M_V={z[i,1]:.2f} (expect ~ 4.7-5.0)")
i = np.argmin(np.abs(z[:, 0] + 0.20))
print(f"solar ZAMS at B-V=-0.20: M_V={z[i,1]:.2f} (expect ~ -1 to -2)")
y = np.array(iso["0"]["7.00"]) if "7.00" in iso["0"] else None
if y is not None:
    print(f"logAge 7.00 solar: {len(y)} pts, brightest M_V={y[:,1].min():.2f} (expect < -4)")
print("==========================================================================")
print("\nWrote isochrone_grid.js — upload it (or commit to the repo) for integration.")
