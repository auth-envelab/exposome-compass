"""Installed command line for environmental reference assembly and postcode reports."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Sequence

import pandas as pd

from ._version import __version__
from ._util import save_json, verify_reference
from .annual import aggregate_annual
from .errors import CompassError
from .lookup import EnvironmentalReference
from .reference import import_reference, new_reference
from .scoring import run_scenario


def create_demo(output: Path) -> dict:
    """Tiny clearly artificial example for learning and testing; not research data."""
    if output.exists():raise CompassError('Demo destination already exists')
    output.mkdir(parents=True)
    records=[]
    for i in range(12):
        records.append(dict(country_code='GR' if i < 6 else 'ES',
            postal_code=f'{50000+i:05d}',pm25=5+i*.95,no2=7+i*1.3,
            pm10=12+i*1.2,tree_cover=max(0.0,.7-.04*i),
            built_up=min(1.,.15+.05*i),
            latitude=40.5+i*.003,longitude=22.9+i*.003,
            pm25_source_year='synthetic',no2_source_year='synthetic',
            pm10_source_year='synthetic',model_label=''))
    ref=output/'demo_reference'
    new_reference(pd.DataFrame(records),ref,metadata=dict(data_kind='synthetic',
                      warning='All demo values are fabricated for demonstration only'))
    scenario=dict(schema_version=1,model_type='environmental_preference',
        criteria=[dict(indicator='pm25',weight=.7,direction='higher',low_quantile=.05,high_quantile=.95),
                  dict(indicator='no2',weight=.3,direction='higher',low_quantile=.05,high_quantile=.95)],
        top_fraction=.2,draws=32,seed=192837,
        weight_sensitivity=dict(half_width=.1))
    save_json(output/'scenario.json',scenario)
    run=output/'demo_result'
    run_scenario(ref,output/'scenario.json',run)
    case=EnvironmentalReference(run).lookup('GR','50005')
    case.write(output/'demo_case')
    (output/'DEMO_IS_SYNTHETIC.txt').write_text(
        'All locations and values in this demonstration are artificial. Do not use for research claims.\n',encoding='utf-8')
    return dict(demo_root=str(output),reference=str(ref),scenario=str(output/'scenario.json'),
                result=str(run),example_report=str(output/'demo_case'/'case_report.html'))


def main(argv: Sequence[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog='exposome-compass',
        description='Postcode environmental observations, explicit MCDA scenarios and reproducible research reports.')
    p.add_argument('--version',action='version',version=f'%(prog)s {__version__}')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('demo-create',help='Build a small synthetic end-to-end demonstration')
    a.add_argument('--output',required=True,type=Path)
    a=sub.add_parser('import-existing',help='Export only allowed environmental columns from an existing postcode table')
    a.add_argument('input_csv',type=Path)
    a.add_argument('--output',required=True,type=Path)
    a.add_argument('--expected-sha256',help='Optional independently recorded source checksum')
    a=sub.add_parser('aggregate-air',help='Four-year annual concentration means, requiring complete 2022-2025 coverage')
    a.add_argument('input_csv',type=Path)
    a.add_argument('--output',required=True,type=Path)
    a=sub.add_parser('sample-raster',help='Sample a local annual GeoTIFF at supplied postcode points')
    a.add_argument('--points',type=Path,required=True)
    a.add_argument('--raster',type=Path,required=True)
    a.add_argument('--indicator',choices=('pm25','no2','pm10'),required=True)
    a.add_argument('--year',type=int,required=True)
    a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('run',help='Environmental MCDA and top-group weight-sensitivity analysis')
    a.add_argument('--reference',type=Path,required=True)
    a.add_argument('--scenario',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('postcode',help='Report for one country-qualified postcode from a prepared reference')
    a.add_argument('postal_code')
    a.add_argument('--country',required=True)
    a.add_argument('--reference',type=Path,
                   help='Prepared result directory; alternatively set EXPOSOME_COMPASS_REFERENCE')
    a.add_argument('--output',type=Path,
                   help='Override default reference/reports/COUNTRY_POSTCODE directory')
    a=sub.add_parser('verify',help='Check an environmental reference against its file hashes')
    a.add_argument('reference',type=Path)
    args=p.parse_args(argv)
    try:
        if args.command=='demo-create':result=create_demo(args.output)
        elif args.command=='import-existing':
            result=import_reference(args.input_csv,args.output,expected_sha256=args.expected_sha256)
        elif args.command=='aggregate-air':result=aggregate_annual(args.input_csv,args.output)
        elif args.command=='sample-raster':
            from .raster import sample_raster
            result=sample_raster(args.points,args.raster,args.output,
                                 indicator=args.indicator,year=args.year)
        elif args.command=='run':result=run_scenario(args.reference,args.scenario,args.output)
        elif args.command=='postcode':
            directory=args.reference or os.environ.get('EXPOSOME_COMPASS_REFERENCE')
            if directory is None:
                raise CompassError('Provide --reference or set EXPOSOME_COMPASS_REFERENCE to a prepared reference directory')
            case=EnvironmentalReference(directory).lookup(args.country,args.postal_code)
            result_dir=args.output or (Path(directory)/'reports'/f'{case.country}_{case.postal_code}')
            case.write(result_dir)
            result=dict(country_code=case.country,postal_code=case.postal_code,
                        matched_records=len(case.records),
                        case_report_html=str(result_dir/'case_report.html'),
                        case_report_json=str(result_dir/'case_report.json'),
                        environmental_priority_status=case.result['ranking']['model_label'],
                        recomputed_scenario_draws=0)
        elif args.command=='verify':
            result=verify_reference(args.reference)
        else:raise CompassError('Unrecognized command')
        print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
        return 0
    except (CompassError, OSError, ValueError) as exc:
        print(f'BLOCKED [{type(exc).__name__}]: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
