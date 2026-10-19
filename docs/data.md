# Environmental data preparation and stewardship

The public code **does not redistribute GISCO, EEA or proprietary provider rasters**, raw geographic references, or large derived tables. Supply files lawfully obtained and licensed for your use. Store inputs and outputs outside your repository working tree.

## Suggested external sources

- GISCO geographic postcode reference and available location/representative-point metadata: https://ec.europa.eu/eurostat/web/gisco/geodata/administrative-units/postal-codes
- EEA air data products and release notices: https://www.eea.europa.eu/
- User-approved local sources for road geometry, vegetation, environmental noise and other context, retaining snapshot year, units, spatial support and licence.

The source provenance, release version, retrieval date, modelled-versus-measured status, unit conversion, raster pixel size, geographic support, and data licence should be documented *before* creating a reference. A SHA-256 fingerprint checks byte integrity but does not independently authenticate a provider.

## Supported common input columns

`reference.csv` always begins with `country_code`, `postal_code`, and optional `location_id`, `latitude`, `longitude`. The current environmental measurements are `pm25`, `no2`, `pm10` in µg/m³; `road_density` in km/km²; `road_distance` in metres; `tree_cover` and `built_up` fractions between zero and one. Each measurement has an optional `*_source_year` string.

The scoring pipeline can select declared criteria from this set, although scientific appropriateness and overlap review are external tasks. PM10 and PM2.5 must not be treated as independently additive physical masses without adjusting the intended model.

## Representing missing and older inputs

An empty numeric cell means no compatible value is available. Do not put 0 or a typical country value in a missing cell. Mark land-cover and road snapshots with their actual years rather than the air baseline. Document any coordinate reuse, coverage gaps and disagreements among administrative sources.

## Postcode and person separation

Data inputs contain environmental geography only. Do not use this system to attach raw participant records, household locations or confidential addresses. Its lookup returns **area-level** observations.

## Notes on scale

The package can read countrywide or Europewide reference CSVs, but memory/disk/time should be measured on the intended host. The NumPy score path keeps O(number of postcodes) arrays and performs a full-reference sort for each sensitivity draw. A national experiment is an appropriate first validation before attempting hundreds of thousands of areas and thousands of draws.
