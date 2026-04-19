import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


plt.style.use('ggplot')
sns.set_palette("colorblind")  # set a nice ggplot-like color palette

# Define the function
def f(x, E):
    return E - x - E / x

# Set parameters and range
E = 48
x = np.linspace(0.7, E+2, 400)  # avoid x=0 to prevent division by zero

# Compute function values
y = f(x, E)

# Plot
plt.figure(figsize=(8, 5))
plt.plot(x, y, label=r'$f(u) = E - u - \frac{E}{u}$')
# plt.axhline(0, color='gray', linestyle='--', linewidth=0.8)
# plt.axvline(0, color='gray', linestyle='--', linewidth=0.8)
plt.axvline(np.sqrt(E), color='black', linestyle='--', label='Maximum at $u = \sqrt{E}$ = ' + str(round(
    np.sqrt(E), 2)))
# plt.axvline(6, color='green', linestyle='--', label='Integral solution with maximum at $u = 6$')
# plt.axvline(E/6, color='green', linestyle='--', label='Integral solution with maximum at $E/u = 8$')

# plt.axvline(1, color='blue', linestyle='--', label='Integral solution with maximum at $x = 2$')
# plt.axvline(E, color='blue', linestyle='--', label='Integral solution with maximum at $x = 2$')
# plt.axvline(3, color='gray', linestyle='--', label='Integral solution with maximum at $x = 2$')
# plt.axvline(E/3, color='gray', linestyle='--', label='Integral solution with maximum at $x = 2$')

plt.fill_between(x, y, where=(x > 6) & (x < E/6), color='gold', alpha=0.9, label='Integral bounds with maximum value')

plt.fill_between(x, y, where=(x > 1) & (x <= 6), color='black', alpha=0.25, label='Bounds for all integral solutions')
plt.fill_between(x, y, where=(x >= 8) & (x < E), color='black', alpha=0.25, label='Bounds for all integral solutions')

plt.title('Plot of $f(u) = E - u - \\frac{E}{u}$ for E = 48')
plt.xlabel('u')
plt.ylabel('f(u)')
plt.grid(True)
plt.legend()
plt.show()
