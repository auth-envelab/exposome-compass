"""Read and export an explicit postcode-level environmental reference."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from ._util import (create_stage, discard_stage, finite_number, load_json,
                    publish_stage, regular_path, save_json, sha256, validate_key,
                    verify_reference)
from ._version import __version__
from .errors import CompassError

MEASURES = ('pm25', 'no2', 'pm10', 'road_density', 'road_distance', 'tree_cover', 'built_up')
CONCENTRATIONS = ('pm25', 'no2', 'pm10')
GEOGRAPHIC = ('latitude', 'longitude')
META_COLUMNS = ('location_id',) + GEOGRAPHIC
MEASUREMENT_META = tuple(f'{n}_source_year' for n in MEASURES)
# A constrained export schema prevents arbitrary source columns from leaking into results.
REFERENCE_FIELDS = ('country_code', 'postal_code', *META_COLUMNS, *MEASURES,
                    *MEASUREMENT_META, 'eligible', 'air_scenario_score_mean',
                    'top_20pct_probability_necessary', 'top_20pct_probability_possible',
                    'mean_best_rank', 'mean_worst_rank', 'score_epistemic_lower',
                    'score_epistemic_upper', 'top_group_evidence_class',
                    'outer_draws', 'model_label')

# An existing analysis can be imported without copying its complete source schema.
EXISTING_COLUMN_MAP = {
    'location_id': 'location_id',
    'postcode_representative_latitude': 'latitude',
    'postcode_representative_longitude': 'longitude',
    'pm25_value': 'pm25',
    'no2_value': 'no2',
    'pm10_value': 'pm10',
    'road_density_geofabrik_value': 'road_density',
    'road_distance_geofabrik_value': 'road_distance',
    'tree_cover_worldcover2021_value': 'tree_cover',
    'built_up_landcover_worldcover2021_value': 'built_up',
    'pm25_source_year': 'pm25_source_year',
    'no2_source_year': 'no2_source_year',
    'pm10_source_year': 'pm10_source_year',
    'road_density_geofabrik_source_year': 'road_density_source_year',
    'road_distance_geofabrik_source_year': 'road_distance_source_year',
    'tree_cover_worldcover2021_source_year': 'tree_cover_source_year',
    'built_up_landcover_worldcover2021_source_year': 'built_up_source_year',
    'eligible': 'eligible',
    'air_scenario_score_mean': 'air_scenario_score_mean',
    'top_20pct_probability_necessary': 'top_20pct_probability_necessary',
    'top_20pct_probability_possible': 'top_20pct_probability_possible',
    'mean_best_rank': 'mean_best_rank',
    'mean_worst_rank': 'mean_worst_rank',
    'score_epistemic_lower': 'score_epistemic_lower',
    'score_epistemic_upper': 'score_epistemic_upper',
    'top_group_evidence_class': 'top_group_evidence_class',
    'outer_draws': 'outer_draws',
}
REQUIRED_EXISTING = {'country_code', 'postal_code', 'pm25_value', 'no2_value'}


def _extract_row(row: dict[str, str], *, mapping: dict[str, str]) -> dict[str, str]:
    country, postcode = validate_key(row['country_code'], row['postal_code'])
    out = {name: '' for name in REFERENCE_FIELDS}
    out.update(country_code=country, postal_code=postcode)
    for source, target in mapping.items():
        if source in row:
            out[target] = row[source].strip()
    for field in (*MEASURES, *GEOGRAPHIC, 'air_scenario_score_mean',
                  'top_20pct_probability_necessary', 'top_20pct_probability_possible',
                  'mean_best_rank', 'mean_worst_rank', 'score_epistemic_lower',
                  'score_epistemic_upper'):
        if out[field]:
            v = finite_number(out[field], name=field)
            if field in ('tree_cover', 'built_up',
                         'top_20pct_probability_necessary', 'top_20pct_probability_possible'):
                if not 0 <= v <= 1:
                    raise CompassError(f'{field} must be within [0, 1]')
            elif field in (*MEASURES, 'air_scenario_score_mean') and v < 0:
                raise CompassError(f'{field} cannot be negative')
            elif field == 'latitude' and not -90 <= v <= 90:
                raise CompassError('Latitude outside [-90, 90]')
            elif field == 'longitude' and not -180 <= v <= 180:
                raise CompassError('Longitude outside [-180, 180]')
    if out['air_scenario_score_mean'] and float(out['air_scenario_score_mean']) > 100 + 1e-8:
        raise CompassError('Priority score outside [0, 100]')
    if (out['top_20pct_probability_necessary'] and out['top_20pct_probability_possible']
            and float(out['top_20pct_probability_necessary']) > float(out['top_20pct_probability_possible'])):
        raise CompassError('Necessary top-group fraction cannot exceed possible fraction')
    for key in (*MEASUREMENT_META, 'location_id', 'top_group_evidence_class'):
        if out[key] and out[key][0] in '=+@':
            raise CompassError(f'Unsafe CSV text prefix in {key}')
    if out['eligible']:
        value = out['eligible'].lower()
        if value not in ('true', 'false', '1', '0'):
            raise CompassError('Eligible must be a boolean/0/1')
        out['eligible'] = '1' if value in ('true', '1') else '0'
    else:
        out['eligible'] = '1' if all(out[k] for k in ('pm25', 'no2')) else '0'
    return out


def import_reference(source: str | Path, destination: str | Path, *,
                     expected_sha256: str | None = None) -> dict:
    """Project an existing CSV onto an environmental-only, strictly allowed schema.

    The original input is never edited. Unsupported columns are not exported.
    Precomputed scores remain explicitly exploratory and are never recalculated.
    """
    source, destination = regular_path(Path(source), must_exist=True), regular_path(Path(destination))
    source_sha = sha256(source)
    if expected_sha256 is not None and expected_sha256.lower() != source_sha:
        raise CompassError('The input file does not match its expected SHA-256')
    stage = create_stage(destination)
    try:
        counts: dict[str, int] = {}
        count = 0
        seen = set()
        with source.open('r', encoding='utf-8-sig', newline='') as stream, \
             (stage / 'reference.csv').open('w', encoding='utf-8', newline='') as out:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if not REQUIRED_EXISTING.issubset(headers) or len(set(headers)) != len(headers):
                raise CompassError('Expected an existing postcode CSV with pollutant columns')
            writer = csv.DictWriter(out, fieldnames=REFERENCE_FIELDS, lineterminator='\n')
            writer.writeheader()
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise CompassError(f'Malformed input row {count+2}')
                clean = _extract_row(row, mapping=EXISTING_COLUMN_MAP)
                key = (clean['country_code'], clean['postal_code'])
                if key in seen:
                    raise CompassError('Duplicate country/postcode identity in imported source')
                seen.add(key)
                clean['model_label'] = ('exploratory_imported_environmental_preference'
                                        if clean['air_scenario_score_mean'] else '')
                writer.writerow(clean)
                counts[clean['country_code']] = counts.get(clean['country_code'], 0) + 1
                count += 1
        if count == 0:
            raise CompassError('No postcode records in source')
        manifest = dict(format='exposome-compass-environmental-v1',
                        operation='import-existing-reference', package_version=__version__,
                        source_basename=source.name, source_sha256=source_sha,
                        files_sha256={'reference.csv': sha256(stage / 'reference.csv')},
                        postcode_records=count, countries=counts, baseline_years=[2022,2023,2024,2025],
                        source_status='user-supplied external reference; provider origin not authenticated',
                        score_status='imported_exploratory_precomputed; no simulation rerun',
                        postcode_counts_not_population_counts=True)
        save_json(stage / 'reference_manifest.json', manifest)
        publish_stage(stage, destination)
        return manifest
    except BaseException:
        discard_stage(stage)
        raise


def read_reference(directory: str | Path, *, checked: bool = True) -> pd.DataFrame:
    directory = Path(directory)
    if checked:
        verify_reference(directory)
    path = regular_path(directory / 'reference.csv', must_exist=True)
    df = pd.read_csv(path, encoding='utf-8-sig', dtype=str,
                     keep_default_na=False, low_memory=False)
    if (len(df) == 0 or len(df.columns) != len(set(df.columns))
            or not {'country_code', 'postal_code'}.issubset(df)):
        raise CompassError('Invalid postcode reference CSV')
    if df.duplicated(['country_code', 'postal_code']).any():
        raise CompassError('Duplicate country/postcode identity in reference')
    return df


def new_reference(frame: pd.DataFrame, destination: str | Path, *,
                  metadata: dict | None = None) -> dict:
    """Write a prepared clean reference (including validated synthetic examples)."""
    destination = Path(destination)
    stage = create_stage(destination)
    try:
        if not {'country_code', 'postal_code'}.issubset(frame.columns) or frame.empty:
            raise CompassError('Input needs country_code and postal_code')
        seen = set()
        with (stage / 'reference.csv').open('w', encoding='utf-8', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=REFERENCE_FIELDS, lineterminator='\n')
            writer.writeheader()
            for r in frame.fillna('').to_dict(orient='records'):
                clean = _extract_row({k: str(v) for k,v in r.items()},
                                     mapping={key: key for key in REFERENCE_FIELDS if key not in ('country_code','postal_code')})
                key = (clean['country_code'], clean['postal_code'])
                if key in seen:
                    raise CompassError('Duplicate country/postcode identity in input')
                seen.add(key)
                writer.writerow(clean)
        result = dict(format='exposome-compass-environmental-v1',
                      operation='create-reference',package_version=__version__,
                      postcode_records=int(len(frame)),
                      countries={str(k): int(v) for k,v in frame.groupby('country_code').size().items()},
                      postcode_counts_not_population_counts=True,
                      files_sha256={'reference.csv':sha256(stage / 'reference.csv')},
                      source_metadata=metadata or {})
        save_json(stage / 'reference_manifest.json', result)
        publish_stage(stage, destination)
        return result
    except BaseException:
        discard_stage(stage)
        raise
