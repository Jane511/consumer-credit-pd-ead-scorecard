
import numpy as np
import pandas as pd

def psi(expected, actual, eps=1e-6):
    expected = np.where(expected == 0, eps, expected)
    actual = np.where(actual == 0, eps, actual)
    return np.sum((actual - expected) * np.log(actual / expected))

def psi_table(expected_counts, actual_counts):
    expected_dist = expected_counts / expected_counts.sum()
    actual_dist = actual_counts / actual_counts.sum()
    psi_val = psi(expected_dist, actual_dist)
    return psi_val
