# Rotor Balancing Workbench — user guide

## Purpose and safety

`python Rotor_Balancing.py` launches the local Tkinter workbench. It calculates candidate influence-coefficient corrections from synchronous 1× vibration amplitude/phase inputs. It is an engineering aid, not a certified balancing instrument, rotordynamics model, or proof of ISO/API acceptance. Use qualified engineering review, applicable controlled standards/specifications, and safe-work procedures. Predictions are not measured acceptance results.

The influence-coefficient model assumes response varies approximately linearly with complex correction weight and that measurement conditions remain comparable. Response can be sensitive to speed, support state, temperature, load, runout and other changes, especially near critical speeds. Stop if trial response is unsafe, inconsistent or materially unlike prediction. The software does not enforce trial-weight limits, validate physical installation, or save job records; retain an external run sheet.

## Terms and units

- **Vibration vector:** synchronous 1× amplitude and phase for a defined probe, speed, measurement direction and operating state. Inputs are mm/s RMS. Use one analyzer phase reference and convention consistently; do not mix measurement quantities or amplitude conventions.
- **Trial/correction mass:** complex mass in grams at an angular position. The same documented radius must be used for trials and corrections in a plane, or values must be consistently converted to equivalent unbalance (mass × radius, e.g. g·mm). Masses at differing radii are not interchangeable without conversion.
- **Balance grade G:** a residual-unbalance quality descriptor conventionally expressed in mm/s, not measured bearing vibration. There is no universal conversion from rpm or G to an acceptable measured vibration limit.

## Workbench layout and four stages

The application provides **Single plane** and **Multi-plane / multi-speed** modes. Each mode uses the same four numbered stages. The single-plane counts are fixed at one plane, probe and speed. Multi-plane/multi-speed permits 1–8 planes, probes and speeds; changing configuration resets entries and results.

1. **Baseline.** With NO trial weights installed, enter the synchronous 1× velocity amplitude (mm/s RMS) and phase for each probe at each speed. Enter speeds in r/min. Do not enter broadband overall vibration.
2. **Trial masses & runs.** Runs are sequential: install only the named plane’s trial mass, measure every channel, and remove that mass before the next plane’s trial. Keep trial and correction radius identical in each plane. Simultaneous trial masses are not supported. Each trial response is compared to the original no-trial baseline.
3. **Correction & plots.** Calculate the candidate correction. Rank-deficient or ill-conditioned influence matrices (>100 condition number) are rejected. Results are proposed additions, not confirmation of installation. The single-plane polar plot distinguishes **Baseline O**, **Trial run O+T**, and **Trial effect T**; multi-plane plots show **baseline measured** against **predicted residual** across probe/speed channels. Legends identify the plotted series. Predictions must not be described as measurements.
4. **Verify & trim.** Remove all trial masses before installing the proposed correction. Enter the **actual installed net correction** relative to baseline—not the previous proposal—and fresh synchronous 1× measurements. The trim result is an incremental addition; it also reports the candidate net total (vector sum of actual plus increment) as an alternative if the actual correction is removed and replaced. Do not add the increment to an already-installed net-total proposal. Predicted residuals are model outputs; remeasure after any approved trim and compare actual response with prediction.

The **Help: load worked example** button loads deterministic synthetic teaching data, not machine measurements. Inspect the inputs, then calculate in stage 3. Example values are rounded for display.

## Model interpretation and limitations

For each probe/speed channel, the model is `V_after ≈ V_measured + A·W`, with `A` derived from sequential trial response changes divided by complex trial weights. The solver seeks weights reducing complex vibration by least squares across included channels. Least squares can improve aggregate error while worsening an individual channel; review every predicted residual against the applicable agreed criterion.

A channel count at least as large as the plane count does not establish uniqueness: the influence matrix must have full column rank. Conditioning also matters. The program cannot independently verify that trial masses were removed, speeds and conditions matched, sensor setup was sound, or radii/sign conventions were appropriate. Check the run log and installation feasibility independently. Discrete weights, available holes, angular restrictions and attachment limits may make a mathematical solution impractical.

Trim reuses the original matrix only if its local linear approximation remains valid. Comparable rotor/support state and operating conditions are required. Stop and reassess or acquire new data if measured response materially differs from prediction, conditions change, or corrections challenge linearity. The application does not persist a job history or measurement record.

## Standards & tolerances tab

Four numbered sections, in order, because ISO and API size tolerance from different quantities and flexible-rotor tolerance is derived from the rigid-rotor result, not computed independently:

1. **ISO 21940-11 — rigid-behaviour rotor.** `ω = 2πn/60` rad/s; `e_per = 9549 × G / n` (µm = g·mm/kg); `U_per = rotor mass × e_per` (g·mm) — the TOTAL allowance for the whole rotor. This is a sizing aid, not the Annex B static/couple plane-allocation procedure.
2. **ISO 21940-12 — flexible-behaviour rotor.** ISO 21940-12 does not give an independent tolerance formula: it scales the rigid-rotor `U_per` from section 1 by generic percentages — each significant bending mode (1st, 2nd) ≤ 60% of `U_per`; if low-speed (rigid-body) balancing is also or only performed, total residual ≤ 100% of `U_per`. Calculate section 1 first; the button reuses that result. This is NOT the standard's Annex D procedure for evaluating equivalent modal unbalance from measured mode shapes — it is a sizing aid only.
3. **API (617/612/610, via API TR 684-1) — rigid-rotor tolerance per journal.** `U_per = 6350 × W / N` [g·mm] (SI) = `4 × W / N` [oz·in] (US customary), where `W` is the STATIC LOAD on that journal (bearing reaction), not total rotor mass, and `N` is the speed nearest the balance/critical speed of concern. Typically one plane per journal (two planes total for a two-bearing rotor). Numerically close to ISO grade G≈1.0 for many pumps/compressors — tighter than the commonly-used ISO G2.5.
4. **Measured broadband velocity.** No universal conversion from g·mm (sections 1–3) or rpm to measured mm/s exists. Enter a verified agreed limit at nominal operating speed, the measured mm/s RMS value, and criterion source/clause/location. It compares only the entered measurement and limit; it does not establish ISO/API compliance or rotor balance acceptance. The ISO 20816-3 zone-boundary table bundled in `balancing/standards.py` reflects the now-superseded 2022-era thresholds (replaced by the October 2026 edition) and is not exposed in this tab for that reason — use the controlled current standard and an explicit agreed limit instead.

## References

See [references.md](references.md) for official standards pages, research sources and interpretation notes. Public abstracts are not substitutes for controlled standards text.
