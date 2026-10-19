# Reproducibility and publication checks

Record software commit, Python version, dependency environment, selected input/source SHA-256 checksums, actual source product identifiers, years, area geography, missingness, criterion definitions, weights, transformations, sampling method/seed and comparison denominator.

A finished environmental reference is immutable. The `verify` command recalculates SHA-256 for its manifest-listed CSVs; a changed file blocks a query. Postcode-specific reports can be refreshed only when the existing report directory consists exclusively of intact files for the same postcode and reference hash. The original reference file is never replaced by a lookup.

Sampled-weight Monte Carlo scenarios measure numerical sensitivity conditional on the chosen preference distribution. Preserve the scenario JSON, computation environment and reference population when comparing outputs. A new indicator, time period, transform, weight range or ranking universe requires a new versioned output, not silent overwrite of an older result.

The repository intentionally contains only small **synthetic** examples. Users must neither assume realistic measured source values nor confuse a passing regression test with provider authenticity, independent source QA or scientific validation. For public research, publish source-specific provenance and a reproducible reference recipe, respecting data-use licences.
