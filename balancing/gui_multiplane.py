"""
Tkinter GUI for generalized multi-plane / multi-speed rotor balancing
(the Generalized Influence Coefficient Method, GICM) plus ISO 21940-11 /
ISO 20816-3 tolerance lookups.

This module is self-contained and is embedded into Rotor_Balancing.py's
"Multi-Plane / Multi-Speed" tab; it can also be run standalone:

    python -m balancing.gui_multiplane
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
import math
from tkinter import ttk, messagebox
import webbrowser

import numpy as np

from .engine import (
    mag_phase_to_complex,
    complex_to_mag_phase,
    combine_weights,
    build_influence_matrix,
    solve_correction_weights,
    residual_rms,
)
from .standards import (
    G_GRADE_TABLE,
    e_per_iso21940_11,
    u_per_iso21940_11,
    allocate_two_plane_lever_rule,
    ISO20816_3_ZONES,
    ZONE_MEANING,
    classify_vibration_zone,
)


class _VectorEntry(ttk.Frame):
    """A small (magnitude, phase) entry pair with labels."""

    def __init__(self, parent, mag_default="", phase_default=""):
        super().__init__(parent)
        self.mag = ttk.Entry(self, width=8)
        self.phase = ttk.Entry(self, width=8)
        self.mag.insert(0, str(mag_default))
        self.phase.insert(0, str(phase_default))
        self.mag.grid(row=0, column=0, padx=1)
        ttk.Label(self, text="@").grid(row=0, column=1)
        self.phase.grid(row=0, column=2, padx=1)
        ttk.Label(self, text="\u00b0").grid(row=0, column=3)

    def get_complex(self) -> complex:
        m = float(self.mag.get())
        p = float(self.phase.get())
        if not math.isfinite(m) or not math.isfinite(p) or m < 0:
            raise ValueError("Amplitude/mass must be finite and non-negative; angle must be finite (non-finite values are rejected).")
        return mag_phase_to_complex(m, p)

    def set_complex(self, value: complex) -> None:
        m, p = complex_to_mag_phase(value)
        self.mag.delete(0, tk.END)
        self.mag.insert(0, f"{m:.3f}")
        self.phase.delete(0, tk.END)
        self.phase.insert(0, f"{p:.2f}")


class MultiPlaneFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.n_planes = tk.IntVar(value=2)
        self.n_probes = tk.IntVar(value=2)
        self.n_speeds = tk.IntVar(value=1)

        self.initial_entries: dict[tuple[int, int], _VectorEntry] = {}
        self.trial_weight_entries: dict[int, _VectorEntry] = {}
        self.trial_run_entries: dict[tuple[int, int, int], _VectorEntry] = {}
        self.trim_entries: dict[tuple[int, int], _VectorEntry] = {}
        self.actual_entries: dict[int, _VectorEntry] = {}

        self.influence_matrix: np.ndarray | None = None
        self.installed_weights: np.ndarray | None = None  # (n_planes,) complex, cumulative
        self.rms_history: list[float] = []
        self.proposed_weights: np.ndarray | None = None
        self._input_snapshot = None

        self._build_setup_section()
        self._grid_frame = None  # built on demand
        ttk.Button(self, text="Help / user guide", command=self._open_help).pack(anchor="e", padx=10)

    def _open_help(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("USER_GUIDE.md", "references.md"):
            path = root / "docs" / name
            if path.exists():
                webbrowser.open(path.as_uri())

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _build_setup_section(self):
        setup = ttk.LabelFrame(self, text="1. Configuration")
        setup.pack(fill="x", padx=8, pady=6)

        for i, (label, var) in enumerate(
            [("Number of correction planes", self.n_planes),
             ("Number of measurement probes", self.n_probes),
             ("Number of balancing speeds", self.n_speeds)]
        ):
            ttk.Label(setup, text=label).grid(row=0, column=2 * i, padx=6, pady=4, sticky="w")
            ttk.Spinbox(setup, from_=1, to=8, textvariable=var, width=4).grid(
                row=0, column=2 * i + 1, padx=6, pady=4
            )

        ttk.Button(setup, text="Build data-entry grid", command=self._build_grid).grid(
            row=0, column=6, padx=12, pady=4
        )

        hint = ("Standard requirement (API 684 / least-squares GICM): "
                "n_probes x n_speeds must be >= n_planes for a determined "
                "or overdetermined (least squares) solution. Fewer "
                "channels than planes gives an underdetermined result "
                "(flagged after solving).")
        ttk.Label(setup, text=hint, foreground="#555", wraplength=760, justify="left").grid(
            row=1, column=0, columnspan=7, sticky="w", padx=6, pady=(0, 4)
        )

    # ------------------------------------------------------------------
    # Dynamic grid: initial run, trial weights, trial runs
    # ------------------------------------------------------------------
    def _build_grid(self):
        if self._grid_frame is not None:
            self._grid_frame.destroy()
        self.initial_entries.clear()
        self.trial_weight_entries.clear()
        self.trial_run_entries.clear()
        self.trim_entries.clear()
        self.actual_entries.clear()
        self.influence_matrix = None
        self.installed_weights = None

        nP, nM, nS = self.n_planes.get(), self.n_probes.get(), self.n_speeds.get()

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=4)
        self._grid_frame = container

        canvas = tk.Canvas(container, height=360)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        # --- Baseline (initial) run ---
        ttk.Label(scroll_frame, text="2. Baseline run (no trial weight) \u2014 amplitude @ phase per probe/speed",
                  font=("", 9, "bold")).grid(row=row, column=0, columnspan=nS + 1, sticky="w", pady=(2, 2))
        row += 1
        ttk.Label(scroll_frame, text="Probe \\ Speed").grid(row=row, column=0, padx=4)
        for s in range(nS):
            ttk.Label(scroll_frame, text=f"Speed {s+1}").grid(row=row, column=s + 1, padx=4)
        row += 1
        for m in range(nM):
            ttk.Label(scroll_frame, text=f"Probe {m+1}").grid(row=row, column=0, padx=4, sticky="w")
            for s in range(nS):
                ve = _VectorEntry(scroll_frame)
                ve.grid(row=row, column=s + 1, padx=2, pady=1)
                self.initial_entries[(m, s)] = ve
            row += 1

        # --- Trial weights ---
        row += 1
        ttk.Label(scroll_frame, text="3. trial mass [g] @ angle [degrees] installed at each plane",
                  font=("", 9, "bold")).grid(row=row, column=0, columnspan=nS + 1, sticky="w", pady=(8, 2))
        row += 1
        for p in range(nP):
            ttk.Label(scroll_frame, text=f"Plane {p+1}").grid(row=row, column=0, padx=4, sticky="w")
            ve = _VectorEntry(scroll_frame)
            ve.grid(row=row, column=1, padx=2, pady=1, sticky="w")
            self.trial_weight_entries[p] = ve
            row += 1

        # --- Trial runs, one block per plane ---
        for p in range(nP):
            row += 1
            ttk.Label(
                scroll_frame,
                text=f"4.{p+1} Trial vibration run [mm/s RMS] @ phase [degrees], only plane {p+1} trial installed",
                font=("", 9, "bold"),
            ).grid(row=row, column=0, columnspan=nS + 1, sticky="w", pady=(8, 2))
            row += 1
            ttk.Label(scroll_frame, text="Probe \\ Speed").grid(row=row, column=0, padx=4)
            for s in range(nS):
                ttk.Label(scroll_frame, text=f"Speed {s+1}").grid(row=row, column=s + 1, padx=4)
            row += 1
            for m in range(nM):
                ttk.Label(scroll_frame, text=f"Probe {m+1}").grid(row=row, column=0, padx=4, sticky="w")
                for s in range(nS):
                    ve = _VectorEntry(scroll_frame)
                    ve.grid(row=row, column=s + 1, padx=2, pady=1)
                    self.trial_run_entries[(p, m, s)] = ve
                row += 1

        # --- Solve button + results ---
        row += 1
        ttk.Button(scroll_frame, text="Solve correction weights", command=self._solve).grid(
            row=row, column=0, columnspan=2, pady=10, sticky="w"
        )
        row += 1
        ttk.Button(scroll_frame, text="Load example", command=self.load_example).grid(row=row-1, column=3, pady=10, sticky="w")
        self.results_text = tk.Text(scroll_frame, height=10, width=90, state="disabled")
        self.results_text.grid(row=row, column=0, columnspan=max(nS + 1, 4), sticky="w", pady=4)

        # --- Trim section ---
        row += 1
        row += 1
        ttk.Label(scroll_frame, text="Actual correction currently installed [g] @ angle (enter measured/as-installed state)", font=("", 9, "bold")).grid(row=row, column=0, columnspan=nS + 1, sticky="w")
        row += 1
        for p in range(nP):
            ttk.Label(scroll_frame, text=f"Plane {p+1}").grid(row=row, column=0, sticky="w")
            ve = _VectorEntry(scroll_frame, "0", "0")
            ve.grid(row=row, column=1, sticky="w")
            self.actual_entries[p] = ve
            row += 1
        row += 1
        ttk.Label(scroll_frame, text="5. Trim pass: enter vibration measured AFTER installing the stated correction",
                  font=("", 9, "bold")).grid(row=row, column=0, columnspan=nS + 1, sticky="w", pady=(10, 2))
        row += 1
        ttk.Label(scroll_frame, text="Probe \\ Speed").grid(row=row, column=0, padx=4)
        for s in range(nS):
            ttk.Label(scroll_frame, text=f"Speed {s+1}").grid(row=row, column=s + 1, padx=4)
        row += 1
        for m in range(nM):
            ttk.Label(scroll_frame, text=f"Probe {m+1}").grid(row=row, column=0, padx=4, sticky="w")
            for s in range(nS):
                ve = _VectorEntry(scroll_frame)
                ve.grid(row=row, column=s + 1, padx=2, pady=1)
                self.trim_entries[(m, s)] = ve
            row += 1
        row += 1
        ttk.Button(scroll_frame, text="Compute trim correction", command=self._trim).grid(
            row=row, column=0, columnspan=2, pady=10, sticky="w"
        )
        row += 1
        self.trim_text = tk.Text(scroll_frame, height=10, width=90, state="disabled")
        self.trim_text.grid(row=row, column=0, columnspan=max(nS + 1, 4), sticky="w", pady=4)

    # ------------------------------------------------------------------
    def load_example(self):
        """Load a deterministic, illustrative two-plane example."""
        if not self.initial_entries:
            self._build_grid()
        if self.n_planes.get() != 2 or self.n_probes.get() != 2 or self.n_speeds.get() != 1:
            messagebox.showinfo("Example", "Set 2 planes, 2 probes and 1 speed before loading this example.")
            return
        for key, value in { (0,0):(2.0,20),(1,0):(1.5,140) }.items(): self.initial_entries[key].set_complex(mag_phase_to_complex(*value))
        for p, value in enumerate(((10,0),(10,0))): self.trial_weight_entries[p].set_complex(mag_phase_to_complex(*value))
        for p, vals in enumerate((((3,30),(2,150)),((2,70),(3,190)))):
            for m, value in enumerate(vals): self.trial_run_entries[(p,m,0)].set_complex(mag_phase_to_complex(*value))

    def _snapshot_inputs(self):
        return tuple((k, v.mag.get(), v.phase.get()) for mapping in
                     (self.initial_entries, self.trial_weight_entries, self.trial_run_entries)
                     for k, v in sorted(mapping.items()))

    def _read_vib_grid(self, entries: dict, nM: int, nS: int) -> np.ndarray:
        arr = np.zeros((nM, nS), dtype=complex)
        for (m, s), ve in entries.items():
            arr[m, s] = ve.get_complex()
        return arr

    def _write_results(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state="disabled")

    def _solve(self):
        try:
            nP, nM, nS = self.n_planes.get(), self.n_probes.get(), self.n_speeds.get()
            initial = self._read_vib_grid(self.initial_entries, nM, nS)
            trial_weights = np.array(
                [self.trial_weight_entries[p].get_complex() for p in range(nP)]
            )
            trial_vib = np.zeros((nP, nM, nS), dtype=complex)
            for p in range(nP):
                for m in range(nM):
                    for s in range(nS):
                        trial_vib[p, m, s] = self.trial_run_entries[(p, m, s)].get_complex()

            A = build_influence_matrix(initial, trial_vib, trial_weights)
            result = solve_correction_weights(A, initial)
            if result.rank < nP:
                raise ValueError(f"Influence matrix rank {result.rank} is below {nP} planes; no unique correction is reported. Repeat/re-plan measurements.")
            self.influence_matrix = A
            self.proposed_weights = result.correction_weights.copy()
            self._input_snapshot = self._snapshot_inputs()
            self.installed_weights = np.zeros(nP, dtype=complex)  # actual installed state must be entered separately
            self.rms_history = [residual_rms(initial), residual_rms(result.predicted_residual)]

            lines = [
                f"Determinacy: {result.determinacy}  "
                f"(n_channels={result.n_channels}, n_planes={result.n_planes})",
                f"Condition number: {result.condition_number:.3g}"
                + ("  ** ILL-CONDITIONED (>100) \u2014 verify trial weight sizes/plane choice before trusting this! **"
                   if result.is_ill_conditioned() else ""),
                "",
                "Correction weights to install (mass @ angle):",
            ]
            for p in range(nP):
                m, ang = complex_to_mag_phase(result.correction_weights[p])
                lines.append(f"  Plane {p+1}: {m:.3f} units @ {ang:.2f}\u00b0")
            lines.append("")
            lines.append("Predicted residual vibration after installing the correction "
                         "(ideal, assumes exact installation \u2014 verify by remeasuring):")
            for m in range(nM):
                for s in range(nS):
                    mag, ang = complex_to_mag_phase(result.predicted_residual[m, s])
                    lines.append(f"  Probe {m+1}, Speed {s+1}: {mag:.3f} @ {ang:.2f}\u00b0")
            lines.append("")
            lines.append("Baseline RMS -> predicted RMS: "
                         f"{self.rms_history[0]:.4f} -> {self.rms_history[1]:.4f}")
            self._write_results(self.results_text, "\n".join(lines))
        except Exception as exc:  # noqa: BLE001 - show the user what went wrong
            messagebox.showerror("Solve failed", str(exc))

    def _trim(self):
        if self.influence_matrix is None or self.installed_weights is None:
            messagebox.showwarning("Not ready", "Solve the initial correction first.")
            return
        try:
            if self._snapshot_inputs() != self._input_snapshot:
                raise ValueError("Baseline/trial data changed after solve. Rebuild the influence matrix before trimming.")
            nP, nM, nS = self.n_planes.get(), self.n_probes.get(), self.n_speeds.get()
            measured = self._read_vib_grid(self.trim_entries, nM, nS)
            actual = np.array([self.actual_entries[p].get_complex() for p in range(nP)])
            result = solve_correction_weights(self.influence_matrix, measured)
            if result.rank < nP:
                raise ValueError("Influence matrix is rank deficient; trim rejected.")
            delta = result.correction_weights

            new_total = actual + delta
            self.rms_history.append(residual_rms(measured))
            self.rms_history.append(residual_rms(result.predicted_residual))

            lines = [
                f"Determinacy: {result.determinacy}  Condition number: {result.condition_number:.3g}",
                "",
                "INCREMENTAL correction to ADD this pass (mass @ angle):",
            ]
            for p in range(nP):
                m, ang = complex_to_mag_phase(delta[p])
                lines.append(f"  Plane {p+1}: +{m:.3f} units @ {ang:.2f}\u00b0")
            lines.append("")
            lines.append("NEW cumulative total weight that should be on each plane "
                         "(vector sum of every round so far):")
            for p in range(nP):
                m, ang = complex_to_mag_phase(new_total[p])
                lines.append(f"  Plane {p+1}: {m:.3f} units @ {ang:.2f}\u00b0")
            lines.append("")
            lines.append("Predicted residual after this trim pass:")
            for m in range(nM):
                for s in range(nS):
                    mag, ang = complex_to_mag_phase(result.predicted_residual[m, s])
                    lines.append(f"  Probe {m+1}, Speed {s+1}: {mag:.3f} @ {ang:.2f}\u00b0")
            lines.append("")
            lines.append("RMS trend across passes: "
                         + " -> ".join(f"{v:.4f}" for v in self.rms_history))
            lines.append("")
            lines.append("If the RMS is not yet within your acceptance tolerance "
                         "(see Standards tab), install the NEW cumulative total weight, "
                         "remeasure, and run another trim pass with the fresh measurement.")
            self._write_results(self.trim_text, "\n".join(lines))
            self.installed_weights = new_total
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Trim failed", str(exc))


class StandardsFrame(ttk.Frame):
    """ISO 21940-11 (G-grade residual unbalance) and ISO 20816-3 (vibration
    severity zone) lookup helpers."""

    def __init__(self, parent):
        super().__init__(parent)

        iso1 = ttk.LabelFrame(self, text="ISO 21940-11 \u2014 permissible residual unbalance")
        iso1.pack(fill="x", padx=8, pady=8)

        ttk.Label(iso1, text="Balance quality grade G [mm/s]").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.g_grade = ttk.Combobox(
            iso1, values=[str(g) for g in sorted(G_GRADE_TABLE)], width=8
        )
        self.g_grade.set("2.5")
        self.g_grade.grid(row=0, column=1, padx=4)

        ttk.Label(iso1, text="Max service speed [rpm]").grid(row=0, column=2, sticky="w", padx=4)
        self.speed = ttk.Entry(iso1, width=10)
        self.speed.insert(0, "10000")
        self.speed.grid(row=0, column=3, padx=4)

        ttk.Label(iso1, text="Rotor mass [kg]").grid(row=0, column=4, sticky="w", padx=4)
        self.mass = ttk.Entry(iso1, width=10)
        self.mass.insert(0, "2.5")
        self.mass.grid(row=0, column=5, padx=4)

        ttk.Button(iso1, text="Calculate", command=self._calc_iso21940).grid(row=0, column=6, padx=8)

        ttk.Label(iso1, text="Plane 1 distance from CG [mm]").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.dist1 = ttk.Entry(iso1, width=10)
        self.dist1.insert(0, "100")
        self.dist1.grid(row=1, column=1, padx=4)
        ttk.Label(iso1, text="Plane 2 distance from CG [mm]").grid(row=1, column=2, sticky="w", padx=4)
        self.dist2 = ttk.Entry(iso1, width=10)
        self.dist2.insert(0, "100")
        self.dist2.grid(row=1, column=3, padx=4)

        self.iso1_result = tk.Text(iso1, height=6, width=90, state="disabled")
        self.iso1_result.grid(row=2, column=0, columnspan=7, padx=4, pady=6, sticky="w")

        iso2 = ttk.LabelFrame(self, text="ISO 20816-3 \u2014 vibration severity zone")
        iso2.pack(fill="x", padx=8, pady=8)

        ttk.Label(iso2, text="Legacy ISO 20816-3:2022 reference only — NOT current acceptance (2026 edition). Use agreed site limit below.", foreground="#a33", wraplength=700).grid(row=0, column=0, columnspan=7, sticky="w", padx=4)
        ttk.Label(iso2, text="Machine group").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.group = ttk.Combobox(iso2, values=["group1", "group2"], width=10, state="readonly")
        self.group.set("group1")
        self.group.grid(row=1, column=1, padx=4)

        ttk.Label(iso2, text="Support class").grid(row=1, column=2, sticky="w", padx=4)
        self.support = ttk.Combobox(iso2, values=["rigid", "flexible"], width=10, state="readonly")
        self.support.set("rigid")
        self.support.grid(row=1, column=3, padx=4)

        ttk.Label(iso2, text="Measured velocity [mm/s RMS]").grid(row=1, column=4, sticky="w", padx=4)
        self.velocity = ttk.Entry(iso2, width=10)
        self.velocity.insert(0, "3.0")
        self.velocity.grid(row=1, column=5, padx=4)

        ttk.Button(iso2, text="Classify (legacy reference)", command=self._classify_iso20816).grid(row=1, column=6, padx=8)

        self.iso2_result = tk.Text(iso2, height=6, width=90, state="disabled")
        self.iso2_result.grid(row=2, column=0, columnspan=7, padx=4, pady=6, sticky="w")

        disclaimer = ttk.LabelFrame(self, text="Verify before using for sign-off")
        disclaimer.pack(fill="x", padx=8, pady=8)
        ttk.Label(
            disclaimer,
            text=("These tables are reproduced for engineering convenience from the public "
                  "summaries of ISO 21940-11 and ISO 20816-3. Confirm the exact clause/table/"
                  "revision in your organization's controlled copy of the standard (and any "
                  "applicable API spec, e.g. API 617/684 acceptance criteria) before using "
                  "these numbers for a contractual or safety acceptance decision."),
            wraplength=760, justify="left", foreground="#a33",
        ).pack(padx=6, pady=6, anchor="w")

    def _write(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state="disabled")

    def _calc_iso21940(self):
        try:
            g = float(self.g_grade.get())
            n = float(self.speed.get())
            m = float(self.mass.get())
            e_per = e_per_iso21940_11(g, n)
            u_per = u_per_iso21940_11(g, n, m)
            lines = [
                f"e_per = 9549 * G / n = 9549 * {g} / {n} = {e_per:.4f} g.mm/kg (= um eccentricity)",
                f"U_per = e_per * m = {e_per:.4f} * {m} = {u_per:.4f} g.mm  (total, for the whole rotor)",
            ]
            d1 = float(self.dist1.get())
            d2 = float(self.dist2.get())
            u1, u2 = allocate_two_plane_lever_rule(u_per, d1, d2)
            lines.append("")
            lines.append("Simplified two-plane lever-rule allocation "
                         "(see ISO 21940-11 Annex B for the rigorous static+couple split):")
            lines.append(f"  Plane 1 (closer side gets more): U_per,1 = {u1:.4f} g.mm")
            lines.append(f"  Plane 2: U_per,2 = {u2:.4f} g.mm")
            lines.append("")
            lines.append(f"Reference (G{g}): {G_GRADE_TABLE.get(g, 'custom/non-standard grade \u2014 verify applicability')}")
            self._write(self.iso1_result, "\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Calculation failed", str(exc))

    def _classify_iso20816(self):
        try:
            v = float(self.velocity.get())
            group = self.group.get()
            support = self.support.get()
            zone = classify_vibration_zone(v, group, support)
            zb = ISO20816_3_ZONES[(group, support)]
            lines = [
                f"Zone boundaries for ({group}, {support}): "
                f"A/B={zb.ab}  B/C={zb.bc}  C/D={zb.cd} mm/s RMS",
                f"Measured {v} mm/s RMS -> Zone {zone}",
                ZONE_MEANING[zone],
            ]
            self._write(self.iso2_result, "\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Classification failed", str(exc))


def build_tabs(notebook: ttk.Notebook) -> tuple[MultiPlaneFrame, StandardsFrame]:
    """Create and attach the Multi-Plane/Multi-Speed and Standards tabs to
    an existing ttk.Notebook, returning the created frames."""
    mp = MultiPlaneFrame(notebook)
    std = StandardsFrame(notebook)
    notebook.add(mp, text="Multi-Plane / Multi-Speed")
    notebook.add(std, text="Standards (ISO 21940-11 / 20816-3)")
    return mp, std


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Multi-Plane / Multi-Speed Rotor Balancing (standalone)")
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    build_tabs(nb)
    root.mainloop()
