from pathlib import Path
import csv
import json

import pandas as pd
import pytest

from exposome_compass import (CompassError,EnvironmentalReference,import_reference,
                              new_reference,read_reference)
from exposome_compass._util import sha256,verify_reference


def test_import_existing_allowlist_and_real_fixture_columns(tmp_path):
    inp=tmp_path/'in.csv'
    with inp.open('w',newline='',encoding='utf8') as f:
        w=csv.writer(f)
        w.writerow(['country_code','postal_code','pm25_value','no2_value','pm10_value',
                    'air_scenario_score_mean','top_20pct_probability_necessary',
                    'unrelated_private_notes'])
        w.writerow(['GR','054628','17.52','21.79','29.62','100','1','DO_NOT_COPY'])
        w.writerow(['GR','56123','12.7','14.2','20.3','50','0','DO_NOT_COPY'])
    out=tmp_path/'reference'
    m=import_reference(inp,out,expected_sha256=sha256(inp))
    assert m['postcode_records']==2
    raw=(out/'reference.csv').read_text()
    assert 'DO_NOT_COPY' not in raw and 'unrelated_private_notes' not in raw
    assert read_reference(out).loc[0,'postal_code']=='054628'
    case=EnvironmentalReference(out).lookup('GR','054628')
    assert case.result['ranking']['priority_score_0_100']==100
    assert case.result['exposures'][0]['value']==17.52
    assert case.result['percentiles'][0]['compared_postcodes']==2
    assert len(case.result['percentiles'])>=4
    assert case.result['ranking']['top_membership_fraction']==1
    r=case.write(tmp_path/'case')
    assert '054628' in (r/'case_report.html').read_text()
    assert case.write(r)==r
    assert len(list(r.iterdir()))==4


def test_rejects_modified_previous_case(tmp_path):
    ref=tmp_path/'ref'
    new_reference(pd.DataFrame([dict(country_code='GR',postal_code='54628',pm25=9,no2=8)]),ref)
    report=EnvironmentalReference(ref).lookup('GR','54628')
    dest=report.write(tmp_path/'case')
    (dest/'case_report.html').write_text('User edited report')
    with pytest.raises(CompassError,match='modified'):
        report.write(dest)
    assert (dest/'case_report.html').read_text()=='User edited report'


def test_protect_unrelated_previous_directory(tmp_path):
    r=tmp_path/'ref'
    new_reference(pd.DataFrame([dict(country_code='GR',postal_code='54628')]),r)
    report=EnvironmentalReference(r).lookup('GR','54628')
    p=tmp_path/'case';p.mkdir();(p/'something-else.txt').write_text('keep')
    with pytest.raises(CompassError,match='unrelated'):
        report.write(p)
    assert (p/'something-else.txt').read_text()=='keep'


def test_source_digest_changed(tmp_path):
    inp=tmp_path/'ref'
    new_reference(pd.DataFrame([dict(country_code='GR',postal_code='54628',pm25=9,no2=8)]),inp)
    with (inp/'reference.csv').open('a') as f:f.write('unverified change\n')
    with pytest.raises(CompassError,match='changed or corrupted'):
        verify_reference(inp)


def test_missing_key_is_actionable(tmp_path):
    inp=tmp_path/'ref'
    new_reference(pd.DataFrame([dict(country_code='GR',postal_code='54628',pm25=9,no2=8)]),inp)
    with pytest.raises(CompassError,match='absent'):
        EnvironmentalReference(inp).lookup('GR','56123')


def test_duplicate_rows_rejected_before_publication(tmp_path):
    inp=tmp_path/'ref'
    with pytest.raises(CompassError,match='Duplicate'):
        new_reference(pd.DataFrame([
            dict(country_code='GR',postal_code='54628',pm25=9),
            dict(country_code='GR',postal_code='54628',pm25=8)]),inp)
    assert not inp.exists()


def test_import_sha_block(tmp_path):
    csvp=tmp_path/'src.csv'
    csvp.write_text('country_code,postal_code,pm25_value,no2_value\nGR,54628,4,5\n')
    with pytest.raises(CompassError,match='SHA-256'):
        import_reference(csvp,tmp_path/'out',expected_sha256='0'*64)
