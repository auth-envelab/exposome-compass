import json
from pathlib import Path
import pandas as pd
import pytest

from exposome_compass import (new_reference,run_scenario,EnvironmentalReference,CompassError)
from exposome_compass.scoring import load_scenario


def _scenario(tmp_path,*,draws=32,weight_half_width=.1):
    p=tmp_path/'scenario.json'
    q={'schema_version':1,'model_type':'environmental_preference',
       'criteria':[dict(indicator='pm25',weight=.7,direction='higher',low_quantile=.05,high_quantile=.95),
                   dict(indicator='no2',weight=.3,direction='higher',low_quantile=.05,high_quantile=.95)],
       'top_fraction':.25,'draws':draws,'seed':104,
       'weight_sensitivity':{'half_width':weight_half_width}}
    p.write_text(json.dumps(q)); return p


def test_ties_share_rank_and_missing_is_retained(tmp_path):
    inp=tmp_path/'ref'
    new_reference(pd.DataFrame([
       dict(country_code='GR',postal_code='10001',pm25=1,no2=2),
       dict(country_code='GR',postal_code='10002',pm25=5,no2=6),
       dict(country_code='GR',postal_code='10003',pm25=10,no2=11),
       dict(country_code='GR',postal_code='10004',pm25=10,no2=11),
       dict(country_code='GR',postal_code='10005',pm25=2,no2='')]),inp)
    result=tmp_path/'result'
    m=run_scenario(inp,_scenario(tmp_path),result)
    assert m['source_metadata']['eligible']==4
    a=EnvironmentalReference(result).lookup('GR','10003').result
    b=EnvironmentalReference(result).lookup('GR','10004').result
    assert a['ranking']['priority_score_0_100']==100
    assert a['ranking']['mean_best_rank']==1
    assert a['ranking']['top_membership_fraction']==1
    assert b['ranking']['mean_best_rank']==1
    missing=EnvironmentalReference(result).lookup('GR','10005').result
    assert missing['ranking']['eligible'] is False
    assert missing['ranking']['priority_score_0_100'] is None


def test_results_are_deterministic(tmp_path):
    inp=tmp_path/'ref'
    new_reference(pd.DataFrame([
       dict(country_code='GR',postal_code=f'{i:05d}',pm25=i,no2=40-i)
       for i in range(1,20)]),inp)
    s=_scenario(tmp_path)
    run_scenario(inp,s,tmp_path/'one')
    run_scenario(inp,s,tmp_path/'two')
    assert (tmp_path/'one'/'reference.csv').read_bytes()==(tmp_path/'two'/'reference.csv').read_bytes()


def test_weights_must_be_explicit_and_sum_one(tmp_path):
    p=_scenario(tmp_path)
    obj=json.loads(p.read_text())
    del obj['criteria'][0]['weight']
    p.write_text(json.dumps(obj))
    with pytest.raises(CompassError,match='Weights'):
        load_scenario(p)


def test_impossible_sensitivity_is_rejected(tmp_path):
    p=_scenario(tmp_path,weight_half_width=.9)
    with pytest.raises(CompassError,match='half-width'):
        load_scenario(p)


def test_insufficient_complete_postcodes(tmp_path):
    inp=tmp_path/'ref'
    new_reference(pd.DataFrame([
        dict(country_code='GR',postal_code='10001',pm25=4,no2=6),
        dict(country_code='GR',postal_code='10002',pm25=4,no2='')]),inp)
    with pytest.raises(CompassError,match='two jointly complete'):
        run_scenario(inp,_scenario(tmp_path),tmp_path/'result')
