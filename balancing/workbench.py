"""Local engineering workbench. Predictions are not measured acceptance results."""
from pathlib import Path
import math
import re
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from .engine import build_influence_matrix, solve_correction_weights
from .gui_multiplane import _VectorEntry

ROOT = Path(__file__).resolve().parents[1]


def number(value, positive=False):
    x = float(value)
    if not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise ValueError('Enter a finite ' + ('positive' if positive else 'non-negative') + ' value.')
    return x


def entry(parent, label, value='', width=10):
    box = ttk.Frame(parent)
    box.pack(side='left', padx=8, pady=6)
    ttk.Label(box, text=label).pack(anchor='w')
    v = ttk.Entry(box, width=width)
    v.insert(0, str(value))
    v.pack(anchor='w')
    return v


def page(notebook, title, instruction):
    outer = ttk.Frame(notebook, padding=10)
    notebook.add(outer, text=title)
    ttk.Label(outer, text=instruction, wraplength=1020, style='Hint.TLabel').pack(anchor='w', pady=(0, 10))
    canvas = tk.Canvas(outer, highlightthickness=0, background='#f2f5f8')
    sy = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
    sx = ttk.Scrollbar(outer, orient='horizontal', command=canvas.xview)
    sy.pack(side='right', fill='y')
    sx.pack(side='bottom', fill='x')
    canvas.pack(fill='both', expand=True)
    inner = ttk.Frame(canvas, padding=6)
    canvas.create_window(0, 0, window=inner, anchor='nw')
    canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    inner.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
    return inner


class BalancePanel(ttk.Frame):
    def __init__(self, parent, single=False):
        super().__init__(parent, padding=8)
        self.single_mode = single
        self.model = None
        setup = ttk.Frame(self)
        setup.pack(fill='x')
        self.counts = [entry(setup, name, val, 6) for name, val in zip(
            ('Planes', 'Probes', 'Speeds'), (1, 1, 1) if single else (2, 2, 2))]
        if single:
            for e in self.counts:
                e.configure(state='disabled')
        ttk.Button(setup, text='Apply configuration / reset', command=self.configure_job).pack(side='left', padx=10)
        ttk.Button(setup, text='Help: load worked example', command=self.example).pack(side='left', padx=10)
        self.status = tk.StringVar(value='Enter the baseline first. No trial weights should be installed.')
        ttk.Label(self, textvariable=self.status, wraplength=1100, style='Hint.TLabel').pack(fill='x', pady=6)
        self.steps = ttk.Notebook(self)
        self.steps.pack(fill='both', expand=True)
        self.build()

    def configure_job(self):
        if messagebox.askyesno('Reset data?', 'Applying configuration clears all entries and results. Continue?'):
            try:
                self.build()
            except Exception as exc:
                messagebox.showerror('Configuration', str(exc))

    def build(self):
        shape = tuple(int(e.get()) for e in self.counts)
        if any(n < 1 or n > 8 for n in shape):
            raise ValueError('Each count must be an integer between 1 and 8.')
        self.shape = shape
        self.model = None
        for tab in self.steps.tabs():
            self.steps.nametowidget(tab).destroy()
        p, m, s = shape
        self.vectors = {}
        baseline = page(self.steps, '1  Baseline', 'NO trial weights installed. Enter synchronous 1× velocity amplitude (mm/s RMS) and phase (°) for every probe at each speed. Do not enter broadband overall vibration here.')
        speedrow = ttk.Frame(baseline)
        speedrow.grid(row=0, column=0, columnspan=s+1, sticky='w')
        self.rpms = [entry(speedrow, f'Speed {j+1} [r/min]', 3000*(j+1)) for j in range(s)]
        self.grid_vectors(baseline, 'baseline', m, s, 1)
        trials = page(self.steps, '2  Trial masses & runs', 'SEQUENTIAL runs: install only the named plane’s trial mass, measure every channel, then REMOVE it before the next plane’s trial. Keep each plane’s trial/correction radius identical. Simultaneous trials are not supported here.')
        self.weights = []
        for i in range(p):
            section = ttk.LabelFrame(trials, text=f'Trial run {i+1} — ONLY Plane {i+1} trial installed', padding=10)
            section.pack(fill='x', pady=6)
            ttk.Label(section, text=f'Plane {i+1}: trial mass [g] / installation angle [°]').grid(row=0, column=0, sticky='w')
            w = _VectorEntry(section)
            w.grid(row=0, column=1, sticky='w')
            self.weights.append(w)
            self.grid_vectors(section, f'trial{i}', m, s, 1)
        results = page(self.steps, '3  Correction & plots', 'REMOVE all trial masses before installing the proposed correction. Masses below are proposals, not confirmed installation. Plot residuals are predictions; verify with another run. Angle zero/direction must match your analyzer and rotor marking.')
        ttk.Button(results, text='Calculate correction and update plots', command=self.safe_solve).pack(anchor='w', pady=8)
        self.result_table = ttk.Treeview(results, columns=('plane', 'mass', 'angle'), show='headings', height=p)
        for key, label in [('plane','Correction plane'),('mass','Proposed addition [g]'),('angle','Installation angle [°]')]:
            self.result_table.heading(key, text=label)
            self.result_table.column(key, width=220, anchor='center')
        self.result_table.pack(fill='x')
        self.figure = Figure(figsize=(10, 4.3), dpi=100, layout='constrained')
        self.plot_canvas = FigureCanvasTkAgg(self.figure, results)
        self.plot_canvas.get_tk_widget().pack(fill='both', expand=True, pady=8)
        NavigationToolbar2Tk(self.plot_canvas, results).update()
        trim = page(self.steps, '4  Verify & trim', 'Enter the ACTUAL installed net correction relative to the baseline (not the last proposal), plus fresh synchronous 1× measurements. Trim is an incremental ADDITION. Alternative: remove that actual correction and install the proposed NET TOTAL — do not add both.')
        self.actual = []
        for i in range(p):
            row = ttk.Frame(trim)
            row.pack(anchor='w', pady=4)
            ttk.Label(row, text=f'Plane {i+1}: actual net correction [g] @ [°]   ').pack(side='left')
            v = _VectorEntry(row, 0, 0)
            v.pack(side='left')
            self.actual.append(v)
        vg = ttk.Frame(trim)
        vg.pack(anchor='w', pady=8)
        self.grid_vectors(vg, 'measured', m, s, 0)
        ttk.Button(trim, text='Calculate incremental trim', command=self.safe_trim).pack(anchor='w', pady=8)
        self.trim_result = ScrolledText(trim, width=115, height=12, wrap='word', font=('Consolas', 10))
        self.trim_result.pack(fill='both', expand=True)
        self.trim_result.configure(state='disabled')

    def grid_vectors(self, parent, name, m, s, row):
        ttk.Label(parent, text='Probe / speed channel').grid(row=row, column=0, sticky='w', padx=5)
        for j in range(s):
            ttk.Label(parent, text=f'Speed {j+1}: mm/s RMS @ °').grid(row=row, column=j+1, padx=8, pady=6)
        for i in range(m):
            ttk.Label(parent, text=f'Probe {i+1}').grid(row=row+i+1, column=0, sticky='w', padx=5)
            for j in range(s):
                v = _VectorEntry(parent)
                v.grid(row=row+i+1, column=j+1, padx=8, pady=5)
                self.vectors[name, i, j] = v

    def values(self, name):
        _, m, s = self.shape
        return np.array([[self.vectors[name,i,j].get_complex() for j in range(s)] for i in range(m)])

    def snapshot(self):
        return (tuple(e.get() for e in self.counts), tuple(e.get() for e in self.rpms),
                tuple((k,v.mag.get(),v.phase.get()) for k,v in self.vectors.items() if k[0] != 'measured'),
                tuple((v.mag.get(),v.phase.get()) for v in self.weights))

    def solve(self):
        self.model = None
        if tuple(int(e.get()) for e in self.counts) != self.shape:
            raise ValueError('Apply configuration before solving changed counts.')
        for e in self.rpms:
            number(e.get(), True)
        base = self.values('baseline')
        trials = np.array([self.values(f'trial{i}') for i in range(self.shape[0])])
        weights = np.array([v.get_complex() for v in self.weights])
        if np.any(np.abs(weights) == 0):
            raise ValueError('Every sequential trial mass must be greater than zero.')
        a = build_influence_matrix(base, trials, weights)
        result = solve_correction_weights(a, base)
        if result.rank < self.shape[0]:
            raise ValueError('Rank-deficient influence matrix: no unique correction. Re-plan independent trials/channels.')
        if result.is_ill_conditioned():
            raise ValueError('Ill-conditioned influence matrix (>100). Re-plan trials before reporting a correction.')
        self.model, self.signature = a, self.snapshot()
        self.result_table.delete(*self.result_table.get_children())
        for i,w in enumerate(result.correction_weights):
            self.result_table.insert('', 'end', values=(f'Plane {i+1}',f'{abs(w):.4f}',f'{np.angle(w,deg=True)%360:.2f}'))
        self.status.set(f'{result.determinacy} | Rank {result.rank} | Condition {result.condition_number:.3g} | PROPOSED correction only — remeasure after installation.')
        self.draw(base, trials, result.predicted_residual)
        return result

    def draw(self, base, trials, predicted):
        self.figure.clear()
        if self.single_mode:
            ax = self.figure.add_subplot(121, projection='polar')
            for value,label,color in [(base[0,0],'Baseline O','#2672b8'),(trials[0,0,0],'Trial run O+T','#d17926'),(trials[0,0,0]-base[0,0],'Trial effect T','#17856b')]:
                ax.plot([np.angle(value),np.angle(value)], [0,abs(value)], marker='o', label=label, color=color)
            ax.set_title('Synchronous 1× vectors [mm/s RMS]')
            ax.legend(loc='lower center', bbox_to_anchor=(.5,-.3), fontsize=8)
        else:
            ax = self.figure.add_subplot(121)
            for i in range(base.shape[0]):
                rpm = [float(e.get()) for e in self.rpms]
                ax.plot(rpm,abs(base[i]),'o-',label=f'Probe {i+1}: baseline')
                ax.plot(rpm,abs(predicted[i]),'s--',label=f'Probe {i+1}: predicted')
            ax.set_xlabel('Speed [r/min]')
            ax.set_ylabel('Synchronous 1× velocity [mm/s RMS]')
            ax.set_title('Baseline versus predicted residual')
            ax.legend(fontsize=8)
            ax.grid(alpha=.25)
        bars = self.figure.add_subplot(122)
        x = np.arange(base.size)
        bars.bar(x-.18, abs(base).ravel(), .36, label='Baseline measured')
        bars.bar(x+.18, abs(predicted).ravel(), .36, label='Residual predicted')
        bars.set_xticks(x, [f'P{i+1}/S{j+1}' for i in range(base.shape[0]) for j in range(base.shape[1])], rotation=45)
        bars.set_ylabel('Synchronous 1× velocity [mm/s RMS]')
        bars.set_title('Each probe / speed channel')
        bars.legend(fontsize=8)
        self.plot_canvas.draw()

    def trim(self):
        if self.model is None or self.snapshot() != self.signature:
            raise ValueError('Solve again: configuration, baseline or trial inputs changed, or no valid influence matrix exists.')
        measured = self.values('measured')
        actual = np.array([v.get_complex() for v in self.actual])
        result = solve_correction_weights(self.model, measured)
        lines = ['TRIM PROPOSAL — does not modify the recorded actual installed state.']
        for i,(old,delta) in enumerate(zip(actual,result.correction_weights)):
            total=old+delta
            lines.append(f'Plane {i+1}: ADD {abs(delta):.4f} g @ {np.angle(delta,deg=True)%360:.2f}°; alternative NET TOTAL {abs(total):.4f} g @ {np.angle(total,deg=True)%360:.2f}°')
        for (i,j),value in np.ndenumerate(result.predicted_residual):
            lines.append(f'Probe {i+1}, Speed {j+1}: measured {abs(measured[i,j]):.4f} -> predicted {abs(value):.4f} mm/s RMS')
        lines.append('Stop and reassess if measured response differs materially from prediction. Unchanged supports, speed, thermal state and linear response are required for matrix reuse.')
        self.trim_result.configure(state='normal')
        self.trim_result.delete('1.0','end')
        self.trim_result.insert('end','\n'.join(lines))
        self.trim_result.configure(state='disabled')
        return result

    def safe_solve(self):
        try:
            self.solve()
        except Exception as exc:
            self.result_table.delete(*self.result_table.get_children())
            self.figure.clear()
            self.plot_canvas.draw()
            self.status.set('No valid correction — resolve the input/model error.')
            messagebox.showerror('Cannot calculate',str(exc))

    def safe_trim(self):
        try:
            self.trim()
        except Exception as exc:
            messagebox.showerror('Cannot trim',str(exc))

    def example(self):
        # Deterministic synthetic teaching example; not measured machine data.
        self.build()
        p,m,s=self.shape
        if self.single_mode:
            self.vectors['baseline',0,0].set_complex(5.6*np.exp(1j*np.deg2rad(135)))
            self.vectors['trial0',0,0].set_complex(3.3*np.exp(1j*np.deg2rad(238)))
            self.weights[0].set_complex(74*np.exp(1j*np.deg2rad(315)))
        else:
            rng=np.random.default_rng(271)
            a=(rng.normal(size=(m*s,p))+1j*rng.normal(size=(m*s,p)))*.04
            unbalance=np.arange(1,p+1)*8*np.exp(1j*np.arange(p))
            base=(a@unbalance).reshape(m,s)
            for i in range(p):
                w=20*np.exp(1j*i)
                self.weights[i].set_complex(w)
                trial=base+(a[:,i]*w).reshape(m,s)
                for (j,k),v in np.ndenumerate(trial):
                    self.vectors[f'trial{i}',j,k].set_complex(v)
            for (j,k),v in np.ndenumerate(base):
                self.vectors['baseline',j,k].set_complex(v)
        self.status.set('SYNTHETIC WORKED EXAMPLE loaded. Inspect baseline and each trial, then calculate in step 3. Fields are rounded for display.')
        self.steps.select(0)


class Application(ttk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.pack(fill='both',expand=True)
        root.title('Sahyadri Precision | Rotor Balancing Workbench')
        root.geometry('1220x850')
        root.minsize(900,650)
        style=ttk.Style(root)
        style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background='#f2f5f8',foreground='#192f42')
        style.configure('TButton',padding=(12,7))
        style.configure('TNotebook.Tab',padding=(16,9))
        style.configure('TLabelframe.Label',font=('Segoe UI',11,'bold'))
        style.configure('Hint.TLabel',foreground='#425c70',padding=4)
        style.configure('Treeview',rowheight=28,background='white',fieldbackground='white')
        header=tk.Frame(self,bg='#142d40')
        header.pack(fill='x')
        png=ROOT/'assets/sahyadri_precision.png'
        if png.exists():
            from PIL import Image, ImageTk
            with Image.open(png) as image:
                self.icon=ImageTk.PhotoImage(image.convert('RGBA'), master=root)
                self.small=ImageTk.PhotoImage(image.resize((64,64)).convert('RGBA'), master=root)
            root.iconphoto(True,self.icon)
            tk.Label(header,image=self.small,bg='#142d40').pack(side='left',padx=12,pady=8)
        tk.Label(header,text='SAHYADRI PRECISION  /  Rotor Balancing',font=('Segoe UI',18,'bold'),fg='white',bg='#142d40').pack(side='left',padx=12)
        nb=ttk.Notebook(self)
        nb.pack(fill='both',expand=True,padx=8,pady=8)
        self.single=BalancePanel(nb,True)
        self.multi=BalancePanel(nb)
        nb.add(self.single,text='Single plane')
        nb.add(self.multi,text='Multi-plane / multi-speed')
        standards=ttk.Frame(nb,padding=16)
        nb.add(standards,text='Standards & tolerances')
        self.standards_ui(standards)
        helpframe=ttk.Frame(nb,padding=12)
        nb.add(helpframe,text='Help & research papers')
        self.help_text=ScrolledText(helpframe,wrap='word',font=('Segoe UI',11),padx=15,pady=15)
        self.help_text.pack(fill='both',expand=True)
        for f in ('USER_GUIDE.md','references.md'):
            path=ROOT/'docs'/f
            if path.exists():
                self.help_text.insert('end',path.read_text(encoding='utf-8')+'\n\n')
        text=self.help_text.get('1.0','end')
        for i,match in enumerate(re.finditer(r'https?://[^\s)]+',text)):
            tag=f'url{i}'
            self.help_text.tag_add(tag,f'1.0+{match.start()}c',f'1.0+{match.end()}c')
            self.help_text.tag_config(tag,foreground='#087e8b',underline=True)
            self.help_text.tag_bind(tag,'<Button-1>',lambda event,url=match.group():webbrowser.open(url))
        self.help_text.configure(state='disabled')
        ttk.Label(self,text='Engineering aid — not certified for high-speed operation. Verify trial safety, attachment/radius, phase convention and machine-specific acceptance.',style='Hint.TLabel').pack(fill='x',padx=10,pady=4)

    def standards_ui(self, parent):
        ttk.Label(parent,text='Residual unbalance (a property of the rotor) and measured vibration (a property of rotor + support + speed) are DIFFERENT acceptance quantities. ISO sizes tolerance from rotor mass/grade; API sizes it from journal bearing load.',font=('Segoe UI',13,'bold'),wraplength=1080).pack(anchor='w',pady=10)

        ttk.Label(parent,text='1) ISO 21940-11 — RIGID-behaviour rotor residual unbalance',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(6,0))
        ttk.Label(parent,text='G [mm/s] is a balance-quality grade, NOT a measured bearing vibration tolerance. e_per = 9549 × G / N  [µm = g·mm/kg];  U_per = e_per × rotor mass  [g·mm], the TOTAL allowance for the whole rotor (split across tolerance planes separately — see Annex B / the two-plane lever-rule note below).',wraplength=1080).pack(anchor='w')
        row=ttk.Frame(parent)
        row.pack(fill='x',pady=8)
        self.grade=entry(row,'Grade G [mm/s]',2.5)
        self.service=entry(row,'Max service [r/min]',10000)
        self.mass=entry(row,'Rotor mass [kg]',2.5)
        ttk.Button(row,text='Calculate ISO rigid U_per',command=self.calc_unbalance).pack(side='left',padx=12)
        self.u_result=tk.StringVar()
        ttk.Label(parent,textvariable=self.u_result,wraplength=1050).pack(anchor='w',pady=8)

        ttk.Separator(parent).pack(fill='x',pady=12)
        ttk.Label(parent,text='2) ISO 21940-12 — FLEXIBLE-behaviour rotor: equivalent MODAL residual unbalance limits',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(parent,text='ISO 21940-12 gives no independent formula: it derives equivalent modal unbalance limits as a percentage of the RIGID U_per above, computed for the same rotor. Generic guidance: each significant bending mode (1st, 2nd) <= 60% of U_per; if balancing is also/only done at low speed as a rigid body, total rigid-body residual <= 100% of U_per. Uses the U_per from section 1 - calculate that first. This does NOT implement the standards Annex D procedure for evaluating modal unbalance from measured mode shapes; it only scales the rigid-rotor allowance.',wraplength=1080).pack(anchor='w',pady=(4,0))
        ttk.Button(parent,text='Calculate ISO flexible modal limits (uses U_per above)',command=self.calc_flexible).pack(anchor='w',pady=8)
        self.flex_result=tk.StringVar()
        ttk.Label(parent,textvariable=self.flex_result,wraplength=1050).pack(anchor='w',pady=(0,8))

        ttk.Separator(parent).pack(fill='x',pady=12)
        ttk.Label(parent,text='3) API (617 / 612 / 610, via API TR 684-1) — rigid-rotor tolerance PER JOURNAL',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(parent,text='API sizes the tolerance from the JOURNAL STATIC LOAD (bearing reaction), not total rotor mass: U_per = 6350 × W / N  [g·mm] (SI) = 4 × W / N  [oz·in] (US customary), W = static load on that journal [kg or lb], N = speed nearest the balance/critical speed of concern [r/min]. One plane per journal (typically 2 planes total). This is numerically close to ISO grade G≈1.0 for many pumps/compressors — noticeably tighter than the commonly-used ISO G2.5.',wraplength=1080).pack(anchor='w',pady=(4,0))
        row=ttk.Frame(parent)
        row.pack(fill='x',pady=8)
        self.journal_load=entry(row,'Journal static load W [kg]',12.5)
        self.api_speed=entry(row,'Speed near critical N [r/min]',10000)
        ttk.Button(row,text='Calculate API journal U_per',command=self.calc_api).pack(side='left',padx=12)
        self.api_result=tk.StringVar()
        ttk.Label(parent,textvariable=self.api_result,wraplength=1050).pack(anchor='w',pady=8)

        ttk.Separator(parent).pack(fill='x',pady=15)
        ttk.Label(parent,text='4) Measured broadband velocity — agreed criterion at nominal operating speed',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(parent,text='No universal conversion from g·mm (ISO/API residual unbalance, sections 1–3) or rpm to measured mm/s exists. Enter a verified contractual/site limit for the correct machine, sensor, location and operating condition. ISO 20816-3:2026 supersedes 2022; no unverified zone limits are supplied here.',wraplength=1050).pack(anchor='w',pady=8)
        row=ttk.Frame(parent)
        row.pack(fill='x')
        self.nominal=entry(row,'Nominal speed [r/min]',3000)
        self.limit=entry(row,'Agreed limit [mm/s RMS]','')
        self.measured=entry(row,'Measured [mm/s RMS]','')
        self.source=entry(row,'Criterion source / clause / location','',36)
        ttk.Button(parent,text='Compare to entered criterion',command=self.compare).pack(anchor='w',pady=10)
        self.v_result=tk.StringVar()
        ttk.Label(parent,textvariable=self.v_result,wraplength=1050).pack(anchor='w')

    def calc_unbalance(self):
        try:
            g,n,m=(number(e.get(),True) for e in (self.grade,self.service,self.mass))
            e=9549.0*g/n
            self.u_per_rigid=m*e
            self.u_result.set(f'e_per = 9549×G/N = {e:.4f} µm (g·mm/kg); U_per = m × e_per = {self.u_per_rigid:.4f} g·mm.\nSelected G = {g:g} mm/s — NOT a measured vibration limit. Total rotor allowance; plane allocation requires separate review (ISO 21940-11 Annex B for the full static+couple split).')
        except Exception as exc:
            self.u_result.set(f'Invalid input: {exc}')

    def calc_flexible(self):
        try:
            if not hasattr(self,'u_per_rigid'):
                raise ValueError('Calculate the ISO rigid U_per in section 1 first.')
            u=self.u_per_rigid
            self.flex_result.set(
                f'From rigid U_per = {u:.4f} g·mm:\n'
                f'  Equivalent 1st modal residual unbalance limit  ≤ 60% × U_per = {0.60*u:.4f} g·mm\n'
                f'  Equivalent 2nd modal residual unbalance limit  ≤ 60% × U_per = {0.60*u:.4f} g·mm\n'
                f'  If ALSO/ONLY low-speed (rigid-body) balanced: total residual ≤ 100% × U_per = {u:.4f} g·mm\n'
                'Generic ISO 21940-12 guidance percentages, applied to this rotors own U_per. Does not replace the standards modal-unbalance evaluation procedure (Annex D) or machine-specific review.'
            )
        except Exception as exc:
            self.flex_result.set(f'Invalid input: {exc}')

    def calc_api(self):
        try:
            w,n=(number(e.get(),True) for e in (self.journal_load,self.api_speed))
            u_si=6350.0*w/n
            u_oz_in=4.0*(w*2.2046226218)/n
            self.api_result.set(f'U_per (this journal) = 6350×W/N = {u_si:.4f} g·mm  (= {u_oz_in:.4f} oz·in).\nReferenced to this journals static load only — repeat per journal/plane; do not use total rotor mass here.')
        except Exception as exc:
            self.api_result.set(f'Invalid input: {exc}')

    def compare(self):
        try:
            n=number(self.nominal.get(),True)
            limit=number(self.limit.get(),True)
            measured=number(self.measured.get())
            if not self.source.get().strip():
                raise ValueError('Record the criterion source, clause and measurement location.')
            outcome='WITHIN entered criterion' if measured<=limit else 'EXCEEDS entered criterion'
            self.v_result.set(f'At {n:g} r/min: {measured:g} mm/s RMS vs {limit:g} mm/s RMS: {outcome}.\nSource: {self.source.get()}. This comparison does not establish ISO/API compliance or rotor balance acceptance.')
        except Exception as exc:
            self.v_result.set(f'Invalid input: {exc}')


def main():
    root=tk.Tk()
    Application(root)
    root.mainloop()


if __name__=='__main__':
    main()
