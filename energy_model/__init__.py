"""Public interface for the energy model package."""

###
# __init__.py is used to mark a directory as a Python package. 
# It can also be used to define what is available at the package level.
# We expose model_run here as the package's "front door".
###

from .model import model_run
from .h2_scenario import make_scenario
from .h2_presets import SCENARIOS, CO2_PRICES
__all__ = ["model_run", "make_scenario", "SCENARIOS", "CO2_PRICES"]