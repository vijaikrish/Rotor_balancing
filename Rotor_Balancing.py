# Single plane balancing
# Two plane balancing with single speed
# Two plane balancing with multiple speeds
# Three plane balancing with multiple speeds
# Influence coefficient method
import numpy as np
from tkinter import *
import cmath
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


# from numpy import angle

root = Tk()
root.title('ROTOR BALANCING')
root.iconbitmap('icon.ico')


def mag2comp(m, theta):
    x = m * np.cos(theta * (np.pi / 180))
    y = m * np.sin(theta * (np.pi / 180))
    com = complex(x, y)
    return com


def comp2phase(d):
    pha = (180 / np.pi) * cmath.phase(d)
    return pha


def comp2mag(m):
    m = abs(m)
    return m


tab = ttk.Notebook(root)
sp = ttk.Frame(tab)
tp = ttk.Frame(tab)
hep = ttk.Frame(tab)
inf = ttk.Frame(tab)

tab.add(sp, text='Single Plane')
tab.add(tp, text='Two Plane')
tab.add(hep, text='Help')
tab.add(inf, text='Program info')
tab.grid(row=0, column=0, columnspan=10, sticky="NW")

# Tile
lbl_run = Label(sp, text='')
lbl_mag = Label(sp, text='Amplitude')
lbl_phase = Label(sp, text='Phase Angle')

# Single plane balancing
lbl_ini_mag = Label(sp, text='Initial Run')
ini_mag = Entry(sp)
ini_mag.insert(0, 'mm/s')
ini_phase = Entry(sp)
ini_phase.insert(0, 'degree')

lbl_tr_mag = Label(sp, text='Trial Run')
tr_mag = Entry(sp)
tr_mag.insert(0, 'mm/s')
tr_phase = Entry(sp)
tr_phase.insert(0, 'degree')

lbl_tw = Label(sp, text='Trial Weight')
tw_w = Entry(sp)
tw_w.insert(0, 'grams')
tw_phase = Entry(sp)
tw_phase.insert(0, 'angle')

lbl_ifc_mag = Label(sp, text='IFC')
ifc_mag = Entry(sp)
ifc_mag.insert(0, 'mm/s')
ifc_phase = Entry(sp)
ifc_phase.insert(0, 'degree')

lbl_cw = Label(sp, text='Correction Weight')
cw_w = Entry(sp)
cw_w.insert(0, 'grams')
cw_phase = Entry(sp)
cw_phase.insert(0, 'angle')


# Single plane calculation

def sp_calculate():
    # 1) Initial Run to complex form
    global im
    global ip
    im = float(ini_mag.get())
    ip = float(ini_phase.get())
    ini_com = mag2comp(im, ip)

    # 2) Trial run to complex form
    global trm
    global trp
    trm = float(tr_mag.get())
    trp = float(tr_phase.get())
    tr_com = mag2comp(trm, trp)

    # 3) Resultant run calculation
    t_com = tr_com - ini_com

    # 4) Influence coefficient calculation
    global twm
    global twp
    twm = float(tw_w.get())
    twp = float(tw_phase.get())
    global tma
    global tph
    tma = comp2mag(t_com)
    tph = comp2phase(t_com)
    ifc_m = twm / tma
    ifc_p = twp - tph
    if ifc_p >= 360:
        ifc_ph = ifc_p - 360
    else:
        ifc_ph = ifc_p
    ifc_mm = "{: .2f}".format(float(ifc_m))
    ifc_phh = "{: .2f}".format(float(ifc_ph))
    ifc_mag.insert(0, ifc_mm)
    ifc_phase.insert(0, ifc_phh)
    ifc_com = mag2comp(ifc_m, ifc_ph)

    # 5) Calculation of heavy spot
    hs_com = ini_com * ifc_com

    # 6) Correction weight
    global cwm
    global cwp
    cwm = comp2mag(hs_com)
    cwp = comp2phase(hs_com) + 180
    if cwp >= 360:
        cwph = cwp - 360
    else:
        cwph = cwp
    cwmm = "{: .2f}".format(float(cwm))
    cwphh = "{: .2f}".format(float(cwph))
    cw_w.insert(0, cwmm)
    cw_phase.insert(0, cwphh)
    ax.clear()
    ax.plot([0, ip * (2 * (3.14 / 360))], [0, im], 'bo-')
    ax.plot([0, trp * (2 * (3.14 / 360))], [0, trm], 'ro-')
    ax.plot([trp * (2 * (3.14 / 360)), ip * (2 * (3.14 / 360))], [trm, im], 'go-')

    # Defining plot inside the window
    chart_type1 = FigureCanvasTkAgg(fig, sp)
    chart_type1.get_tk_widget().grid(row=0, column=5, columnspan=3, rowspan=10, sticky="E")
    # plt.polar([0, ip * (2 * (3.14 / 360))], [0, im], 'bo-')
    # plt.polar([0, trp * (2 * (3.14 / 360))], [0, trm], 'ro-')
    # plt.polar([trp * (2 * (3.14 / 360)), ip * (2 * (3.14 / 360))], [trm, im], 'go-')
    # limit = np.max(np.ceil(np.absolute(ini_com)))  # set limits for axis
    # plt.show()


def plot():
    if im >= trm:
        cwm = im+2
    else:
        cwm = trm+2
    plt.figure()
    ay = plt.subplot(111, projection='polar')
    ay.plot([0, ip * (2 * (3.14 / 360))], [0, im], 'b-', lw=2, label="Initial Run (O)")
    ay.plot([0, trp * (2 * (3.14 / 360))], [0, trm], 'r-', lw=2, label="Trial Run(O+T)")
    ay.plot([trp * (2 * (3.14 / 360)), ip * (2 * (3.14 / 360))], [trm, im], 'g-', lw=2, label="Resultant Run (T)")
    ay.plot([0, tph * (2 * (3.14 / 360))], [0, tma], 'm--', lw=2, label="Projection vector")
    ay.plot([twp * (2 * (3.14 / 360))], [cwm], 'yo', lw=2, label="Trial Weight")
    ay.plot([cwp * (2 * (3.14 / 360))], [cwm], 'co', lw=2, label="Correction Weight")
    angle = np.deg2rad(67.5)
    ay.legend(loc="lower left", bbox_to_anchor=(.5 + np.cos(angle) / 2, .5 + np.sin(angle) / 2))
    # ay.set_thetagrids(-10)
    # ay.set_rlabel_position(-22.5)
    # thetaticks = np.arange(0, 360, 45)
    # ay.set_thetagrids(thetaticks, labels=None)
    plt.title("POLAR PLOT")
    #plt.grid(axis='x')
    
    plt.show()


def reset():
    ini_mag.delete(0, END)
    ini_phase.delete(0, END)
    tr_phase.delete(0, END)
    tr_mag.delete(0, END)
    tw_w.delete(0, END)
    tw_phase.delete(0, END)
    ifc_mag.delete(0, END)
    ifc_phase.delete(0, END)
    cw_w.delete(0, END)
    cw_phase.delete(0, END)


def help1():
    ini_mag.delete(0, END)
    ini_phase.delete(0, END)
    tr_phase.delete(0, END)
    tr_mag.delete(0, END)
    tw_w.delete(0, END)
    tw_phase.delete(0, END)
    ifc_mag.delete(0, END)
    ifc_phase.delete(0, END)
    cw_w.delete(0, END)
    cw_phase.delete(0, END)
    ini_mag.insert(0, 5.6)
    ini_phase.insert(0, 135)
    tr_phase.insert(0, 238)
    tr_mag.insert(0, 3.3)
    tw_w.insert(0, 74)
    tw_phase.insert(0, 315)


# GUI packing
# Configuration
root.rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=1)
root.columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
sp.rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
sp.columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
# Title
lbl_run.grid(row=1, column=0, padx=25, pady=10, sticky="NSEW")
lbl_mag.grid(row=1, column=1, padx=25, pady=10, sticky="NSEW")
lbl_phase.grid(row=1, column=2, padx=25, pady=10, sticky="NSEW")
# Data grid
lbl_ini_mag.grid(row=2, column=0, padx=25, pady=10, sticky="NSEW")
ini_mag.grid(row=2, column=1, padx=25, pady=10, sticky="NSEW")
ini_phase.grid(row=2, column=2, padx=25, pady=10, sticky="NSEW")

lbl_tr_mag.grid(row=3, column=0, padx=25, pady=10, sticky="NSEW")
tr_mag.grid(row=3, column=1, padx=25, pady=10, sticky="NSEW")
tr_phase.grid(row=3, column=2, padx=25, pady=10, sticky="NSEW")

lbl_tw.grid(row=4, column=0, padx=25, pady=10, sticky="NSEW")
tw_w.grid(row=4, column=1, padx=25, pady=10, sticky="NSEW")
tw_phase.grid(row=4, column=2, padx=25, pady=10, sticky="NSEW")

lbl_ifc_mag.grid(row=5, column=0, padx=25, pady=10, sticky="NSEW")
ifc_mag.grid(row=5, column=1, padx=25, pady=10, sticky="NSEW")
ifc_phase.grid(row=5, column=2, padx=25, pady=10, sticky="NSEW")

lbl_cw.grid(row=6, column=0, padx=25, pady=10, sticky="NSEW")
cw_w.grid(row=6, column=1, padx=25, pady=10, sticky="NSEW")
cw_phase.grid(row=6, column=2, padx=25, pady=10, sticky="NSEW")

button_single_plane = Button(sp, text="Calculate", padx=20, pady=5, cursor="hand2", command=sp_calculate)
button_single_plane.grid(row=7, column=2, padx=25, pady=10, sticky="NSEW")

button_plot = Button(sp, text="Graph", padx=20, pady=5, cursor="hand2", command=plot)
button_plot.grid(row=7, column=1, padx=25, pady=10, sticky="NSEW")

button_reset = Button(sp, text="Reset", padx=20, pady=5, cursor="hand2", command=reset)
button_reset.grid(row=7, column=0, padx=25, pady=10, sticky="NSEW")

button_help = Button(sp, text="Help", padx=20, pady=5, cursor="hand2", command=help1)
button_help.grid(row=8, column=1, padx=25, pady=10, sticky="NSEW")

# Polar plot
# Plot configuration
fig = Figure(figsize=(3.5, 3.5))
ax = fig.add_subplot(111, polar=True)
chart_type = FigureCanvasTkAgg(fig, sp)
chart_type.get_tk_widget().grid(row=0, column=5, columnspan=3, rowspan=10, sticky="E")
# ax = fig.add_subplot(111, polar = True)
# ax.plot([0, j], [0, i], 'bo-')
# ax.plot([0, 10], [0, 5], 'bo-', label='python')
# ax.set_rmin(0)
# ax.set_rmax(10)
# ax.set_thetalim(-np.pi, np.pi)
# ax.set_xticks(np.linspace(np.pi, -np.pi, 4, endpoint=False))
# ax.grid(True)
# ax.set_theta_direction(-1)
# ax.set_theta_zero_location("N")
root.resizable(True, True)
root.mainloop()
