"""
Correctness tests for the generalized influence-coefficient balancing
engine, including a hand-checkable single-plane regression test (matches
the worked example already shipped in Rotor_Balancing.py's Help button),
an exactly-determined 2-plane/1-speed case, an overdetermined
2-plane/2-speed/2-probe case, and a multi-pass trim-balancing simulation
with injected correction-weight realization error (you can never install
*exactly* the computed correction weight/angle in practice -- a trim pass
must still converge despite that).
"""
import numpy as np
import pytest

from balancing.engine import (
    mag_phase_to_complex,
    complex_to_mag_phase,
    combine_weights,
    build_influence_matrix,
    solve_correction_weights,
    residual_rms,
)
from balancing.standards import (
    e_per_iso21940_11,
    u_per_iso21940_11,
    allocate_two_plane_lever_rule,
    classify_vibration_zone,
    nearest_g_grade,
    flexible_modal_unbalance_limits,
    u_per_api_617_684_si,
    u_per_api_oz_in,
)


def test_mag_phase_roundtrip():
    for mag, phase in [(5.6, 135), (3.3, 238), (74, 315), (0.001, 0), (12, 359.9)]:
        c = mag_phase_to_complex(mag, phase)
        m2, p2 = complex_to_mag_phase(c)
        assert m2 == pytest.approx(mag, abs=1e-9)
        # phase can wrap at 0/360
        assert (p2 == pytest.approx(phase % 360, abs=1e-6))


def test_single_plane_matches_existing_worked_example():
    """Reproduce the influence-coefficient arithmetic by hand, matching
    the exact method already implemented in Rotor_Balancing.py's
    sp_calculate(), using the Help button's example numbers:
    initial run 5.6 mm/s @ 135 deg, trial run 3.3 mm/s @ 238 deg,
    trial weight 74 g @ 315 deg. This proves the generalized engine's
    1-plane/1-probe/1-speed special case agrees with the single-plane
    tool already shipped and in field use.
    """
    ini = mag_phase_to_complex(5.6, 135)
    trial_run = mag_phase_to_complex(3.3, 238)
    tw = mag_phase_to_complex(74, 315)

    # Reference calculation copied from Rotor_Balancing.py sp_calculate()
    t_com = trial_run - ini
    tma = abs(t_com)
    tph = np.degrees(np.angle(t_com)) % 360
    ifc_m = 74 / tma
    ifc_p = (315 - tph) % 360
    ifc_com = mag_phase_to_complex(ifc_m, ifc_p)
    hs_com = ini * ifc_com
    cwm = abs(hs_com)
    cwp = (np.degrees(np.angle(hs_com)) + 180) % 360
    reference_correction = mag_phase_to_complex(cwm, cwp)

    # Generalized engine, 1 plane / 1 probe / 1 speed
    initial_vibration = np.array([[ini]])        # (n_probes=1, n_speeds=1)
    trial_vibration = np.array([[[trial_run]]])  # (n_planes=1, 1, 1)
    trial_weights = np.array([tw])
    A = build_influence_matrix(initial_vibration, trial_vibration, trial_weights)
    result = solve_correction_weights(A, initial_vibration)

    engine_correction = result.correction_weights[0]
    assert abs(engine_correction - reference_correction) < 1e-6
    # Predicted residual after applying the correction should be ~0
    assert abs(result.predicted_residual[0, 0]) < 1e-9


def test_two_plane_exactly_determined_recovers_zero_residual():
    """Synthetic 2-plane / 1-speed / 2-probe case with a known influence
    matrix: build fake measured data from a chosen 'true' A matrix and
    unbalance, solve, and check the solver recovers a correction that
    drives the predicted residual to ~0 (exact system, no noise)."""
    rng = np.random.default_rng(42)
    n_planes, n_probes, n_speeds = 2, 2, 1

    true_A = (rng.normal(size=(n_probes * n_speeds, n_planes))
              + 1j * rng.normal(size=(n_probes * n_speeds, n_planes)))
    true_V0 = (rng.normal(size=(n_probes, n_speeds))
               + 1j * rng.normal(size=(n_probes, n_speeds)))

    trial_weights = np.array([mag_phase_to_complex(50, 0), mag_phase_to_complex(50, 90)])

    # Build trial_vibration[p] = V0 + true_A[:,p] * trial_weight[p] (plane p alone)
    trial_vibration = np.zeros((n_planes, n_probes, n_speeds), dtype=complex)
    for p in range(n_planes):
        col = true_A[:, p].reshape(n_probes, n_speeds)
        trial_vibration[p] = true_V0 + col * trial_weights[p]

    A = build_influence_matrix(true_V0, trial_vibration, trial_weights)
    np.testing.assert_allclose(A, true_A, atol=1e-10)

    result = solve_correction_weights(A, true_V0)
    assert result.determinacy == "exactly determined"
    assert np.max(np.abs(result.predicted_residual)) < 1e-8


def test_overdetermined_two_speed_two_probe_least_squares():
    """2 planes, 2 probes, 2 speeds -> 4 channels, 2 planes: overdetermined.
    A random 4-channel vibration vector is generically NOT reachable by
    only 2 correction planes (4 equations, 2 unknowns), so this test
    constructs the baseline vibration as the response to a hidden "true"
    unbalance that IS expressible through the same influence matrix
    (true_V0 = -true_A @ w_true), which is the physically meaningful
    noise-free case: an unbalance fully correctable by these 2 planes.
    The least-squares solve must then recover w_true and drive the
    predicted residual to ~0."""
    rng = np.random.default_rng(7)
    n_planes, n_probes, n_speeds = 2, 2, 2
    n_channels = n_probes * n_speeds

    true_A = (rng.normal(size=(n_channels, n_planes))
              + 1j * rng.normal(size=(n_channels, n_planes)))
    w_true_unbalance = (rng.normal(size=n_planes) + 1j * rng.normal(size=n_planes))
    true_V0 = (-true_A @ w_true_unbalance).reshape(n_probes, n_speeds)
    trial_weights = np.array([mag_phase_to_complex(80, 10), mag_phase_to_complex(80, 170)])

    trial_vibration = np.zeros((n_planes, n_probes, n_speeds), dtype=complex)
    for p in range(n_planes):
        col = true_A[:, p].reshape(n_probes, n_speeds)
        trial_vibration[p] = true_V0 + col * trial_weights[p]

    A = build_influence_matrix(true_V0, trial_vibration, trial_weights)
    result = solve_correction_weights(A, true_V0)
    assert result.determinacy == "overdetermined (least squares)"
    assert np.max(np.abs(result.predicted_residual)) < 1e-8
    np.testing.assert_allclose(result.correction_weights, w_true_unbalance, atol=1e-8)


def test_underdetermined_flagged():
    """1 probe, 1 speed (1 channel) but 2 planes -> underdetermined; the
    engine must still return a (minimum-norm) answer but flag it."""
    n_planes, n_probes, n_speeds = 2, 1, 1
    A = np.array([[1 + 0j, 1j]])  # 1 channel, 2 planes
    vib = np.array([[2 + 1j]])
    result = solve_correction_weights(A, vib)
    assert result.determinacy == "underdetermined"


def test_trim_pass_converges_despite_realization_error():
    """Simulate a real-world trim-balancing sequence: the computed
    correction weight can never be installed exactly (discrete trim
    weights, mounting tolerance), yet iterating with the SAME influence
    matrix (no new trial weights) must still converge the residual
    vibration toward zero within a few passes -- this is exactly the
    workflow requested: compute correction, apply it (imperfectly),
    remeasure, compute the next correction from the new measurement."""
    rng = np.random.default_rng(3)
    n_planes, n_probes, n_speeds = 2, 2, 2
    n_channels = n_probes * n_speeds

    true_A = (rng.normal(size=(n_channels, n_planes))
              + 1j * rng.normal(size=(n_channels, n_planes)))
    w_true_unbalance = (rng.normal(size=n_planes) * 3 + 1j * rng.normal(size=n_planes) * 3)
    true_V0 = (-true_A @ w_true_unbalance).reshape(n_probes, n_speeds)
    trial_weights = np.array([mag_phase_to_complex(80, 10), mag_phase_to_complex(80, 170)])

    trial_vibration = np.zeros((n_planes, n_probes, n_speeds), dtype=complex)
    for p in range(n_planes):
        col = true_A[:, p].reshape(n_probes, n_speeds)
        trial_vibration[p] = true_V0 + col * trial_weights[p]

    A = build_influence_matrix(true_V0, trial_vibration, trial_weights)

    def true_vibration_for_installed_weight(W_installed):
        flat = true_V0.reshape(-1) + true_A @ W_installed
        return flat.reshape(n_probes, n_speeds)

    installed = np.zeros(n_planes, dtype=complex)
    measured = true_V0.copy()
    rms_history = [residual_rms(measured)]

    REALIZATION_ERROR_FRAC = 0.08  # can only realize correction weight within 8%

    for _ in range(4):
        result = solve_correction_weights(A, measured)
        delta_w = result.correction_weights
        # Simulate imperfect realization of the computed increment
        noise = (rng.normal(size=delta_w.shape) + 1j * rng.normal(size=delta_w.shape))
        noise *= REALIZATION_ERROR_FRAC * np.abs(delta_w) / np.sqrt(2)
        realized_delta = delta_w + noise
        installed = installed + realized_delta
        measured = true_vibration_for_installed_weight(installed)
        rms_history.append(residual_rms(measured))

    # Converges: last RMS much smaller than the first, and monotonically
    # trending down overall despite realization noise.
    assert rms_history[-1] < rms_history[0] * 0.05
    assert rms_history[-1] < rms_history[1]


def test_combine_weights_vector_sum():
    w1 = mag_phase_to_complex(10, 0)
    w2 = mag_phase_to_complex(10, 180)
    total = combine_weights(w1, w2)
    assert abs(total) < 1e-9  # equal and opposite cancel out

    w3 = mag_phase_to_complex(5, 0)
    w4 = mag_phase_to_complex(5, 0)
    total2 = combine_weights(w3, w4)
    mag, phase = complex_to_mag_phase(total2)
    assert mag == pytest.approx(10)
    assert phase == pytest.approx(0, abs=1e-6)


def test_iso21940_11_eper_known_example():
    """Cross-check against ISO 21940-11 Annex E worked example: G6.3,
    service speed 10 000 r/min, rotor mass 2.5 kg -> e_per and U_per.
    e_per = 9549 * 6.3 / 10000 = 6.016 ... um; U_per = e_per * 2.5 kg
    = 15.04 g.mm total (ISO's Annex E allocates this between two
    tolerance planes per its own geometry; this test only checks our
    e_per/U_per formulas, not the plane allocation, against the standard's
    published formula)."""
    e_per = e_per_iso21940_11(6.3, 10000)
    assert e_per == pytest.approx(9549 * 6.3 / 10000, rel=1e-9)
    u_per = u_per_iso21940_11(6.3, 10000, 2.5)
    assert u_per == pytest.approx(e_per * 2.5, rel=1e-9)


def test_allocate_two_plane_lever_rule_symmetric():
    # CG exactly midway -> equal split
    u1, u2 = allocate_two_plane_lever_rule(100.0, 50.0, 50.0)
    assert u1 == pytest.approx(50.0)
    assert u2 == pytest.approx(50.0)
    # CG closer to plane 1 -> plane 1 gets the larger share
    u1, u2 = allocate_two_plane_lever_rule(100.0, 20.0, 80.0)
    assert u1 > u2
    assert u1 == pytest.approx(80.0)
    assert u2 == pytest.approx(20.0)


def test_iso20816_3_zone_classification():
    assert classify_vibration_zone(2.0, "group1", "rigid") == "A"
    assert classify_vibration_zone(3.0, "group1", "rigid") == "B"
    assert classify_vibration_zone(5.0, "group1", "rigid") == "C"
    assert classify_vibration_zone(8.0, "group1", "rigid") == "D"
    # Flexible support has higher (more lenient) boundaries than rigid
    assert classify_vibration_zone(3.0, "group1", "flexible") == "A"


def test_nearest_g_grade():
    assert nearest_g_grade(2.4) == 2.5
    assert nearest_g_grade(6.0) == 6.3


def test_flexible_modal_limits_are_percentages_of_rigid_u_per():
    u_per = u_per_iso21940_11(6.3, 10000, 2.5)
    limits = flexible_modal_unbalance_limits(u_per)
    assert limits["mode1_limit_g_mm"] == pytest.approx(0.60 * u_per)
    assert limits["mode2_limit_g_mm"] == pytest.approx(0.60 * u_per)
    assert limits["low_speed_total_limit_g_mm"] == pytest.approx(u_per)
    with pytest.raises(ValueError):
        flexible_modal_unbalance_limits(0.0)


def test_api_journal_tolerance_si_and_us_customary_are_consistent():
    # API TR 684-1 / API 617 criterion: U = 6350*W/N (SI, g.mm) = 4*W/N
    # (US customary, oz.in). Check the SI formula directly and that the
    # two unit systems agree once W is converted kg <-> lb.
    u_si = u_per_api_617_684_si(journal_static_load_kg=12.5, service_speed_rpm=10000)
    assert u_si == pytest.approx(6350.0 * 12.5 / 10000)

    w_lb = 12.5 * 2.2046226218  # kg -> lb
    u_oz_in = u_per_api_oz_in(journal_static_load_lb=w_lb, service_speed_rpm=10000)
    assert u_oz_in == pytest.approx(4.0 * w_lb / 10000)

    with pytest.raises(ValueError):
        u_per_api_617_684_si(0.0, 10000)
    with pytest.raises(ValueError):
        u_per_api_oz_in(12.0, 0.0)
