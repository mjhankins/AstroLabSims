#!/usr/bin/env python3
"""
get_jacoby_atlas.py — fetch main-sequence standards from the Jacoby, Hunter &
Christian (1984) spectral library at STScI and package them for the
Open Educational Observatory web app.

Reference: Jacoby, G. H., Hunter, D. A., & Christian, C. A. 1984,
"A Library of Stellar Spectra", ApJS, 56, 257.
Data host: https://archive.stsci.edu/hlsps/reference-atlases/cdbs/grid/jacobi/
Each jc_N.fits contains a BINTABLE with WAVELENGTH (Angstroms) and FLUX (FLAM)
columns, 2799 rows spanning ~3510-7427 A.

Usage:
    pip install astropy numpy          (one time)
    python3 get_jacoby_atlas.py                  # the 13-standard teaching atlas
    python3 get_jacoby_atlas.py --all-dwarfs     # every unique class-V type (~40)

Outputs (current directory):
    jacoby_atlas.js    — place next to open-educational-observatory.html;
                         the app loads it automatically on startup
    jacoby_atlas.json  — same data; importable from the Classify Spectra page
"""

import argparse
import io
import json
import re
import sys
import urllib.request

DEFAULT_BASE = "https://archive.stsci.edu/hlsps/reference-atlases/cdbs/grid/jacobi/"
WL_LO, WL_HI, DWL = 3510.0, 7426.0, 2.0
LETTERS = "OBAFGKM"

# ---------------------------------------------------------------------------
# Full index of the atlas (jc file number -> spectral type), from the
# FILENAME/SPTYPE table distributed with the library at STScI.
# ---------------------------------------------------------------------------
INDEX = {
    1:"O5V",2:"O5.5V",3:"O6.5V",4:"O7V",5:"O7.5V",6:"O8V",7:"O8V",8:"O9V",
    9:"O9V",10:"O9.5V",11:"B0V",12:"B0V",13:"B1.5V",14:"B3V",15:"B4V",
    16:"B4V",17:"B6V",18:"B8V",19:"A1V",20:"A1V",21:"A2V",22:"A2V",23:"A2V",
    24:"A3V",25:"A5V",26:"A6V",27:"A7V",28:"A7V",29:"A8V",30:"A9V",31:"F0V",
    32:"F3V",33:"F4V",34:"F5V",35:"F6V",36:"F6V",37:"F7V",38:"F7V",39:"F7V",
    40:"F8V",41:"F9V",42:"F9V",43:"G0V",44:"G1V",45:"G2V",46:"G3V",47:"G4V",
    48:"G6V",49:"G7V",50:"G9V",51:"G9V",52:"K0V",53:"K4V",54:"K5V",55:"M0V",
    56:"M1V",57:"M5V",58:"F0IV",59:"F3IV",60:"G2IV",61:"G5IV",62:"O6.5III",
    63:"O7.5III",64:"O8.5III",65:"O9.5III",66:"B1III",67:"B2III",68:"B2III",
    69:"B2.5III",70:"B3III",71:"B4III",72:"B4III",73:"B5III",74:"B7III",
    75:"B8III",76:"B9III",77:"A3III",78:"A6III",79:"A8III",80:"F0III",
    81:"F4III",82:"F5III",83:"F6III",84:"F7III",85:"F8III",86:"G0III",
    87:"G0III",88:"G2III",89:"G4III",90:"G5III",91:"G6III",92:"G6III",
    93:"G6III",94:"G7III",95:"G8III",96:"G9III",97:"K0III",98:"K2III",
    99:"K2III",100:"K3III",101:"K4III",102:"K7III",103:"M3III",104:"M4III",
    105:"M5III",106:"B2II",107:"B2II",108:"F5II",109:"G8II",110:"G9II",
    111:"K6II",112:"M3II",113:"M7II",114:"O8I",115:"O8I",116:"B0.5I",
    117:"B0.5I",118:"B1.5I",119:"B2I",120:"B3I",121:"B5I",122:"B7I",
    123:"B8I",124:"B9I",125:"A0I",126:"A0I",127:"A1I",128:"A2I",129:"A3I",
    130:"A4I",131:"A7I",132:"A9I",133:"F0I",134:"F2I",135:"F3I",136:"F4I",
    137:"F5I",138:"F6I",139:"F5I",140:"F8I",141:"G0I",142:"G1I",143:"G2I",
    144:"G3I",145:"G5I",146:"K0I",147:"K1I",148:"K2I",149:"K5I",150:"M1I",
    151:"M1I",152:"M2I",153:"MPF4V",154:"MPF4V",155:"M4.5EV",156:"O5I",
    157:"O6I",158:"O7I",159:"B1I",160:"B1I",161:"B5I",
}

# The 13-rung teaching atlas: every label has an exact match in the library.
TEACHING_SET = {
    "O5V":1, "B0V":11, "B6V":17, "A1V":19, "A5V":25, "F0V":31, "F5V":34,
    "G0V":43, "G6V":48, "K0V":52, "K5V":54, "M0V":55, "M5V":57,
}


def type_to_t(sp):
    """Numeric temperature scale: O0=0 ... M9=69. None for peculiar types."""
    m = re.fullmatch(r"([OBAFGKM])(\d(?:\.\d)?)V", sp)
    if not m:
        return None
    return LETTERS.index(m.group(1)) * 10 + float(m.group(2))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "oeo-atlas-fetch/1.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def read_jc_fits(raw):
    """Return (wavelength, flux) from a jc_N.fits BINTABLE extension."""
    from astropy.io import fits
    import numpy as np
    with fits.open(io.BytesIO(raw)) as hdul:
        for hdu in hdul[1:]:
            data = getattr(hdu, "data", None)
            if data is None:
                continue
            names = [c.upper() for c in data.columns.names]
            if "WAVELENGTH" in names and "FLUX" in names:
                wl = np.asarray(data["WAVELENGTH"], dtype=float).ravel()
                fx = np.asarray(data["FLUX"], dtype=float).ravel()
                order = np.argsort(wl)
                return wl[order], fx[order]
    raise ValueError("no WAVELENGTH/FLUX table found")


def choose_entries(all_dwarfs):
    if not all_dwarfs:
        return [(label, idx) for label, idx in TEACHING_SET.items()]
    # every unique normal class-V type, first occurrence wins
    seen, out = set(), []
    for idx in sorted(INDEX):
        sp = INDEX[idx]
        t = type_to_t(sp)
        if t is None or sp in seen:      # skips peculiars like MPF4V, M4.5EV
            continue
        seen.add(sp)
        out.append((sp, idx))
    out.sort(key=lambda e: type_to_t(e[0]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--all-dwarfs", action="store_true",
                    help="include every unique class-V spectral type (~40 standards) "
                         "instead of the 13-rung teaching atlas")
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help="data URL base (default: STScI reference-atlases archive)")
    args = ap.parse_args()

    try:
        import numpy as np
        from astropy.io import fits  # noqa: F401
    except ImportError:
        sys.exit("This script needs astropy and numpy:  pip install astropy numpy")

    entries = choose_entries(args.all_dwarfs)
    print(f"Building atlas with {len(entries)} class-V standards "
          f"({'full dwarf ladder' if args.all_dwarfs else 'teaching set'})\n")

    grid = np.arange(WL_LO, WL_HI + DWL / 2, DWL)
    out_entries, failures = [], []
    for label, idx in sorted(entries, key=lambda e: type_to_t(e[0])):
        url = f"{args.base}jc_{idx}.fits"
        print(f"  {label:>6}  <-  jc_{idx}.fits ... ", end="", flush=True)
        try:
            wl, fx = read_jc_fits(fetch(url))
        except Exception as e:
            print(f"FAILED ({e})")
            failures.append(label)
            continue
        fx = np.interp(grid, wl, fx)
        fx = np.clip(fx, 0, None)
        peak = float(fx.max())
        if peak > 0:
            fx = fx / peak
        out_entries.append({
            "label": label,
            "star": f"JC_{idx}",
            "type": INDEX[idx],
            "file": f"jc_{idx}.fits",
            "wl0": WL_LO,
            "dwl": DWL,
            "flux": [round(float(v), 4) for v in fx],
        })
        print(f"ok  ({len(wl)} rows, {wl.min():.0f}-{wl.max():.0f} A)")

    if not out_entries:
        sys.exit("\nNo spectra retrieved — check your network connection and the "
                 "base URL, then try again.")
    if failures:
        print(f"\nWARNING: could not retrieve {', '.join(failures)}; "
              "the atlas will simply omit those rungs.")

    payload = {
        "meta": {
            "source": "Jacoby, Hunter & Christian 1984, ApJS 56, 257",
            "host": args.base,
            "note": "Resampled to a uniform 2 Angstrom grid; normalized to peak flux.",
        },
        "entries": out_entries,
    }
    with open("jacoby_atlas.json", "w") as f:
        json.dump(payload, f)
    with open("jacoby_atlas.js", "w") as f:
        f.write("/* Auto-generated by get_jacoby_atlas.py — see meta for provenance */\n")
        f.write("window.JACOBY_ATLAS = ")
        json.dump(payload, f)
        f.write(";\n")

    print(f"\nDone: wrote jacoby_atlas.js and jacoby_atlas.json "
          f"({len(out_entries)} standards).")
    print("Place jacoby_atlas.js in the same folder as the observatory HTML file,")
    print("or import jacoby_atlas.json from the Classify Spectra page.")


if __name__ == "__main__":
    main()
