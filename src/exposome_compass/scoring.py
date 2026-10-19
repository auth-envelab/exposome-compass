"""Explicit environmental MCDA with conditional preference-sensitivity draws.

Scores and top-group fractions describe analytical preferences among postcodes;
none is a personal probability or a disease-risk estimate.
"""
from __future__ import annotations

import math
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from ._util import (create_stage, discard_stage, load_json, publish_stage,
                    save_json, sha256, verify_reference)
from ._version import __version__
from .errors import CompassError
from .reference import MEASURES, new_reference, read_reference, REFERENCE_FIELDS


def load_scenario(path: str | Path) -> dict:
    obj = load_json(Path(path))
    if obj.get('schema_version') != 1 or obj.get('model_type') != 'environmental_preference':
        raise CompassError('Unknown scenario schema; specify environmental_preference version 1')
    terms = obj.get('criteria')
    if not isinstance(terms, list) or not 1 <= len(terms) <= 12:
        raise CompassError('Declare 1–12 explicit environmental criteria')
    seen: set[str] = set()
    total = 0.0
    for term in terms:
        if not isinstance(term, dict) or set(term) - {'indicator', 'weight', 'direction', 'low_quantile', 'high_quantile'}:
            raise CompassError('Invalid criterion schema')
        key = term.get('indicator')
        if key not in MEASURES or key in seen:
            raise CompassError('Criteria must be distinct supported environmental indicators')
        seen.add(key)
        weight = term.get('weight')
        if type(weight) not in (int,float) or not math.isfinite(weight) or weight < 0:
            raise CompassError('Weights must be explicit, finite, and nonnegative')
        total += weight
        if term.get('direction') not in ('higher', 'lower'):
            raise CompassError('Each criterion must declare adverse direction')
        low, high = term.get('low_quantile'),term.get('high_quantile')
        if (type(low) not in (int,float) or type(high) not in (int,float)
                or not 0 <= low < high <= 1):
            raise CompassError('Each criterion must specify valid quantile bounds')
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-8):
        raise CompassError('Explicit criterion weights must sum to one; no fallback weights')
    top = obj.get('top_fraction')
    if type(top) not in (int,float) or not math.isfinite(top) or not 0 < top <= 1:
        raise CompassError('top_fraction must lie in (0, 1]')
    draws, seed = obj.get('draws'), obj.get('seed')
    if type(draws) is not int or not 1 <= draws <= 100000:
        raise CompassError('draws must be an integer from 1 to 100000')
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise CompassError('seed must be a nonnegative 63-bit integer')
    scenario = obj.get('weight_sensitivity')
    if scenario is not None:
        if len(terms) != 2 or not isinstance(scenario, dict) or set(scenario) != {'half_width'}:
            raise CompassError('The current weight-sensitivity sampler requires two criteria')
        width = scenario['half_width']
        center = terms[0]['weight']
        if (type(width) not in (int,float) or not math.isfinite(width)
                or width < 0 or center - width < 0 or center + width > 1):
            raise CompassError('Sensitivity half-width must yield weights within [0, 1]')
    elif draws != 1:
        raise CompassError('Use draws=1 for fixed weights or explicitly declare weight_sensitivity')
    return obj


def run_scenario(input_reference: str | Path, scenario_path: str | Path,
                 destination: str | Path) -> dict:
    """Run fully global tie-inclusive postcode ranking; no per-chunk ranks.

    Runs in O(N) retained arrays and O(N log N) work per draw; no N×draw matrix.
    The current sampler varies only analyst-declared criterion preference weights.
    """
    input_reference = Path(input_reference)
    source_manifest = verify_reference(input_reference)
    cfg = load_scenario(scenario_path)
    frame = read_reference(input_reference, checked=False)
    terms = cfg['criteria']
    eligible = np.ones(len(frame), dtype=bool)
    numbers: list[np.ndarray] = []
    for term in terms:
        indicator = term['indicator']
        if indicator not in frame:
            raise CompassError(f'Reference is missing scoring indicator: {indicator}')
        raw = frame[indicator]
        value = pd.to_numeric(raw.where(raw.ne(''), other=np.nan), errors='coerce').to_numpy(dtype=float)
        if np.any(~np.isfinite(value) & raw.ne('').to_numpy()):
            raise CompassError(f'Non-finite {indicator} cannot be scored')
        eligible &= np.isfinite(value)
        numbers.append(value)
    if int(eligible.sum()) < 2:
        raise CompassError('Ranking requires at least two jointly complete postcode records')
    transformed: list[np.ndarray] = []
    bounds: dict[str,dict] = {}
    for term,x in zip(terms,numbers):
        qlo = float(np.quantile(x[eligible],term['low_quantile'],method='linear'))
        qhi = float(np.quantile(x[eligible],term['high_quantile'],method='linear'))
        if not qlo < qhi:
            raise CompassError(f'Degenerate quantile bounds for {term["indicator"]}; no arbitrary epsilon')
        val = np.clip((x-qlo)/(qhi-qlo),0,1)
        if term['direction']=='lower':
            val = 1-val
        val[~eligible] = np.nan
        transformed.append(val)
        bounds[term['indicator']] = dict(low=qlo,high=qhi,method='clipped_affine',
                                        low_quantile=term['low_quantile'],
                                        high_quantile=term['high_quantile'],
                                        adverse_direction=term['direction'],
                                        interpretation='empirical reference bounds, not health thresholds')
    n=int(eligible.sum())
    idx=np.flatnonzero(eligible)
    total_scores=np.zeros(len(frame),dtype=float)
    total_scores_sq=np.zeros(len(frame),dtype=float)
    sum_ranks=np.zeros(len(frame),dtype=float)
    top_count=np.zeros(len(frame),dtype=np.int64)
    lowest=np.full(len(frame),np.inf)
    highest=np.full(len(frame),-np.inf)
    rng=np.random.default_rng(cfg['seed'])
    draws=cfg['draws']
    k=math.ceil(cfg['top_fraction'] * n)
    for draw in range(draws):
        weights=[float(t['weight']) for t in terms]
        if cfg.get('weight_sensitivity') is not None:
            width=cfg['weight_sensitivity']['half_width']
            w=float(rng.uniform(weights[0]-width,weights[0]+width)) if width else weights[0]
            weights=[w,1-w]
        score=np.zeros(n,dtype=float)
        for w,arr in zip(weights,transformed):
            score += 100.0*w*arr[idx]
        rounded=np.round(score,8)
        ordered=np.sort(rounded)
        ranks=1+n-np.searchsorted(ordered,rounded,side='right')
        top_count[idx] += (ranks <= k)
        total_scores[idx] += score
        total_scores_sq[idx] += score**2
        sum_ranks[idx] += ranks
        lowest[idx]=np.minimum(lowest[idx],score)
        highest[idx]=np.maximum(highest[idx],score)
    mean=total_scores[idx]/draws
    variance=np.maximum(0.0,total_scores_sq[idx]/draws - mean**2)
    frame['eligible'] = eligible.astype(int).astype(str)
    for col in ('air_scenario_score_mean','top_20pct_probability_necessary',
                'top_20pct_probability_possible','mean_best_rank','mean_worst_rank',
                'score_epistemic_lower','score_epistemic_upper','top_group_evidence_class',
                'outer_draws','model_label'):
        frame[col] = ''
    frame.loc[eligible,'air_scenario_score_mean']=mean.astype(str)
    ratios=top_count[idx] / draws
    frame.loc[eligible,'top_20pct_probability_necessary']=ratios.astype(str)
    frame.loc[eligible,'top_20pct_probability_possible']=ratios.astype(str)
    frame.loc[eligible,'mean_best_rank']=(sum_ranks[idx]/draws).astype(str)
    frame.loc[eligible,'mean_worst_rank']=(sum_ranks[idx]/draws).astype(str)
    # These are exact sampled extrema, not a confidence interval or empirical quantile.
    frame.loc[eligible,'score_epistemic_lower']=lowest[idx].astype(str)
    frame.loc[eligible,'score_epistemic_upper']=highest[idx].astype(str)
    frame.loc[eligible,'top_group_evidence_class'] = np.where(
        top_count[idx]==draws,'TOP_IN_ALL_DRAWS',
        np.where(top_count[idx]==0,'NOT_TOP_ANY_DRAW','TOP_IN_SOME_DRAWS'))
    frame.loc[~eligible,'top_group_evidence_class']='NOT_RANKED_MISSING_DATA'
    frame['outer_draws']=str(draws)
    frame['model_label']='environmental_preference_exploratory'
    dest=Path(destination)
    # Reuse the same public reference contract; never overwrite the frozen input.
    manifest=new_reference(frame,dest,metadata=dict(
        operation='global_exploratory_mcda',source_csv_sha256=source_manifest['files_sha256']['reference.csv'],
        scenario_sha256=sha256(scenario_path),criteria_bounds=bounds,
        top_fraction=cfg['top_fraction'],top_group_count_nominal=k, eligible=n,
        draws=draws,seed=cfg['seed'],
        preference_uncertainty_only=True,
        score_interval_interpretation='minimum/maximum scores observed across scenario draws, not 95% quantiles',
        worst_case_membership_mcse_bound=(0.5/math.sqrt(draws)) if draws>1 else None,
        scientific_weight_review='not performed',
        individual_risk_prediction=False))
    return manifest
