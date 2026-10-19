# Exposome Compass

**Environmental observations and transparent postcode prioritisation for research.**

Exposome Compass is a local Python library and command-line tool for comparing geographic environmental conditions. It turns user-supplied, source-documented postcode-level observations into interpretable exposure summaries and **exploratory** priority rankings. It can also look up an individual postcode without repeating a completed reference analysis.

The unit of analysis is a **postcode reference record, not a person or household**. It does **not** calculate personal disease probabilities, attributable cases, clinical recommendations, or statutory air-quality compliance.

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

## 1. Start here: install and run on your computer

**Prerequisites:** Git, Python **3.11, 3.12 or 3.13**, a terminal, and internet access for initial Python dependency installation. No administrator privileges, Docker, WSL, or environmental dataset are needed to run the demonstration.

Choose your operating system. Each sequence installs the current code into its own virtual environment, runs a complete **synthetic** example, and creates an HTML report. The reference needed for **real** postcode results is a separate input (Section 3).

### Windows (PowerShell) — copy and paste

Open **Windows PowerShell** in a folder where you can create a new directory (for example, Documents):

~~~powershell
git --version
py -3.13 --version

git clone https://github.com/auth-envelab/exposome-compass.git
Set-Location exposome-compass

py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m exposome_compass --version

.\.venv\Scripts\python.exe -m exposome_compass demo-create --output demo-example
Invoke-Item .\demo-example\demo_case\case_report.html
~~~

If you have Python 3.12 or 3.11 instead, replace **both** `py -3.13` commands with `py -3.12` or `py -3.11`. Install a supported Python version from [python.org](https://www.python.org/downloads/) if needed.

**Why the explicit Python path?** Windows often has more than one Python installation. Using `.\.venv\Scripts\python.exe` for **every subsequent Windows command** ensures the library is installed and run with the same interpreter. You do not need to activate the environment or change the PowerShell execution policy. In a new PowerShell session, first navigate back to the cloned `exposome-compass` directory.

**Expected output:** The version command displays `0.1.0a1`, the demo command lists its generated folders, and a browser opens `demo-example\demo_case\case_report.html`.

### Linux or macOS — terminal

~~~bash
git --version
python3 --version

git clone https://github.com/auth-envelab/exposome-compass.git
cd exposome-compass

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m exposome_compass --version
python -m exposome_compass demo-create --output demo-example
~~~

Use a `python3` executable reporting version **3.11–3.13**. The activation line ensures that later `python` commands use the new virtual environment. Activate it again in each new terminal session, or run `.venv/bin/python` directly. Open `demo-example/demo_case/case_report.html` in your browser (for example, `open` on macOS or `xdg-open` on Linux, if available).

### Optional GeoTIFF support and developer tests

The base install above includes postcode CSV import, annual aggregation, scoring and reporting. GeoTIFF sampling requires the optional `geo` dependencies; tests use the optional `test` dependencies.

Windows:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -e ".[geo,test]"
.\.venv\Scripts\python.exe -m pytest -q
~~~

Linux/macOS (activate `.venv` first):

~~~bash
python -m pip install -e ".[geo,test]"
python -m pytest -q
~~~

You can instead install only the geo or test extra. These extras are not required to try the demonstration.

## 2. Explore the synthetic demonstration

The Section 1 example creates **12 invented postcodes** (six Greek and six Spanish), source-labelled inputs, a scoring scenario, a two-indicator preference-sensitivity analysis, and a postcode HTML report. It downloads **no environmental measurements**.

From the cloned repository, verify the generated reference and request a new report for a demo postcode.

Windows PowerShell:

~~~powershell
.\.venv\Scripts\python.exe -m exposome_compass verify .\demo-example\demo_result
.\.venv\Scripts\python.exe -m exposome_compass postcode 50005 --country GR --reference .\demo-example\demo_result
Invoke-Item .\demo-example\demo_result\reports\GR_50005\case_report.html
~~~

Linux/macOS (with `.venv` activated):

~~~bash
python -m exposome_compass verify demo-example/demo_result
python -m exposome_compass postcode 50005 --country GR --reference demo-example/demo_result
~~~

| Generated path | Contents |
|---|---|
| `demo-example/demo_reference/` | Synthetic environmental inputs and manifest |
| `demo-example/scenario.json` | Indicators, explicit weights, seed and sensitivity settings |
| `demo-example/demo_result/` | Scored synthetic reference with integrity manifest |
| `demo-example/demo_case/case_report.html` | Initial demo report |
| `demo-example/demo_result/reports/GR_50005/` | Report created by the additional postcode command |

**Never interpret or cite demo measurements as real-world exposure data.** The `demo-create` command will not overwrite an existing demo directory; select a new `--output` path to run it again.

## 3. Query a real postcode from prepared results

**Real-data prerequisite:** You must already have a prepared reference folder containing `reference.csv` and `reference_manifest.json`, created by an import, aggregation or scoring command below. **The public repository does not bundle the European postcode dataset or download official provider measurements automatically.** Lookup reads your supplied reference; it cannot invent observations for a missing postcode.

All Windows code blocks below assume you are in the cloned repository directory and use the virtual-environment Python. For Linux/macOS, after activating the virtual environment, use `python -m exposome_compass` and bash continuations rather than the Windows executable path.

After preparing or importing a reference, supply the reference directory and a **country-qualified postcode**:

```powershell
.\.venv\Scripts\python.exe -m exposome_compass postcode 54628 --country GR `
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
.\.venv\Scripts\python.exe -m exposome_compass postcode 54628 --country GR
```

Postal codes are treated as **strings** to preserve leading zeros and country-specific formats. A postcode is not an exact dwelling position; coordinates, where provided, identify the geographic support used in the source.

## 4. Import an existing environmental reference

**Fastest real-data route:** Start with your own environmental postcode CSV. Required input columns are `country_code`, `postal_code`, `pm25_value` and `no2_value`; other environmental indicators and precomputed exploratory priority fields are optional. Unknown input columns are not copied into the public reference. The source file itself is not modified.

If you already have an environmental postcode CSV with columns such as `country_code`, `postal_code`, `pm25_value`, `no2_value`, `pm10_value`, `road_density_geofabrik_value`, and optionally precomputed priority fields, you can import it:

```powershell
.\.venv\Scripts\python.exe -m exposome_compass import-existing `
    "E:\Research\existing_postcode_environment.csv" `
    --output "E:\Research\environment-reference"
```

Optional: add `--expected-sha256 HASH` when you have a trusted input checksum. Import uses an explicit column **allowlist**. Unknown columns are not copied; missing measurements stay missing. Previously computed preference-based scores can be carried into the clean reference **without rerunning them or treating them as verified health effects**.

`reference.csv` and `reference_manifest.json` are generated. The existing raw CSV is left untouched. Avoid committing these potentially huge or third-party-licensed files to GitHub.

## 5. Build 2022–2025 air-pollution summaries

**New-data route:** Obtain and document source datasets yourself, including product release, spatial resolution, metric, units, relevant years, permitted use and missingness. For a comparative two-pollutant score you need **at least two postcodes with complete PM2.5 and NO₂**; a single area cannot meaningfully rank itself. The library does not substitute synthetic or imputed values for missing years.

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
.\.venv\Scripts\python.exe -m exposome_compass aggregate-air annual_concentrations.csv `
    --output "E:\Research\air-reference"
```

The aggregate uses a simple equal-year average of all four annual concentrations. If a year is absent, the aggregate remains **missing**, not zero; duplicate country/postcode/indicator/year records fail validation. Each pollutant must have compatible concentration units `ug/m3`. The command does not itself validate the environmental source model or annual measurement accuracy.

### Optional raster extraction

Once you have a permitted local, single-band annual GeoTIFF and `points.csv` containing `country_code,postal_code,latitude,longitude`, you may sample the raster at those representative points:

```powershell
.\.venv\Scripts\python.exe -m exposome_compass sample-raster `
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
.\.venv\Scripts\python.exe -m exposome_compass run `
    --reference "E:\Research\air-reference" `
    --scenario scenario.json `
    --output "E:\Research\air-ranking-v1"
```

Then inspect a postcode from the scored result:

```powershell
.\.venv\Scripts\python.exe -m exposome_compass postcode 54628 --country GR `
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
.\.venv\Scripts\python.exe -m exposome_compass verify "E:\Research\air-ranking-v1"
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

Run tests in the same virtual environment used to install the library. The tests are software fixtures, not independent environmental-science validation.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

The test suite uses synthetic fixtures and explicitly labelled local input examples; it does not assert full European scientific validation. See [Contributing](CONTRIBUTING.md), [Data policy](docs/data.md) and [Reproducibility](docs/reproducibility.md).

Do not commit participant data, exact home addresses, credentials, cached provider data, or substantial processed research tables. Treat public-source redistribution terms individually. This repository is created as a **fresh source tree and fresh Git history**; it does not carry earlier private development history or datasets.

## 11. License, maintenance and citation

This repository is published under the **MIT License**; see the controlling root [`LICENSE`](LICENSE) file. The software licence does **not** automatically grant redistribution rights for third-party environmental datasets.

When using the software in academic work, cite the version, immutable Git commit, accessed source datasets with their version and dates, and your declared model/scenario. A software archive DOI and a scholarly validation publication should be listed only when actually available.

Maintained as an environmental research software project under **auth-envelab**. Issues and contributions should include software version, Python version, the smallest redistributable reproduction case and nonconfidential logs.

## 12. Troubleshooting

| Issue | Resolution |
|---|---|
| Windows says `py` is not recognized or Python is unsupported | Install Python 3.11–3.13 from [python.org](https://www.python.org/downloads/), reopen PowerShell, and use the installed version consistently (for example, `py -3.12`). |
| `exposome-compass` is not recognized, or `python` launches the wrong interpreter on Windows | Run `.\.venv\Scripts\python.exe -m exposome_compass` **from the cloned repository folder**. No PATH or activation changes are needed. |
| `No module named exposome_compass` | Install with the exact virtual-environment interpreter: `.\.venv\Scripts\python.exe -m pip install -e .` (Windows), or activate `.venv` and reinstall on Linux/macOS. |
| `No module named rasterio` while running `sample-raster` | Install the optional geo extra: `.\.venv\Scripts\python.exe -m pip install -e ".[geo]"` on Windows, or `python -m pip install -e ".[geo]"` in an activated Unix environment. |
| `Provide --reference` or postcode not found | Import or create a reference first, point `--reference` to the folder containing `reference.csv` and `reference_manifest.json`, and check that the country-qualified postcode exists in it. |
| An area has no score | All selected criteria must have valid source data. Missing exposure is **not zero**. Ranking requires two or more jointly complete postcodes. |
| Import, scoring or demo reports the output directory already exists | Analysis directories are immutable. Use a **new** `--output` folder. Only a matching, intact **postcode report** directory is eligible for guarded auto-refresh. |
| A postcode report refuses to refresh | Its files were modified or do not match the new case/reference. Preserve the prior directory and supply a new report `--output` path. |
| `git clone` reports that its destination already exists | Reuse the existing checkout or clone into a different folder; do not overwrite other work. |
| Dependency installation fails | Check your Python version, internet connectivity and virtual environment. Optional geo and test dependencies may be installed separately. |

Command-line help on Windows:

~~~powershell
.\.venv\Scripts\python.exe -m exposome_compass --help
.\.venv\Scripts\python.exe -m exposome_compass postcode --help
~~~

When asking for support, provide the command, software version, operating system and a **non-confidential** error log. Do not share personal records, credentials or restricted provider data.
