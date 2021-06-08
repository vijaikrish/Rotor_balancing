from numpy import linspace, random
from scipy.optimize import leastsq
from numpy import exp, sin


def residual(variables, x, data, eps_data):
    """Model a decaying sine wave and subtract data."""
    amp = variables[0]
    phaseshift = variables[1]
    freq = variables[2]
    decay = variables[3]

    model = amp * sin(x * freq + phaseshift) * exp(-x * x * decay)

    return (data - model) / eps_data


# generate synthetic data with noise
x = linspace(0, 100)
eps_data = random.normal(size=x.size, scale=0.2)
print(eps_data)
data = 7.5 * sin(x * 0.22 + 2.5) * exp(-x * x * 0.01) + eps_data
print(data)
variables = [10.0, 0.2, 3.0, 0.007]
out = leastsq(residual, variables, args=(x, data, eps_data))
print(out)
