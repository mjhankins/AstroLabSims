# Open Educational Observatory

Free, browser-based astronomy lab activities built around the real workflow of an
observing run: open the dome, slew to a target, center it on the spectrometer slit,
integrate until the signal-to-noise is good enough, and reduce your own data.

**Live site:** https://mjhankins44.github.io/AstroLabSims/

No installation and no accounts required — the activities run in any modern browser,
online or from a local copy of this repository.

## Activities

| Activity | Status | Level | Time |
|---|---|---|---|
| [Classification of Stellar Spectra](spectral-classification/) | ✅ Available | Intro–advanced | ~1–2 hours |
| Hubble's Law | 🚧 In development | — | — |
| More to come | 🗓 Planned | — | — |

## Repository layout

```
index.html                      Project homepage
spectral-classification/
  index.html                    The complete activity (single self-contained file)
  jacoby_atlas.js               Real spectral standards (see "Data" below)
tools/
  get_jacoby_atlas.py           Regenerates jacoby_atlas.js from the STScI archive
README.md
LICENSE
```

## Running locally

Clone (or download) the repository and open `index.html` in a browser. For strict
browsers that restrict `file://` script loading, serve the folder instead:

```
python3 -m http.server
# then visit http://localhost:8000/
```

Everything works offline — useful for classrooms without reliable internet.

## Data: the Jacoby spectral standards

The spectral-classification activity uses real, flux-calibrated stellar spectra from:

> Jacoby, G. H., Hunter, D. A., & Christian, C. A. 1984, *A Library of Stellar
> Spectra*, ApJS, 56, 257. Data distributed by the Space Telescope Science
> Institute (archive.stsci.edu, reference-atlases collection).

The packaged file `jacoby_atlas.js` is committed to the repository so the live site
serves real data out of the box; it carries a provenance header, and this citation
must be retained in any derivative work. To regenerate it from the source archive:

```
pip install astropy numpy
cd spectral-classification
python3 ../tools/get_jacoby_atlas.py --all-dwarfs
```

(Omit `--all-dwarfs` for a 13-standard subset; the app builds its "simple set"
automatically from the full file, so `--all-dwarfs` is the recommended default.)

If `jacoby_atlas.js` is absent, the activity falls back to self-consistent
synthetic standards and says so in the interface.

## Technical fidelity notes

For instructors who want to know what is and isn't physical:

- **Time & tracking.** UT, Julian Date, and Local Sidereal Time are computed for a
  Kitt Peak–like site. With tracking off, the field drifts west at the true
  sidereal rate — and a star can drift out of the slit mid-integration.
- **Photon counting.** The spectrometer accumulates genuine Poisson-distributed
  counts per channel; S/N grows as √t and count rates scale with stellar V
  magnitude. Noisy student spectra are noisy for the right reasons.
- **Pointing model.** Hot-list slews land 0–0.9′ from the target with a random,
  per-target error that is *repeatable* within a session, as a real telescope
  pointing model would be. Students center targets themselves.
- **Continuum matching.** The Jacoby spectra are real de-reddened
  spectrophotometry; on load, each is rectified by an iterative sigma-clipped
  polynomial continuum fit and re-colored onto the app's model continuum so that
  simulated spectra fit both the simple and full standard ladders. Line profiles
  are untouched. Anyone wanting the original spectrophotometry should use the
  STScI files directly.
- **Field stars.** Stars away from the program list carry randomly assigned
  spectral types drawn from a realistic distribution — a practice (and limitation)
  knowingly inherited from VIREO's own star catalog. Nothing in this simulation is
  a source of research measurements.

## Credit & lineage

These activities are focused on recreating, with realism, the experience of being
an astronomer at an observatory. In pursuing that goal we follow a path opened by
**Project CLEA** (Contemporary Laboratory Experiences in Astronomy, Gettysburg
College) and especially **VIREO — The Virtual Educational Observatory** by Glenn
Snyder and Laurence Marschall, whose design influenced several of our choices.
This project is offered partly as an homage to that work. It was **not** produced
by, and is not affiliated with or endorsed by, Project CLEA, its authors, or
Gettysburg College, and contains none of their code. Reviving these laboratory
experiences is a work in progress that will grow as time allows.

Pedagogical design, feature direction, and classroom testing:
**Matthew Hankins, Arkansas Tech University**. Software written collaboratively with
**Claude** (Anthropic), under the instructor's direction.

## License

MIT — see [LICENSE](LICENSE). Astronomical datasets remain the property of their
original authors; retain the citations above in derivative works.

## Contributing

Bug reports, suggestions, and classroom experience reports are welcome via Issues.
