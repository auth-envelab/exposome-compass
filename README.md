# Exposome Compass

**Environmental observations and transparent postcode prioritisation for research.**

Exposome Compass is a local Python library and command-line tool for comparing geographic environmental conditions. It turns user-supplied, source-documented postcode-level observations into interpretable exposure summaries and **exploratory** priority rankings. It can also look up an individual postcode without repeating a completed reference analysis.

The unit of analysis is a **postcode reference record, not a person or household**. It does **not** calculate personal disease probabilities, attributable cases, clinical recommendations, or statutory air-quality compliance.

> **Maturity:** `0.1.0a1` is an early public environmental-only research release. The numerical algorithms are tested on synthetic fixtures, but the library and any user-selected scoring criteria require independent source and scientific review before operational decisions. There is no bundled European reference dataset or automatic source download.

## Features

| Capability | What the library actually provides |
|---|---|
| Postcode query | `exposome-compass postcode 54628 --country GR --reference ...` with HTML, CSV and JSON reports |
| Real-data import | Whitelist-based conversion of existing environmental postcode tables to a portable reference format |
| Annual aggregation | Four-year (2022–2025) concentration means, only when all required years are present |
| Geospatial extraction | Optional sampling of a user-supplied GeoTIFF at postcode representative points |
| Environmental prioritisation | Explicitly configured, non-equal criterion weights and monotone 0–100 transformations |
| Preference sensitivity | A reproducible set of common two-criterion weight draws; top-group membership across the complete reference |
| Transparency | Per-indicator values, source years, completeness, score transformations, global comparisons, checksums and limitations |
| Report refresh | Repeated postcode lookups safely refresh only an intact, matching generated report |

### What is not included

There are no bundled provider datasets, online dashboard, live API, automated health-impact coefficients, causal exposure-response model, population-weighted burden estimates, or validated all-domain European ranking. Contextual measurements are **not scored automatically**. Source availability does not imply that an environmental indicator should receive a particular scientific weight.

## 1. Installation

Python **3.11, 3.12 or 3.13** is supported by the package metadata. Clone the new public repository and create a virtual environment:

**Windows PowerShell**

```powershell
 git clone https://github.com/auth-envelab/exposome-compass.git
 cd exposome-compass
 py -3.13 -m venv .venv
 .\.venv\Scripts\python.exe -m pip install -e ".[geo,test]"
 .\.venv\Scripts\python.exe -m exposome_compass --version
```

**Linux or macOS**

```bash
 git clone https://github.com/auth-envelab/exposome-compass.git
 cd exposome-compass
 python3 -m venv .venv
 . .venv/bin/activate
 python -m pip install -e ".[geo,test]"
 exposome-compass --version
```

`geo` is optional and needed only for local GeoTIFF sampling; `test` is optional for contributors. The core library requires NumPy and pandas. Network access is needed for dependency installation unless packages are already cached. The command is also available as `python -m exposome_compass` and works without adding virtual-environment executables to `PATH`.

## 2. Five-minute demonstration (synthetic data)

```powershell
python -m exposome_compass demo-create --output demo-example
```

This builds a **clearly synthetic** 12-postcode reference, a fully declared example scoring scenario, a sampled-weight analysis and a postcode HTML report. No live environmental data are retrieved.

Open `demo-example/demo_case/case_report.html`. You can also look up the reference again:

```powershell
python -m exposome_compass postcode 50005 --country GR `
    --reference demo-example/demo_result
```

The example's invented values are for software learning only and must never be reported as observed exposures.

## 3. Query a real postcode from prepared results

After preparing or importing a reference, supply the reference directory and a **country-qualified postcode**:

```powershell
python -m exposome_compass postcode 54628 --country GR `
    --reference "E:\Research\environment-reference"
```

It creates `E:\Research\environment-reference\reports\GR_54628\` with:

- `case_report.html`: readable observations, descriptive WHO comparisons, priority and percentile context;
- `case_report.json`: equivalent machine-readable data and warnings;
- `postcode_rows.csv`: original selected *allowed environmental columns*;
- `source_manifest.json`: input/output fingerprints and case identity.

Run the command again and the library **refreshes the same generated report**. If the existing folder contains unexpected or modified files, the operation refuses to overwrite it. The original reference is never modified by the lookup.

To avoid passing `--reference` on every command:

```powershell
$env:EXPOSOME_COMPASS_REFERENCE = "E:\Research\environment-reference"
python -m exposome_compass postcode 54628 --country GR
```

Postal codes are treated as **strings** to preserve leading zeros and country-specific formats. A postcode is not an exact dwelling position; coordinates, where provided, identify the geographic support used in the source.

## 4. Import an existing environmental reference

If you already have an environmental postcode CSV with columns such as `country_code`, `postal_code`, `pm25_value`, `no2_value`, `pm10_value`, `road_density_geofabrik_value`, and optionally precomputed priority fields, you can import it:

```powershell
python -m exposome_compass import-existing `
    "E:\Research\existing_postcode_environment.csv" `
    --output "E:\Research\environment-reference"
```

Optional: add `--expected-sha256 HASH` when you have a trusted input checksum. Import uses an explicit column **allowlist**. Unknown columns are not copied; missing measurements stay missing. Previously computed preference-based scores can be carried into the clean reference **without rerunning them or treating them as verified health effects**.

`reference.csv` and `reference_manifest.json` are generated. The existing raw CSV is left untouched. Avoid committing these potentially huge or third-party-licensed files to GitHub.

## 5. Build 2022–2025 air-pollution summaries

For new data, start with one record per country, postcode, pollutant and year:

```csv
country_code,postal_code,indicator,year,value,units
GR,54628,pm25,2022,18.1,ug/m3
GR,54628,pm25,2023,17.6,ug/m3
GR,54628,pm25,2024,17.0,ug/m3
GR,54628,pm25,2025,17.4,ug/m3
```

These four rows are merely an input-format example, **not measurements** for the named postcode. A real reference needs the corresponding verified original values for the selected postcodes and pollutants. Do not label example values as observed.

To aggregate a complete annual table:

```powershell
python -m exposome_compass aggregate-air annual_concentrations.csv `
    --output "E:\Research\air-reference"
```

The aggregate uses a simple equal-year average of all four annual concentrations. If a year is absent, the aggregate remains **missing**, not zero; duplicate country/postcode/indicator/year records fail validation. Each pollutant must have compatible concentration units `ug/m3`. The command does not itself validate the environmental source model or annual measurement accuracy.

### Optional raster extraction

Once you have a permitted local, single-band annual GeoTIFF and `points.csv` containing `country_code,postal_code,latitude,longitude`, you may sample the raster at those representative points:

```powershell
python -m exposome_compass sample-raster `
    --points points.csv `
    --raster pm25_2022.tif `
    --indicator pm25 --year 2022 `
    --output sampled_pm25_2022.csv
```

Repeat for each relevant annual grid and carefully consolidate the long tables before `aggregate-air` (keep one CSV header). The sampler uses CRS transformation where necessary and preserves missing/out-of-extent cells as blank values; it does not interpolate outside provider coverage. The owner of the data remains responsible for validating raster units, product identity, source support, permissible use and temporal applicability.

Further reference guidance: [Data preparation](docs/data.md).

## 6. Calculate an exploratory environmental priority

Scoring uses **explicit decision weights**. There are no automatically selected epidemiological coefficients or silently equal criteria. Save a `scenario.json` such as:

```json
{
  "schema_version": 1,
  "model_type": "environmental_preference",
  "criteria": [
    {"indicator":"pm25", "weight":0.70, "direction":"higher", "low_quantile":0.05, "high_quantile":0.95},
    {"indicator":"no2",  "weight":0.30, "direction":"higher", "low_quantile":0.05, "high_quantile":0.95}
  ],
  "top_fraction": 0.20,
  "draws": 1024,
  "seed": 20251015,
  "weight_sensitivity": {"half_width": 0.10}
}
```

**The 70/30 split is an illustrative analyst preference**, not an externally approved exposure-health weight. The uniform `half_width` scenario varies PM2.5's weight from 0.60 to 0.80 and sets the NO2 weight to the complement. It represents preference sensitivity **only**, not real exposure measurement error. To compute one deterministic score, omit `weight_sensitivity` and use `draws: 1`.

Run against a prepared input reference:

```powershell
python -m exposome_compass run `
    --reference "E:\Research\air-reference" `
    --scenario scenario.json `
    --output "E:\Research\air-ranking-v1"
```

Then inspect a postcode from the scored result:

```powershell
python -m exposome_compass postcode 54628 --country GR `
    --reference "E:\Research\air-ranking-v1"
```

**Mathematical meaning.** Each criterion is transformed into a 0–100 adversity scale using the declared empirical 5th/95th percentile bounds across the jointly complete postcode reference. Values outside the bounds are clipped; the transformed criteria are averaged with declared weights. Ranking uses the **entire eligible reference in every draw**, not separate chunks. Exact 8-decimal ties share a competition rank, and boundary ties are included in the top group. The resulting top-membership frequency is conditional on the assumed weight distribution, **not a probability of illness**.

Scores at 100 may be shared by many postcodes because of clipping. Do **not** present a 100/100 score or competition rank 1 as proof of unique worst pollution. Country comparisons count postcodes equally, not residents.

Newly computed score lower/upper values are the **observed minimum and maximum over the declared draws**, not 95% uncertainty intervals. Imported references may retain interval columns from their original model; consult that source's methods. The worst-case membership Monte Carlo standard-error bound for independent draws is `0.5/sqrt(draws)`. This controls numerical sampling noise only, not the scientific model's validity.

See [Methods and limitations](docs/methods.md).

## 7. Outputs, integrity and reproducibility

Each prepared reference/result contains:

| File | Meaning |
|---|---|
| `reference.csv` | One row per country + postal code, allowed environmental descriptors and any explicitly computed/imported exploratory priority |
| `reference_manifest.json` | Input identity, output SHA-256, model/data parameters, numbers of records, coverage and scientific-scope notes |
| `reports/CC_POSTCODE/case_report.html` | Human-readable, postcode-specific evidence |
| `reports/CC_POSTCODE/case_report.json` | Machine-readable postcode evidence and limitations |
| `reports/CC_POSTCODE/postcode_rows.csv` | Selected environmental row(s) |
| `reports/CC_POSTCODE/source_manifest.json` | Query-reference SHA-256 and output checksums |

Verify reference integrity:

```powershell
python -m exposome_compass verify "E:\Research\air-ranking-v1"
```

Checksums detect changes **after** a result was created. They do not independently certify a provider, licence, analytical assumptions or scientific approval. Produced folders are immutable for analysis and may be replaced only through a new versioned output; postcode report folders have a separate, guarded refresh mechanism.

## 8. Provenance and valid scientific use

- Public geographical sources include [Eurostat GISCO postal codes](https://ec.europa.eu/eurostat/web/gisco/geodata/administrative-units/postal-codes), the [European Environment Agency](https://www.eea.europa.eu/), and separately licensed national datasets. **No data from those providers are bundled here.**
- A postcode point is not necessarily representative of every residence in its postcode. Multiple postcodes may share coordinates or differ in geographic coverage.
- A concentration is not a measured personal inhaled dose; a road line is not a measured vehicle count; tree-cover fraction is not public green-space accessibility.
- Contextual indicators and older snapshots must retain their true source dates. Do not silently relabel a 2021 land-cover raster as a 2022–2025 measurement.
- The three annual WHO 2021 guideline levels used for descriptive comparisons are 5 µg/m³ (PM2.5), 10 µg/m³ (NO₂), and 15 µg/m³ (PM10). Comparing a four-year *mean* with an annual guideline is **not** a determination that each year exceeded the guideline or violated a legal standard.
- PM10 includes PM2.5 in particle mass. Do not score correlated indicators as independent health burdens without reviewing double counting.
- Never interpret a 0–100 score as disease probability or a top-fifth postcode fraction as the share of residents at risk.
- Sampling uncertainty, exposure uncertainty, decision-weight uncertainty and scientific effect uncertainty are different; this initial algorithm quantifies **only** the stated weight-sensitivity scenario.

## 9. Python API

```python
from exposome_compass import EnvironmentalReference, run_scenario

run_scenario(
    r"E:\Research\air-reference",
    "scenario.json",
    r"E:\Research\air-ranking-v1",
)

reference = EnvironmentalReference(r"E:\Research\air-ranking-v1")
report = reference.lookup("GR", "54628")
print(report.result["exposures"])
print(report.result["ranking"])
report.write(r"E:\Research\postcodes\GR_54628")
```

## 10. Testing, security and contributing

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

The test suite uses synthetic fixtures and explicitly labelled local input examples; it does not assert full European scientific validation. See [Contributing](CONTRIBUTING.md), [Data policy](docs/data.md) and [Reproducibility](docs/reproducibility.md).

Do not commit participant data, exact home addresses, credentials, cached provider data, or substantial processed research tables. Treat public-source redistribution terms individually. This repository is created as a **fresh source tree and fresh Git history**; it does not carry earlier private development history or datasets.

## 11. License, maintenance and citation

The controlling licence is the root [`LICENSE`](LICENSE) file, which must be explicitly selected and included by the organisation before publication. A public repository does not automatically grant reuse rights in the absence of a licence.

When using the software in academic work, cite the version, immutable Git commit, accessed source datasets with their version and dates, and your declared model/scenario. A software archive DOI and a scholarly validation publication should be listed only when actually available.

Maintained as an environmental research software project under **auth-envelab**. Issues and contributions should include software version, Python version, the smallest redistributable reproduction case and nonconfidential logs.
