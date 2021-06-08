import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Arc
Arc = matplotlib.patches.Arc


def halfangle(a, b):
    "Gets the middle angle between a and b, when increasing from a to b"
    if b < a:
        b += 360
    return (a + b) / 2 % 360


def get_arc_patch(lines, radius=None, flip=False, obtuse=False, reverse=False, dec=0, fontsize=8):
    """For two sets of two points, create a matplotlib Arc patch drawing
    an arc between the two lines.

    lines: list of lines, of shape [[(x0, y0), (x1, y1)], [(x0, y0), (x1, y1)]]
    radius: None, float or tuple of floats. If None, is set to half the length
    of the shortest line
    orgio: If True, draws the arc around the point (0,0). If False, estimates
    the intersection of the lines and uses that point.
    flip: If True, flips the arc to the opposite side by 180 degrees
    obtuse: If True, uses the other set of angles. Often used with reverse=True.
    reverse: If True, reverses the two angles so that the arc is drawn
    "the opposite way around the circle"
    dec: The number of decimals to round to
    fontsize: fontsize of the angle label
    """
    import numpy as np
    from matplotlib.patches import Arc

    linedata = [np.array(line.T) for line in lines]
    scales = [np.diff(line).T[0] for line in linedata]
    scales = [s[1] / s[0] for s in scales]

    # Get angle to horizontal
    angles = np.array([np.rad2deg(np.arctan(s / 1)) for s in scales])
    if obtuse:
        angles[1] = angles[1] + 180
    if flip:
        angles += 180
    if reverse:
        angles = angles[::-1]

    angle = abs(angles[1] - angles[0])

    if radius is None:
        lengths = np.linalg.norm(lines, axis=(0, 1))
        radius = min(lengths) / 2

    # Solve the point of intersection between the lines:
    t, s = np.linalg.solve(np.array([line1[1] - line1[0], line2[0] - line2[1]]).T, line2[0] - line1[0])
    intersection = np.array((1 - t) * line1[0] + t * line1[1])
    # Check if radius is a single value or a tuple
    try:
        r1, r2 = radius
    except:
        r1 = r2 = radius
    arc = Arc(intersection, 2 * r1, 2 * r2, theta1=angles[1], theta2=angles[0])

    half = halfangle(*angles[::-1])
    sin = np.sin(np.deg2rad(half))
    cos = np.cos(np.deg2rad(half))

    r = r1 * r2 / (r1 ** 2 * sin ** 2 + r2 ** 2 * cos ** 2) ** 0.5
    xy = np.array((r * cos, r * sin))
    xy = intersection + xy / 2

    textangle = half if half > 270 or half < 90 else 180 + half
    textkwargs = {
        'x': xy[0],
        'y': xy[1],
        's': str(round(angle, dec)) + "°",
        'ha': 'center',
        'va': 'center',
        'fontsize': fontsize,
        'rotation': textangle
    }
    return arc, textkwargs

# lines are formatted like this: [(x0, y0), (x1, y1)]
line1 = np.array([(1,-2), (3,2)])
line2 = np.array([(2,2), (2,-2)])
lines = [line1, line2]

fig, AX = plt.subplots(nrows=2, ncols=2)
for ax in AX.flatten():
    for line in lines:
        x,y = line.T
        ax.plot(x,y)
        ax.axis('equal')

ax1, ax2, ax3, ax4 = AX.flatten()

arc, angle_text = get_arc_patch(lines)
ax1.add_artist(arc)
ax1.set(title='Default')
ax1.text(**angle_text)

arc, angle_text = get_arc_patch(lines, flip=True)
ax2.add_artist(arc)
ax2.set(title='flip=True')
ax2.text(**angle_text)

arc, angle_text = get_arc_patch(lines, obtuse=True, reverse=True)
ax3.add_artist(arc)
ax3.set(title='obtuse=True, reverse=True')
ax3.text(**angle_text)

arc, angle_text = get_arc_patch(lines, radius=(2,1))
ax4.add_artist(arc)
ax4.set(title='radius=(2,1)')
ax4.text(**angle_text)
plt.tight_layout()
plt.show()