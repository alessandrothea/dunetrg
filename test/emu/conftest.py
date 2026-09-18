import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_tps():
    rng = np.random.default_rng(1)
    n = 300
    return pd.DataFrame({
        "readout_view":           np.tile([0, 1, 2], n // 3),
        "bt_is_signal":           np.repeat([0, 1], n // 2),
        "channel":                rng.integers(0, 480, n),
        "sample_peak":            rng.integers(0, 6000, n),
        "adc_peak":               rng.integers(10, 200, n),
        "adc_integral":           rng.integers(50, 1000, n),
        "samples_over_threshold": rng.integers(1, 20, n),
    })
