"""Optional GeoTIFF sample extraction at representative postcode coordinates."""
from __future__ import annotations

import csv
from pathlib import Path

from ._util import finite_number, sha256, validate_key
from .errors import CompassError
from .reference import CONCENTRATIONS


def sample_raster(points_csv: str | Path, raster_file: str | Path, output_csv: str | Path,
                  *, indicator: str, year: int, units: str = 'ug/m3') -> dict:
    """Write an annual long table; point samples are not address-level observations."""
    if indicator not in CONCENTRATIONS or year not in (2022,2023,2024,2025):
        raise CompassError('Raster sampling accepts a named air pollutant and 2022–2025 year')
    if units != 'ug/m3':
        raise CompassError('Convert provider raster concentrations to ug/m3 before sampling')
    try:
        import rasterio
        from rasterio.warp import transform
    except ImportError as exc:
        raise CompassError('Install optional geospatial dependencies with pip install ".[geo]"') from exc
    points_csv, raster_file, output_csv=Path(points_csv),Path(raster_file),Path(output_csv)
    if output_csv.exists():
        raise CompassError('Output CSV already exists; select a versioned path')
    points=[]
    with points_csv.open('r',encoding='utf-8-sig',newline='') as stream:
        r=csv.DictReader(stream)
        if not {'country_code','postal_code','latitude','longitude'}.issubset(r.fieldnames or []):
            raise CompassError('Points CSV requires country_code,postal_code,latitude,longitude')
        seen=set()
        for line,row in enumerate(r,start=2):
            country,code=validate_key(row['country_code'],row['postal_code'])
            if (country,code) in seen:raise CompassError('Duplicate postcode point: '+country+'/'+code)
            seen.add((country,code))
            lat=finite_number(row['latitude'],name='latitude')
            lon=finite_number(row['longitude'],name='longitude')
            if not -90<=lat<=90 or not -180<=lon<=180:
                raise CompassError('Point coordinates are outside geographic bounds')
            points.append((country,code,lon,lat))
    if not points:
        raise CompassError('No points to sample')
    output_csv.parent.mkdir(parents=True,exist_ok=True)
    partial=output_csv.with_suffix(output_csv.suffix+'.incomplete')
    if partial.exists():raise CompassError('Existing incomplete output must be reviewed, not overwritten')
    count=0
    try:
        with rasterio.open(raster_file) as ds:
            if ds.count!=1 or ds.crs is None:
                raise CompassError('Raster requires exactly one band and a declared CRS')
            lon=[x[2] for x in points];lat=[x[3] for x in points]
            if ds.crs.to_epsg()!=4326:
                lon,lat=transform('EPSG:4326',ds.crs,lon,lat)
            coords=list(zip(lon,lat))
            with partial.open('x',encoding='utf-8',newline='') as f:
                writer=csv.writer(f,lineterminator='\n')
                writer.writerow(['country_code','postal_code','indicator','year','value','units'])
                for point,location,sample in zip(points,coords,ds.sample(coords,masked=True)):
                    value=sample[0]
                    if (ds.bounds.left<=location[0]<=ds.bounds.right and
                        ds.bounds.bottom<=location[1]<=ds.bounds.top and
                        not getattr(value,'mask',False)):
                        try:
                            numeric=finite_number(float(value),name=indicator)
                            text=str(numeric) if numeric>=0 else ''
                        except (ValueError,TypeError,CompassError):text=''
                    else:text=''
                    writer.writerow([point[0],point[1],indicator,year,text,units])
                    count+=1
        partial.rename(output_csv)
    except BaseException:
        if partial.exists():partial.unlink()
        raise
    return dict(rows=count,output=str(output_csv),output_sha256=sha256(output_csv),
                source_raster_sha256=sha256(raster_file),points_sha256=sha256(points_csv),
                source_support='raster point samples; provider attribution/licence must be documented')
