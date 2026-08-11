"""Reusable core of the Hanoi urban noise study.

Scripts in `scripts/` are thin command-line entry points; everything they share
-- paths, parameters, feature construction, the cross-validation protocols and
the physical kernel -- lives here so it is stated once and can be tested.

Install with `pip install -e .` (or `make setup`).
"""

__version__ = "1.0.0"
