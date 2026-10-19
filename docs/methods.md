# Methods and interpretation

## Geographic unit

One country/postcode record, not a resident or participant. All denominators count **eligible postcodes**, and every point is taken from the user's declared geographic reference. Postcode representation is heterogeneous among countries, and equal weighting of postcode records is not population weighting.

## Air source aggregation

`aggregate-air` accepts annual PM2.5, NO2 or PM10 concentration observations for 2022, 2023, 2024 and 2025. It requires all four finite annual values for a four-year average, rejects duplicate country/postcode/indicator/year records, and does not substitute an absent annual value with a typical year or zero.

It is the user's responsibility to ensure that four annual concentration surfaces refer to the same scientific metric and reasonably compatible spatial/temporal support. Point samples are not personal exposure estimates. Source raster identity, permissible use, completeness, corrections and climate/monitoring-model uncertainty need independent validation.

## Criterion transformations

For each criterion `j`, the 5th and 95th percentiles (configurable) are computed across the jointly complete reference at run time. For a higher-is-worse criterion:

```
u_j(x) = clip((x - q05_j) / (q95_j - q05_j), 0, 1)
```

For a lower-is-worse criterion, use `1-u_j(x)`. These are relative ordering scales, **not epidemiological response functions or health thresholds**. Saturation can make many distinct high-pollution postcodes tie at 100.

The score for one declared weight configuration is:

```
S(p) = 100 * sum_j(w_j * u_j(x[p,j]))
```

Weights are nonnegative and explicitly provided with sum 1. There are **no default weights**. No criterion enters a score merely because an environmental indicator is available.

## Preference-sensitivity simulation

For two criteria only, a declared half-width `h` produces a uniformly sampled first weight within `[w1-h, w1+h]`, with the second as `1-w1`. One common weight draw is applied to **all postcodes**. A deterministic random seed and number of draws are recorded. The output top-membership fraction describes the proportion of these analyst-assumption draws for which a postcode enters the top share.

These are not inferred probabilities for unknown environmental exposure errors. The simulation does not estimate personal health outcomes or causal exposure effects. Never present the scenario frequency as the probability that a person develops illness.

## Ranking and ties

Every draw ranks the complete declared eligible reference; splitting the data into chunks **must not** create local top-fifth rankings. Scores are rounded to eight decimals for reproducible near-tie handling. Competition ranks are `1 + number of strictly higher scores`; tied postcodes may have the same rank. Postcodes tied at the top cutoff are included together, so the selected number can exceed the nominal `ceil(fraction × count)`.

For a deterministic run (`draws=1`), the top membership flag is zero or one. For sampled weights, it is the fraction of draws with a top membership. The worst-case standard-error bound of a Bernoulli membership estimator over independent draws is `0.5/sqrt(draws)`; that bound is not a confidence interval or scientific validation of model assumptions.

`score_epistemic_lower` and `score_epistemic_upper` in new scores contain the **lowest and highest calculated score across draws**, not an interpolated quantile or confidence interval. An imported, already scored environmental reference may use different definitions and must retain its source interpretation.

## Quality and missingness

Any postcode lacking a required scoring criterion is retained as unscored. Missing means **unobserved** and must not be interpreted as low pollution. Contextual indicators remain separately displayed. Source years outside 2022–2025 are permitted only as clearly labelled context and never silently become part of the four-year air reference.

## Scientific scope

The resulting score measures a reproducible, explicitly selected *environmental preference index*. It is not an attributable risk, clinical prediction, intervention treatment effect or validated multi-pollutant causal model. Strong environmental-health conclusions require independently reviewed sources, criteria, overlap rules, uncertainties and validation of the specific population of interest.
