"""
Helper functions for the residual-unbalance TOLERANCE standards commonly
referenced in rotor balancing acceptance criteria, for both rigid- and
flexible-behaviour rotors, under ISO and API:

- ISO 21940-11:2016 (+ Amd 1:2022) "Rotor balancing -- Part 11: Procedures
  and tolerances for rotors with RIGID behaviour" (successor to the
  withdrawn ISO 1940-1). Balance-quality-grade (G) permissible residual
  unbalance formula, e_per/U_per, and a reference table of typical G
  grades by machine type (its Table 1).

- ISO 21940-12:2016 "Rotor balancing -- Part 12: Procedures and tolerances
  for rotors with FLEXIBLE behaviour". Does NOT give an independent
  tolerance formula: it derives equivalent-MODAL residual unbalance limits
  as a percentage of the rigid-rotor U_per from Part 11 computed for the
  same rotor (generic guidance: <=60% of U_per per bending mode judged
  significant, <=100% total if also/only low-speed/rigid-body balanced).
  The standard's full procedure for *evaluating* equivalent modal
  unbalance from measured mode shapes (its Annex D) is not implemented
  here.

- API rotor-dynamics tutorial formula (API TR 684-1, restating the
  criterion used by API 617/612/610 and historically MIL-STD-167-1) for
  rigid-rotor residual-unbalance tolerance PER JOURNAL/CORRECTION PLANE,
  referenced to that journal's static load (not total rotor mass):
  U_per = 6350*W/N [g.mm] (SI) = 4*W/N [oz.in] (US customary), W = journal
  static load, N = speed nearest the balance/critical speed of concern.

- ISO 20816-3:2022 "Mechanical vibration -- Measurement and evaluation of
  machine vibration -- Part 3" broadband RMS velocity zone boundaries
  (A/B, B/C, C/D). NOTE: ISO 20816-3 was reissued in 2026; the 2022-era
  thresholds retained here for backward compatibility are SUPERSEDED --
  see docs/references.md. Prefer the workbench's "agreed limit" comparison
  (a user-entered, verified contractual/site criterion) over this table.

IMPORTANT -- verify before using for formal acceptance / sign-off
-------------------------------------------------------------------
Every table/formula below is reproduced from the standards' well-known
public summaries, tutorials or secondary engineering literature, for
convenience. None of this is a substitute for your organization's
controlled copies of ISO 21940-11, ISO 21940-12, ISO 20816-3, or the
applicable API spec (610/612/613/617/684) for the specific machine class.
Confirm the exact clause/table/edition/amendment that applies to your
equipment before using these values for a contractual or safety
acceptance decision. See docs/references.md for full source citations.
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# ISO 21940-11 -- balance quality grade G
# ---------------------------------------------------------------------------

#: ISO 21940-11 Table 1 (reproduced), balance quality grade G [mm/s] and
#: representative rotor/machine types. G = e_per * Omega, where e_per is
#: the permissible residual specific unbalance [um] and Omega the max
#: service angular velocity [rad/s].
G_GRADE_TABLE: dict[float, str] = {
    4000: "Crankshaft/drives of rigidly mounted slow marine diesel engines (odd number of cylinders)",
    1600: "Crankshaft/drives of large two-cycle engines, rigidly mounted",
    630: "Crankshaft/drives of large four-cycle engines, rigidly mounted; marine diesel engines",
    250: "Crankshaft/drives, elastically mounted, large diesel engines; rigidly mounted fast 4-cyl. diesel engines",
    100: "Crankshaft/drives of fast four-cylinder diesel engines, elastically mounted",
    40: "Car wheels, wheel rims, wheel sets, drive shafts; crankshaft/drives of fast diesel engines (6+ cyl.), elastically mounted",
    16: "Drive shafts (propeller shafts, cardan shafts) with special requirements; parts of crushing/agricultural machinery; automotive parts",
    6.3: "Parts of process-plant machines; marine main-turbine gears; fans; flywheels; pump impellers; machine-tool/general machinery parts; normal electric armatures; individual components of engines under special requirements",
    2.5: "Gas and steam turbines (incl. marine main turbines); rigid turbo-generator rotors; turbo-compressors; machine-tool drives; medium/large electric armatures without special requirements; small electric armatures; turbine-driven pumps",
    1.0: "Tape recorder and phonograph (gramophone) drives; grinding-machine drives; small electric armatures with special requirements",
    0.4: "Spindles, discs, and armatures of precision grinders; gyroscopes",
}


def nearest_g_grade(target_g: float) -> float:
    """Return the standard G grade from G_GRADE_TABLE closest to target_g."""
    return min(G_GRADE_TABLE, key=lambda g: abs(g - target_g))


def e_per_iso21940_11(g_grade: float, service_speed_rpm: float) -> float:
    """Permissible residual specific unbalance e_per [g.mm/kg] (numerically
    equal to micrometres of mass-centre eccentricity), per ISO 21940-11
    Formula e_per = 9549 * G / n, with service speed n in rev/min.

    9549 = 60 * 1000 / (2*pi), the conversion from G [mm/s] = e_per[mm] *
    Omega[rad/s] into e_per[um] with n in rpm.
    """
    if service_speed_rpm <= 0:
        raise ValueError("service_speed_rpm must be > 0")
    return 9549.0 * g_grade / service_speed_rpm


def u_per_iso21940_11(
    g_grade: float, service_speed_rpm: float, rotor_mass_kg: float
) -> float:
    """Total permissible residual unbalance U_per [g.mm] for the whole
    rotor, per ISO 21940-11: U_per = e_per * m.
    """
    if rotor_mass_kg <= 0:
        raise ValueError("rotor_mass_kg must be > 0")
    return e_per_iso21940_11(g_grade, service_speed_rpm) * rotor_mass_kg


def flexible_modal_unbalance_limits(u_per_rigid_g_mm: float) -> dict[str, float]:
    """ISO 21940-12:2016 ("rotors with flexible behaviour") residual
    MODAL unbalance guidance, expressed as a percentage of the rigid-rotor
    permissible residual unbalance U_per computed from ISO 21940-11 for the
    same rotor (service speed, mass, selected G grade):

    - Equivalent 1st modal residual unbalance  <= 60% of U_per
    - Equivalent 2nd modal residual unbalance  <= 60% of U_per
    - If balancing is additionally/only done at LOW speed (as a rigid
      body), the total rigid-body residual unbalance <= 100% of U_per

    These percentages are the generic guidance figures given in ISO
    21940-12 (see also energy-sector summaries of the standard, e.g.
    Noeremark, "Vibration in nuclear application", Energiforsk 2018,
    citing ISO 21940-12 clause 9). ISO 21940-12 explicitly derives
    flexible-rotor tolerances FROM the ISO 21940-11 rigid-rotor U_per --
    it is not an independent formula. If one bending mode is known to be
    less significant than the other, its limit may be relaxed, but
    neither limit may exceed 100%. This helper applies the generic
    percentages; the standard's actual modal-unbalance *evaluation*
    procedure (equivalent modal unbalance from measured mode shapes, per
    its Annex D) is NOT implemented here and must be done per the
    controlled standard text.
    """
    if u_per_rigid_g_mm <= 0:
        raise ValueError("u_per_rigid_g_mm must be > 0")
    return {
        "mode1_limit_g_mm": 0.60 * u_per_rigid_g_mm,
        "mode2_limit_g_mm": 0.60 * u_per_rigid_g_mm,
        "low_speed_total_limit_g_mm": 1.00 * u_per_rigid_g_mm,
    }


def u_per_api_617_684_si(journal_static_load_kg: float, service_speed_rpm: float) -> float:
    """API residual-unbalance tolerance per correction plane (journal),
    SI units, g.mm:

        U_per = 6350 * W / N

    where W = journal static load [kg] (the static bearing reaction at
    that journal, NOT total rotor mass) and N = operating speed nearest
    the balance/critical speed of concern [r/min]. This is the formula
    given in the API rotor-dynamics tutorial (API TR 684-1, restating the
    API SP 2.8.2.4 criterion used by API 617/612/684 for rigid-rotor
    unbalance tolerance), and is algebraically the same 4*W/N criterion
    used historically by API 610/612/617 and MIL-STD-167-1 in US
    customary units -- see u_per_api_oz_in for that form. Two correction
    planes (one per journal) are typical; this returns the tolerance for
    ONE journal/plane using that journal's own static load, not the
    rotor's total mass.
    """
    if journal_static_load_kg <= 0 or service_speed_rpm <= 0:
        raise ValueError("journal_static_load_kg and service_speed_rpm must be > 0")
    return 6350.0 * journal_static_load_kg / service_speed_rpm


def u_per_api_oz_in(journal_static_load_lb: float, service_speed_rpm: float) -> float:
    """API residual-unbalance tolerance per correction plane (journal), US
    customary units, oz.in: U_per = 4 * W / N, W in lb, N in r/min.
    """
    if journal_static_load_lb <= 0 or service_speed_rpm <= 0:
        raise ValueError("journal_static_load_lb and service_speed_rpm must be > 0")
    return 4.0 * journal_static_load_lb / service_speed_rpm


def allocate_two_plane_lever_rule(
    u_per_total_g_mm: float,
    distance_plane1_from_cg_mm: float,
    distance_plane2_from_cg_mm: float,
) -> tuple[float, float]:
    """Simplified two-plane allocation of a total permissible residual
    unbalance to two tolerance/correction planes straddling the rotor's
    centre of mass, by the inverse-lever rule (closer plane carries the
    larger share):

        U_per,1 = U_per * b / (a + b)
        U_per,2 = U_per * a / (a + b)

    where a = distance from CG to plane 1, b = distance from CG to plane 2.

    This is a simplified, commonly-taught allocation for a rotor whose
    unbalance is predominantly a couple (or for a first-pass budget split).
    ISO 21940-11 Annex B gives the full static + couple decomposition
    (separating U_per into a static component and a couple component and
    allocating each independently) -- use Annex B directly for a
    rigorous, contractual tolerance allocation on an asymmetric rotor.
    """
    a = distance_plane1_from_cg_mm
    b = distance_plane2_from_cg_mm
    if a < 0 or b < 0 or (a + b) <= 0:
        raise ValueError("plane distances from CG must be >= 0 and not both 0")
    u1 = u_per_total_g_mm * b / (a + b)
    u2 = u_per_total_g_mm * a / (a + b)
    return u1, u2


# ---------------------------------------------------------------------------
# ISO 20816-3 -- vibration severity zones
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ZoneBoundaries:
    ab: float  # Zone A/B boundary, mm/s RMS
    bc: float  # Zone B/C boundary, mm/s RMS
    cd: float  # Zone C/D boundary, mm/s RMS


#: ISO 20816-3 broadband RMS velocity zone boundaries [mm/s], by machine
#: group and support stiffness class.
#:   Group 1: large machines, rated power > 300 kW (up to 50 MW); electrical
#:            machines with shaft height H >= 315 mm.
#:   Group 2: medium machines, 15 kW < rated power <= 300 kW; electrical
#:            machines with 160 mm <= H < 315 mm.
#: "Rigid" support: combined machine/support natural frequency >= 1.25x the
#: main excitation (running speed) frequency. Otherwise "flexible".
ISO20816_3_ZONES: dict[tuple[str, str], ZoneBoundaries] = {
    ("group1", "rigid"): ZoneBoundaries(ab=2.3, bc=4.5, cd=7.1),
    ("group1", "flexible"): ZoneBoundaries(ab=3.5, bc=7.1, cd=11.0),
    ("group2", "rigid"): ZoneBoundaries(ab=1.4, bc=2.8, cd=4.5),
    ("group2", "flexible"): ZoneBoundaries(ab=2.3, bc=4.5, cd=7.1),
}

ZONE_MEANING = {
    "A": "Newly commissioned machine condition -- typically satisfactory for new/overhauled equipment.",
    "B": "Acceptable for unrestricted long-term operation.",
    "C": "Unsatisfactory for continuous long-term operation; operate only for a limited period until remedial action can be taken.",
    "D": "Vibration severity normally considered sufficient to cause damage to the machine.",
}


def classify_vibration_zone(
    velocity_mm_s_rms: float, group: str, support: str
) -> str:
    """Classify a broadband RMS vibration velocity reading [mm/s] into an
    ISO 20816-3 zone ('A', 'B', 'C', or 'D') for the given machine group
    ('group1'/'group2') and support class ('rigid'/'flexible').
    """
    key = (group.lower(), support.lower())
    if key not in ISO20816_3_ZONES:
        raise ValueError(f"Unknown (group, support) combination: {key}")
    zb = ISO20816_3_ZONES[key]
    if velocity_mm_s_rms <= zb.ab:
        return "A"
    if velocity_mm_s_rms <= zb.bc:
        return "B"
    if velocity_mm_s_rms <= zb.cd:
        return "C"
    return "D"
