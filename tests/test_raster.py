import csv
from pathlib import Path

import numpy as np
import pytest

from exposome_compass.raster import sample_raster


def test_real_geotiff_sampling_and_out_of_extent(tmp_path):
    rasterio=pytest.importorskip('rasterio')
    from rasterio.transform import from_origin
    raster=tmp_path/'grid.tif'
    with rasterio.open(raster,'w',driver='GTiff',width=2,height=2,count=1,
                       dtype='float32',crs='EPSG:4326',transform=from_origin(22,42,1,1),
                       nodata=-9999) as ds:
        ds.write(np.array([[12,13],[14,-9999]],dtype='float32'),1)
    points=tmp_path/'points.csv'
    points.write_text('country_code,postal_code,latitude,longitude\nGR,54628,41.5,22.5\nGR,56123,60,30\n')
    out=tmp_path/'sample.csv'
    r=sample_raster(points,raster,out,indicator='pm25',year=2022)
    assert r['rows']==2
    with out.open() as f:rows=list(csv.DictReader(f))
    assert rows[0]['value']=='12.0'
    assert rows[1]['value']==''
