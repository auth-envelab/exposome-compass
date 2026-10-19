"""Country-qualified postcode lookup and reproducible environmental reports."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import html
import json
from pathlib import Path
import shutil
import tempfile
import uuid

import numpy as np
import pandas as pd

from ._util import (load_json, regular_path, save_json, sha256, validate_key,
                    verify_reference)
from .errors import CompassError
from .reference import MEASURES, read_reference

WHO_ANNUAL_GUIDELINES = {'pm25': 5.0, 'no2': 10.0, 'pm10': 15.0}
MEASURE_LABELS = {'pm25':'PM2.5','no2':'NO2','pm10':'PM10',
                  'road_density':'Road density', 'road_distance':'Distance to mapped roads',
                  'tree_cover':'Tree-cover fraction','built_up':'Built-up land-cover fraction'}
MEASURE_UNITS = {'pm25':'µg/m³','no2':'µg/m³','pm10':'µg/m³',
                 'road_density':'km/km²','road_distance':'m',
                 'tree_cover':'fraction','built_up':'fraction'}
FILES={'case_report.json','case_report.html','postcode_rows.csv','source_manifest.json'}


def _numeric(data: pd.Series) -> pd.Series:
    return pd.to_numeric(data.where(data.ne(''),other=np.nan),errors='coerce')


def _parse(row: dict, key: str) -> float | None:
    raw = row.get(key,'')
    if raw is None or str(raw).strip()=='':return None
    return float(raw)


@dataclass
class PostcodeReport:
    country: str
    postal_code: str
    records: list[dict]
    result: dict
    source_sha256: str

    def write(self, output: str | Path) -> Path:
        output=regular_path(Path(output))
        output.parent.mkdir(parents=True,exist_ok=True)
        if output.is_file():raise CompassError('Output must be a directory')
        if output.exists():self._check_refresh(output)
        stage=Path(tempfile.mkdtemp(prefix=f'.{output.name}-new-',dir=output.parent))
        previous=None
        try:
            save_json(stage/'case_report.json',self.result)
            (stage/'case_report.html').write_text(render_html(self.result),encoding='utf-8')
            with (stage/'postcode_rows.csv').open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(self.records[0]),lineterminator='\n')
                writer.writeheader();writer.writerows(self.records)
            manifest=dict(format='exposome-compass-environmental-case-v1',
                          country_code=self.country,postal_code=self.postal_code,
                          source_reference_sha256=self.source_sha256,
                          files_sha256={name:sha256(stage/name) for name in FILES if name!='source_manifest.json'},
                          output_scientific_status='research_preference_only')
            save_json(stage/'source_manifest.json',manifest)
            # Publish new bytes only after building and fingerprinting every file.
            if output.exists():
                self._check_refresh(output)
                previous=output.parent/f'.{output.name}-previous-{uuid.uuid4().hex}'
                output.rename(previous)
            try:
                stage.rename(output)
            except BaseException:
                if previous is not None and previous.exists() and not output.exists():
                    previous.rename(output)
                raise
            if previous is not None:shutil.rmtree(previous)
            return output
        finally:
            if stage.exists():shutil.rmtree(stage)

    def _check_refresh(self, folder: Path) -> None:
        if not folder.is_dir() or set(p.name for p in folder.iterdir())!=FILES:
            raise CompassError('Existing output has unrelated or missing files; refusing replacement')
        manifest=load_json(folder/'source_manifest.json')
        if (manifest.get('format')!='exposome-compass-environmental-case-v1' or
            manifest.get('country_code')!=self.country or
            manifest.get('postal_code')!=self.postal_code or
            manifest.get('source_reference_sha256')!=self.source_sha256):
            raise CompassError('Existing output belongs to a different case or reference')
        names=FILES-{'source_manifest.json'}
        if set(manifest.get('files_sha256',{}))!=names:
            raise CompassError('Existing case manifest is incomplete')
        for name in names:
            regular_path(folder/name,must_exist=True)
            if sha256(folder/name)!=manifest['files_sha256'][name]:
                raise CompassError('Existing report was modified; refusing overwrite: '+name)


class EnvironmentalReference:
    """Read-only, source-verified reference; any number of country+postcode lookups."""
    def __init__(self, directory: str | Path):
        self.directory=regular_path(Path(directory))

    def lookup(self, country: str, postal_code: str) -> PostcodeReport:
        country,postal_code=validate_key(country,postal_code)
        manifest=verify_reference(self.directory)
        df=read_reference(self.directory,checked=False)
        rows=df.loc[(df['country_code']==country)&(df['postal_code']==postal_code)]
        if rows.empty:
            raise CompassError(f'Postcode {country} {postal_code} is absent from the declared reference')
        records=rows.to_dict(orient='records')
        row=records[0]
        exposure=[]
        percentiles=[]
        for indicator in MEASURES:
            value=_parse(row,indicator)
            exposure.append(dict(indicator=indicator,label=MEASURE_LABELS[indicator],
                                 value=value,unit=MEASURE_UNITS[indicator],
                                 source_year=row.get(f'{indicator}_source_year','')))
            if value is None:continue
            if indicator in df:
                vals=_numeric(df[indicator])
                for label,mask in [('Reference postcodes',np.ones(len(df),dtype=bool)),
                                   ('Same-country postcodes',df['country_code'].eq(country).to_numpy())]:
                    valid=vals.loc[mask].dropna()
                    if len(valid):
                        percentiles.append(dict(indicator=indicator,comparison=label,
                            fraction_at_or_below=float((valid<=value).sum()/len(valid)),
                            compared_postcodes=int(len(valid))))
        score=_parse(row,'air_scenario_score_mean')
        if score is not None and 'air_scenario_score_mean' in df:
            vals=_numeric(df['air_scenario_score_mean'])
            for label,mask in [('Reference postcodes',np.ones(len(df),dtype=bool)),
                               ('Same-country postcodes',df['country_code'].eq(country).to_numpy())]:
                valid=vals.loc[mask].dropna()
                if len(valid):
                    percentiles.append(dict(indicator='priority_score',comparison=label,
                        fraction_at_or_below=float((valid<=score).sum()/len(valid)),
                        compared_postcodes=int(len(valid)),
                        exact_score_ties=int(np.isclose(valid,score,rtol=0,atol=1e-8).sum())))
        guideline={}
        for key,limit in WHO_ANNUAL_GUIDELINES.items():
            v=_parse(row,key)
            guideline[key]=dict(four_year_mean_value=v,who_2021_annual_guideline=limit,
                                above_guideline=None if v is None else bool(v>limit))
        ranking=dict(eligible=row.get('eligible','') in ('1','True','true'),
                     priority_score_0_100=score,
                     top_membership_fraction=_parse(row,'top_20pct_probability_necessary'),
                     possible_top_membership_fraction=_parse(row,'top_20pct_probability_possible'),
                     mean_best_rank=_parse(row,'mean_best_rank'),
                     mean_worst_rank=_parse(row,'mean_worst_rank'),
                     score_lower=_parse(row,'score_epistemic_lower'),
                     score_upper=_parse(row,'score_epistemic_upper'),
                     class_label=row.get('top_group_evidence_class',''),
                     scenario_draws=int(row['outer_draws']) if row.get('outer_draws','').isdigit() else None,
                     model_label=row.get('model_label',''))
        report=dict(country_code=country,postal_code=postal_code,
                    postcode_records=len(records),
                    location=dict(latitude=_parse(row,'latitude'),longitude=_parse(row,'longitude'),
                                  support='postcode reference point; not a dwelling or household'),
                    exposures=exposure,ranking=ranking,percentiles=percentiles,
                    who_descriptive_screen=guideline,
                    provenance=dict(input_reference_sha256=manifest['files_sha256']['reference.csv'],
                                    source_status=manifest.get('source_status',manifest.get('operation')),
                                    reference_postcode_count=len(df),
                                    reference_countries=int(df['country_code'].nunique()),
                                    record_unit='unweighted postcode records, not residents'),
                    limitations=[
                      'This report does not estimate an individual disease probability or attributable cases.',
                      'Preference-weight scenarios are not epidemiologically reviewed effect weights.',
                      'Environmental source years and spatial support must be inspected before interpretation.',
                      'Top-group membership is conditional on the specified scenario draws, not health probability.',
                      'A score at the upper bound may be shared by many postcodes due to clipping.'])
        return PostcodeReport(country,postal_code,records,report,
                              manifest['files_sha256']['reference.csv'])


def render_html(data: dict) -> str:
    e=html.escape
    r=data['ranking']
    lines=["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
           "<meta name='viewport' content='width=device-width, initial-scale=1'>",
           '<title>Exposome Compass | Postcode environmental reference</title>',
           '<style>body{font:16px/1.55 system-ui,Arial,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;color:#183045;background:#f6f9fc}section{background:#fff;padding:20px;margin:16px 0;border:1px solid #d9e3ea;border-radius:12px}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #e4ecf2;text-align:left;padding:8px}small{color:#536579}h1,h2{margin-bottom:8px}</style></head><body>',
           '<h1>Exposome Compass — Postcode research report</h1>',
           f"<section><h2>{e(data['country_code'])} {e(data['postal_code'])}</h2>",
           '<small>Local environmental reference; not individual risk prediction</small>',
           '<h3>Environmental measurements</h3><table><tr><th>Indicator</th><th>Value</th><th>Unit</th><th>Source year</th></tr>']
    for item in data['exposures']:
        value='Missing' if item['value'] is None else f"{item['value']:.4f}"
        lines.append('<tr>'+''.join(f'<td>{e(str(v))}</td>' for v in
             (item['label'],value,item['unit'],item['source_year'] or 'See input provenance'))+'</tr>')
    lines.append('</table><h3>Environmental priority</h3>')
    score='Unscored' if r['priority_score_0_100'] is None else f"{r['priority_score_0_100']:.3f}/100"
    prob='Unavailable' if r['top_membership_fraction'] is None else f"{100*r['top_membership_fraction']:.2f}%"
    lines.append(f'<p><strong>Preference-based score:</strong> {e(score)}<br><strong>Top-group membership:</strong> {e(prob)}<br><strong>Classification:</strong> {e(r["class_label"])}</p>')
    lines.append('<h3>Postcode percentiles</h3><table><tr><th>Indicator</th><th>Population</th><th>Percentile at or below</th><th>Count</th></tr>')
    for v in data['percentiles']:
        lines.append('<tr>'+''.join(f'<td>{e(str(x))}</td>' for x in (
            v['indicator'],v['comparison'],f"{v['fraction_at_or_below']*100:.2f}%",v['compared_postcodes']))+'</tr>')
    lines.append('</table><h3>WHO 2021 air guideline comparisons</h3><table><tr><th>Indicator</th><th>4-year mean</th><th>Guideline</th><th>Above?</th></tr>')
    for key,v in data['who_descriptive_screen'].items():
        lines.append('<tr>'+''.join(f'<td>{e(str(x))}</td>' for x in(
            key,'Missing' if v['four_year_mean_value'] is None else f"{v['four_year_mean_value']:.2f}",
            v['who_2021_annual_guideline'], 'Not available' if v['above_guideline'] is None else ('Yes' if v['above_guideline'] else 'No')) )+'</tr>')
    lines.append('</table><small>Four-year means versus WHO annual guideline values: descriptive only, not annual legal-compliance determination.</small></section>')
    lines.append('<section><h2>Interpretation and limits</h2><ul>')
    for caveat in data['limitations']:
        lines.append(f'<li>{e(caveat)}</li>')
    lines.append('</ul></section></body></html>')
    return '\n'.join(lines)
