"""
Generalized multi-plane / multi-speed rotor balancing engine.

Implements the Generalized (Least Squares) Influence Coefficient Method
(GICM) used for flexible / high-speed rotor trim balancing, as described in:

- Tessarzik, Badgley & Anderson (1972), "Flexible Rotor Balancing by the
  Exact Point-Speed Influence Coefficient Method", ASME J. Eng. Ind.
- Lund & Tonnesen (1972), "Analysis and Experiments on Multi-Plane
  Balancing of a Flexible Rotor", ASME J. Eng. Ind.
- API Standard 684, "API Standard Paragraphs Rotordynamic Tutorial"
  (2nd ed.), Section on multi-plane/multi-speed balancing and least-squares
  solution of the overdetermined influence-coefficient system.

See balancing.standards for ISO 21940-11 (rigid-rotor balance quality
grades) and ISO 20816-3 (vibration severity zones) helpers.
"""
from .engine import (
    mag_phase_to_complex,
    complex_to_mag_phase,
    combine_weights,
    build_influence_matrix,
    solve_correction_weights,
    SolveResult,
)

__all__ = [
    "mag_phase_to_complex",
    "complex_to_mag_phase",
    "combine_weights",
    "build_influence_matrix",
    "solve_correction_weights",
    "SolveResult",
]
