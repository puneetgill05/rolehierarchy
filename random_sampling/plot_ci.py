import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats

# Parameters
true_p = 0.6            # true population proportion
n = 100                 # sample size
num_samples = 100       # number of repeated samples
confidence = 0.95
z = stats.norm.ppf(1 - (1 - confidence)/2)

# Generate intervals
np.random.seed(42)
intervals = []
contains_true_p = []

for _ in range(num_samples):
    sample = np.random.binomial(1, true_p, n)
    p_hat = sample.mean()
    margin = z * np.sqrt(p_hat * (1 - p_hat) / n)
    lower = p_hat - margin
    upper = p_hat + margin
    intervals.append((lower, upper))
    contains_true_p.append(lower <= true_p <= upper)

# Plot
plt.figure(figsize=(10, 8))
for i, (low, high) in enumerate(intervals):
    color = 'green' if contains_true_p[i] else 'red'
    plt.plot([low, high], [i, i], color=color, linewidth=2)
    plt.plot(true_p, i, 'ko', markersize=3)

plt.axvline(true_p, color='black', linestyle='--', label=f"True p = {true_p}")
plt.xlabel("Proportion")
plt.ylabel("Sample index")
plt.title(f"{num_samples} Repeated Samples — {int(confidence*100)}% Confidence Intervals")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
