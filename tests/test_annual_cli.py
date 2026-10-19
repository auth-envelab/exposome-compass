import json
from pathlib import Path
import subprocess
import sys
import os

import pytest

from exposome_compass import aggregate_annual,CompassError,read_reference


def test_annual_full_years_missingness(tmp_path):
    inp=tmp_path/'annual.csv'
    rows=['country_code,postal_code,indicator,year,value,units']
    for code in ('054628','56123'):
        for y in (2022,2023,2024,2025):
            rows.append(f'GR,{code},pm25,{y},{10+y-2022},ug/m3' if code=='054628' or y!=2025
                        else f'GR,{code},pm25,{y},,ug/m3')
    inp.write_text('\n'.join(rows)+'\n')
    aggregate_annual(inp,tmp_path/'ref')
    df=read_reference(tmp_path/'ref')
    assert df.loc[df.postal_code=='054628','pm25'].iloc[0]=='11.5'
    assert df.loc[df.postal_code=='56123','pm25'].iloc[0]==''


def test_annual_duplicate_year_rejected(tmp_path):
    inp=tmp_path/'annual.csv'
    inp.write_text('country_code,postal_code,indicator,year,value,units\nGR,1,pm25,2022,10,ug/m3\nGR,1,pm25,2022,11,ug/m3\n')
    with pytest.raises(CompassError,match='Duplicate'):
        aggregate_annual(inp,tmp_path/'ref')


def test_cli_demo_and_repeat_postcode(tmp_path,monkeypatch):
    from exposome_compass.cli import main
    assert main(['demo-create','--output',str(tmp_path/'demo')])==0
    ref=tmp_path/'demo'/'demo_result'
    assert main(['verify',str(ref)])==0
    args=['postcode','50005','--country','GR','--reference',str(ref)]
    assert main(args)==0
    assert main(args)==0
    assert (ref/'reports'/'GR_50005'/'case_report.html').exists()
