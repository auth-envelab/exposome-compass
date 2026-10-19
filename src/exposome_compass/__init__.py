"""Exposome Compass: local environmental postcode prioritisation for research."""
from ._version import __version__
from .errors import CompassError
from .reference import import_reference, new_reference, read_reference
from .scoring import load_scenario, run_scenario
from .lookup import EnvironmentalReference, PostcodeReport
from .annual import aggregate_annual

__all__ = ['__version__', 'CompassError', 'import_reference','new_reference',
           'read_reference', 'load_scenario','run_scenario',
           'EnvironmentalReference','PostcodeReport','aggregate_annual']
