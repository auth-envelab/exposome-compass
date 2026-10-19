"""Source-native annual observations to labelled 2022–2025 postcode summaries."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from ._util import finite_number, sha256, validate_key
from .errors import CompassError
from .reference import CONCENTRATIONS, new_reference

YEARS=(2022,2023,2024,2025)
REQUIRED=('country_code','postal_code','indicator','year','value','units')


def aggregate_annual(input_csv: str | Path, destination: str | Path) -> dict:
    """Require all four calendar years per pollutant; never fill missing with zero."""
    src=Path(input_csv)
    grouped: dict[tuple[str,str],dict] = {}
    seen: set[tuple[str,str,str,int]]=set()
    audit={'input_rows':0,'nonmissing_rows':0,'incomplete_country_postcode_indicator':0}
    with src.open('r', encoding='utf-8-sig', newline='') as stream:
        r=csv.DictReader(stream)
        if not set(REQUIRED).issubset(r.fieldnames or []):
            raise CompassError('Annual input must contain country_code,postal_code,indicator,year,value,units')
        for line,row in enumerate(r,start=2):
            audit['input_rows']+=1
            country,postcode=validate_key(row['country_code'],row['postal_code'])
            indicator=row['indicator'].strip().lower()
            if indicator not in CONCENTRATIONS or row['units'].strip().lower().replace('µ','u') not in ('ug/m3','µg/m³'.replace('µ','u')):
                raise CompassError(f'Unsupported indicator or units on row {line}; convert to ug/m3 first')
            try:year=int(row['year'])
            except (ValueError,TypeError) as exc:raise CompassError(f'Invalid year on row {line}') from exc
            if year not in YEARS:
                raise CompassError(f'Year {year} is outside the required 2022–2025 reference')
            key=(country,postcode,indicator,year)
            if key in seen:
                raise CompassError(f'Duplicate annual input for {key}; do not silently average duplicates')
            seen.add(key)
            place=grouped.setdefault((country,postcode),{'country_code':country,'postal_code':postcode})
            if row['value'].strip():
                val=finite_number(row['value'],name=f'row {line}')
                if val < 0: raise CompassError(f'Negative concentration on row {line}')
                place.setdefault(indicator,{})[year]=val
                audit['nonmissing_rows']+=1
    if not grouped:
        raise CompassError('Annual file is empty')
    records=[]
    for place in grouped.values():
        result={'country_code':place['country_code'],'postal_code':place['postal_code']}
        for indicator in CONCENTRATIONS:
            vals=place.get(indicator,{})
            if set(vals)==set(YEARS):
                result[indicator]=sum(vals[y] for y in YEARS)/len(YEARS)
                result[f'{indicator}_source_year']='2022-2025'
            elif vals:
                audit['incomplete_country_postcode_indicator']+=1
        records.append(result)
    frame=pd.DataFrame(records)
    return new_reference(frame,destination,metadata=dict(
        source_type='annual_postcode_observations',input_name=src.name,
        input_sha256=sha256(src),baseline_years=list(YEARS),
        metric='unweighted arithmetic average of 4 annual concentrations, when all 4 present',
        units='ug/m3', audit=audit,
        note='Annual-mean validity is not independently verified against the original provider'))
