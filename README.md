# derives-from-tutorial

[![lineage-check](https://github.com/Adeniyikayodee/derives-from-tutorial/actions/workflows/lineage.yml/badge.svg)](https://github.com/Adeniyikayodee/derives-from-tutorial/actions/workflows/lineage.yml)

Companion code for the freeCodeCamp tutorial **How to Detect Hidden Target Leakage in Public Datasets with Python and a Dependency Graph**.

A model can score close to perfect on public data by rediscovering the formula an agency used to build its target. This repository holds the small tool the tutorial builds to catch that: a YAML manifest that records what each public data product was calculated from, and a linter that refuses any covariate sitting on a derivation path to or from your target.

## What is in here

| file | what it does |
|---|---|
| `leak_demo.py` | rebuilds CDC's SVI Theme 1 from its own five input columns at R² = 0.998 |
| `mini-manifest.yaml` | 11 real US data products and the edges between them |
| `mini_lint.py` | the linter: validates the manifest, walks the graph, and returns FAIL, REVIEW, PASS, or UNTRACED |
| `features.txt` | the covariate list the CI workflow checks |
| `.github/workflows/lineage.yml` | runs the linter on every push and pull request |

## Run it

```bash
git clone https://github.com/Adeniyikayodee/derives-from-tutorial.git
cd derives-from-tutorial
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# the leak demo needs the CDC file (about 7 MB)
curl -L -o California.csv https://svi.cdc.gov/Documents/Data/2022/csv/states/California.csv
python3 leak_demo.py

# the linter
python3 mini_lint.py --target FEMA_NRI.risk_score --covariates ACS.EP_POV150 ACS.EP_UNEMP
python3 mini_lint.py --target FEMA_NRI.risk_score --covariates SAT.chirps_rainfall
```

On Windows, run `.venv\Scripts\activate` in place of the `source` line, and use `python` in place of `python3`.

## Exit codes

| exit code | meaning |
|---|---|
| 0 | the check ran and returned PASS, REVIEW, or UNTRACED |
| 1 | the check ran and found a leak |
| 2 | the manifest is broken or the command is malformed |

## Try the CI check

The workflow checks the names in `features.txt` against `FEMA_NRI.risk_score`. With the file as committed, the check passes. Add `ACS.EP_UNEMP` on a new line and push, and the job turns red with exit code 1. Empty the file and push, and the job turns red with exit code 2.

## The full tool

This repository is the teaching version. The full manifest covers 60 products and 75 derivation edges, with evidence notes and a script that reproduces every R² figure from the live CDC file:

- Repository: <https://github.com/Adeniyikayodee/dependency_manifest>
- Archive: [10.5281/zenodo.22274757](https://doi.org/10.5281/zenodo.22274757)

## Licence

CC0. The CDC, Census Bureau, and FEMA data keep their own terms.
