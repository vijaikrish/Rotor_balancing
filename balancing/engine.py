"""
Core numerical engine for the Generalized Influence Coefficient Method
(GICM): N correction planes x M measurement probes x K running speeds.

Model
-----
At a given probe/speed combination, measured synchronous (1x) vibration is
modeled as linear in the correction weights currently installed on the
rotor:

    V = V0 + A @ W

where
    V   : complex vibration vector actually measured (one entry per
          probe/speed "channel"), units consistent with the sensor
          (e.g. um pk-pk or mm/s pk, phase in the vector's argument)
    V0  : complex vibration that would be measured with *no* correction
          weight installed (the "original unbalance response")
    A   : (n_channels x n_planes) complex influence coefficient matrix,
          A[c, p] = d(vibration at channel c) / d(complex weight at plane p)
    W   : (n_planes,) complex correction weight currently installed at
          each plane (magnitude = mass, angle = mass's angular position)

Linearity in W is the standard small-perturbation assumption behind every
influence-coefficient balancing method; it holds well below the first
flexible critical and is API 684's documented basis for the GICM at and
near a rotor's bending criticals, provided trial weights are kept small
enough not to violate it (API 684 guidance: trial weight response should
be a measurable fraction, roughly 20-50%, of the original vibration,
without overstressing the rotor or exceeding trip setpoints).

Determinacy
------------
Per API 684 / Lund & Tonnesen: the system is solvable in the least-squares
sense whenever

    n_channels = n_probes * n_speeds >= n_planes

(Also stated by commercial tools, e.g. DyRobes RotorBal, as the condition
Ns x Nm >= Nb.) Below that, the problem is underdetermined and
`numpy.linalg.lstsq` returns the minimum-norm solution, which this module
flags via `SolveResult.determinacy`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------------------
# Magnitude/phase <-> complex helpers
# ---------------------------------------------------------------------------

def mag_phase_to_complex(magnitude: float, phase_deg: float) -> complex:
    """Convert a (magnitude, phase[deg]) pair to a complex number.

    Phase convention: whatever your vibration analyzer/keyphasor reference
    uses. Must be used CONSISTENTLY for every vector in a given balancing
    job (initial run, trial runs, trim runs, trial/correction weight
    angles) or all results will be wrong. See README for the sign
    convention warning.
    """
    theta = np.deg2rad(phase_deg)
    return complex(magnitude * np.cos(theta), magnitude * np.sin(theta))


def complex_to_mag_phase(value: complex) -> tuple[float, float]:
    """Convert a complex number back to (magnitude, phase[deg] in [0,360))."""
    magnitude = abs(value)
    phase_deg = np.degrees(np.angle(value)) % 360.0
    return float(magnitude), float(phase_deg)


def combine_weights(*weights: complex) -> complex:
    """Vector-sum (complex add) a sequence of weights placed on the same
    plane across multiple balancing rounds, returning the single
    equivalent weight/angle a technician would need to realize (or the
    net of 'what's on the rotor now' for bookkeeping across trim passes).
    """
    total = 0 + 0j
    for w in weights:
        total += w
    return total


# ---------------------------------------------------------------------------
# Influence coefficient matrix construction
# ---------------------------------------------------------------------------

def build_influence_matrix(
    initial_vibration: np.ndarray,
    trial_vibration: np.ndarray,
    trial_weights: np.ndarray,
) -> np.ndarray:
    """Build the (n_channels x n_planes) influence coefficient matrix from
    the standard sequential single-trial-weight procedure:

        1. Measure the baseline (no trial weight) response at every
           probe/speed: `initial_vibration`.
        2. For each plane p (one at a time, removing any previous trial
           weight first), install a trial weight `trial_weights[p]` and
           re-measure the response at every probe/speed:
           `trial_vibration[p]`.

    Parameters
    ----------
    initial_vibration : complex ndarray, shape (n_probes, n_speeds)
        Baseline synchronous vibration vector per probe/speed, no trial
        weight installed.
    trial_vibration : complex ndarray, shape (n_planes, n_probes, n_speeds)
        Vibration with trial weight installed at plane p (others removed),
        for each plane p.
    trial_weights : complex ndarray, shape (n_planes,)
        The trial weight actually installed at each plane
        (mag_phase_to_complex(trial_mass, trial_angle)).

    Returns
    -------
    A : complex ndarray, shape (n_probes * n_speeds, n_planes)
        Influence coefficient matrix, one row per probe/speed channel
        (flattened in (probe, speed) order), one column per plane.
    """
    initial_vibration = np.asarray(initial_vibration, dtype=complex)
    trial_vibration = np.asarray(trial_vibration, dtype=complex)
    trial_weights = np.asarray(trial_weights, dtype=complex)

    n_planes, n_probes, n_speeds = trial_vibration.shape
    if initial_vibration.shape != (n_probes, n_speeds):
        raise ValueError(
            f"initial_vibration shape {initial_vibration.shape} does not "
            f"match (n_probes, n_speeds)=({n_probes}, {n_speeds}) inferred "
            f"from trial_vibration"
        )
    if trial_weights.shape != (n_planes,):
        raise ValueError(
            f"trial_weights shape {trial_weights.shape} must be (n_planes,)"
            f"=({n_planes},)"
        )
    if np.any(np.abs(trial_weights) == 0):
        raise ValueError(
            "A trial weight is zero magnitude; cannot divide by a zero "
            "trial weight to compute an influence coefficient."
        )

    A = np.zeros((n_probes * n_speeds, n_planes), dtype=complex)
    for p in range(n_planes):
        delta = trial_vibration[p] - initial_vibration  # (n_probes, n_speeds)
        alpha = delta / trial_weights[p]
        A[:, p] = alpha.reshape(-1)
    return A


# ---------------------------------------------------------------------------
# Solve for correction weights (least squares, any plane/probe/speed count)
# ---------------------------------------------------------------------------

@dataclass
class SolveResult:
    """Result of a least-squares influence-coefficient solve."""

    correction_weights: np.ndarray  # (n_planes,) complex
    predicted_residual: np.ndarray  # same shape as the vibration array solved against
    rank: int
    singular_values: np.ndarray
    n_channels: int
    n_planes: int
    condition_number: float = field(init=False)
    determinacy: str = field(init=False)

    def __post_init__(self) -> None:
        sv = self.singular_values
        if sv.size and sv.min() > 0:
            self.condition_number = float(sv.max() / sv.min())
        else:
            self.condition_number = float("inf")
        if self.n_channels < self.n_planes:
            self.determinacy = "underdetermined"
        elif self.n_channels == self.n_planes:
            self.determinacy = "exactly determined"
        else:
            self.determinacy = "overdetermined (least squares)"

    def is_ill_conditioned(self, threshold: float = 100.0) -> bool:
        """Flag a numerically/physically weak solve (planes with very
        similar influence on the measured channels, or a near-singular
        trial-weight set). A high condition number means small measurement
        errors can produce large, unreliable correction weights -- treat
        the result with suspicion and consider different/additional trial
        planes or speeds."""
        return self.condition_number > threshold


def solve_correction_weights(
    influence_matrix: np.ndarray,
    measured_vibration: np.ndarray,
    weighting: np.ndarray | None = None,
) -> SolveResult:
    """Solve A @ W = -measured_vibration for the correction weight vector W
    that minimizes the (optionally weighted) sum of squared residual
    vibration, per channel, across every probe and every speed
    simultaneously (the Linear Least Squares approach documented in API
    684 and used by commercial balancing packages for the overdetermined
    multi-plane/multi-speed case).

    This same function is used for BOTH:
      - the initial correction solve (measured_vibration = the baseline,
        no-correction-installed vibration), and
      - each subsequent TRIM pass (measured_vibration = the vibration
        measured with the previous correction already installed) -- no
        new trial weights are required for trim passes, because the
        influence coefficient matrix A is a property of the rotor/support
        system, not of which weight happens to be on it right now. The
        output of a trim pass is an INCREMENT to add (vector sum, see
        `combine_weights`) to whatever is currently installed at each
        plane, not a replacement value.

    Parameters
    ----------
    influence_matrix : complex ndarray, shape (n_channels, n_planes)
        From `build_influence_matrix`.
    measured_vibration : complex ndarray, shape matching the probe/speed
        grid used to build influence_matrix (n_probes, n_speeds), or
        already flattened to (n_channels,).
    weighting : real ndarray, shape (n_channels,), optional
        Per-channel weighting factor (e.g. up-weight probes near a
        critical bearing, or the speed closest to operating speed;
        weighting of 0 excludes a channel). Implements weighted least
        squares by scaling both sides of the system by sqrt(weighting),
        matching the approach used in DyRobes RotorBal and standard
        weighted-least-squares balancing texts.

    Returns
    -------
    SolveResult
    """
    A = np.asarray(influence_matrix, dtype=complex)
    vib = np.asarray(measured_vibration, dtype=complex)
    original_shape = vib.shape
    b = -vib.reshape(-1)

    n_channels, n_planes = A.shape
    if b.shape[0] != n_channels:
        raise ValueError(
            f"measured_vibration has {b.shape[0]} channels but "
            f"influence_matrix expects {n_channels}"
        )

    if weighting is not None:
        w = np.sqrt(np.asarray(weighting, dtype=float))
        if w.shape[0] != n_channels:
            raise ValueError("weighting must have one entry per channel")
        A_eff = A * w[:, None]
        b_eff = b * w
    else:
        A_eff, b_eff = A, b

    W, residuals, rank, singular_values = np.linalg.lstsq(A_eff, b_eff, rcond=None)

    predicted_residual_flat = vib.reshape(-1) + A @ W
    predicted_residual = predicted_residual_flat.reshape(original_shape)

    return SolveResult(
        correction_weights=W,
        predicted_residual=predicted_residual,
        rank=int(rank),
        singular_values=singular_values,
        n_channels=n_channels,
        n_planes=n_planes,
    )


def residual_rms(vibration: np.ndarray, weighting: np.ndarray | None = None) -> float:
    """RMS magnitude of a (possibly multi-channel) vibration array -- a
    convenient scalar for convergence/tolerance checks between trim
    passes."""
    v = np.asarray(vibration, dtype=complex).reshape(-1)
    mags2 = np.abs(v) ** 2
    if weighting is not None:
        w = np.asarray(weighting, dtype=float).reshape(-1)
        return float(np.sqrt(np.sum(mags2 * w) / np.sum(w)))
    return float(np.sqrt(np.mean(mags2)))
