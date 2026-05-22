import sys
from pathlib import Path
import tempfile

import pandas as pd
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pfr.config import load_config, normalize_config  # noqa: E402
from pfr.processing import build_output_frame, load_final_frame  # noqa: E402


class ProcessingTest(unittest.TestCase):
    def test_final_number_accepts_l_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "realizado_l_prefix.csv"
            path.write_text(
                "Number,X,Y,Z,X_Toe,Y_Toe,Z_Toe,Length,Stemming,Diameter,Subdrilling,Angle,Azimuth,DetonatingTime,InputedCharge\n"
                "L-1,1,2,3,4,5,6,7,8,0.127,0.6,0,0,1000,9\n",
                encoding="utf-8",
            )
            df = load_final_frame(path)
            self.assertEqual(df["Number"].tolist(), [1])

    def test_missing_detonating_time_is_interpolated(self):
        cfg = normalize_config(load_config(ROOT / "config.yaml"), ROOT)
        merged = pd.DataFrame(
            {
                "Number": [1, 2, 3],
                "X": [10.0, 11.0, 12.0],
                "Y": [20.0, 21.0, 22.0],
                "Z": [30.0, 31.0, 32.0],
                "Z_Toe": [29.0, 30.0, 31.0],
                "p_length": [9.0, 9.0, 9.0],
                "r_length": [9.0, 9.0, 9.0],
                "p_stemming": [3.0, 3.0, 3.0],
                "r_stemming": [3.0, 3.0, 3.0],
                "p_subdrilling": [0.6, 0.6, 0.6],
                "r_subdrilling": [0.6, 0.6, 0.6],
                "r_azimuth": [0.0, 0.0, 0.0],
                "r_angle": [0.0, 0.0, 0.0],
                "p_explosive": [10.0, 10.0, 10.0],
                "r_explosive": [10.0, 10.0, 10.0],
                "Diameter_m": [0.127, 0.127, 0.127],
                "DetonatingTime": [1000.0, float("nan"), 1300.0],
            }
        )

        data = build_output_frame(merged, "1234567", "30/04/2026", "06:04:41", cfg)

        self.assertEqual(data["tempo detonacao (ms)"].tolist(), [1000, 1150, 1300])
        self.assertEqual(str(data["tempo detonacao (ms)"].dtype), "Int64")
        self.assertEqual(merged.attrs["imputed_detonating_time_count"], 1)

    def test_stemming_variation_is_deterministic_and_bounded(self):
        cfg = normalize_config(load_config(ROOT / "config.yaml"), ROOT)
        merged = pd.DataFrame(
            {
                "Number": [10, 11, 12],
                "X": [10.0, 11.0, 12.0],
                "Y": [20.0, 21.0, 22.0],
                "Z": [30.0, 31.0, 32.0],
                "Z_Toe": [29.0, 30.0, 31.0],
                "p_length": [9.0, 9.0, 9.0],
                "r_length": [9.0, 9.0, 9.0],
                "p_stemming": [3.0, 3.0, 3.0],
                "r_stemming": [3.0, 3.0, 3.0],
                "p_subdrilling": [0.6, 0.6, 0.6],
                "r_subdrilling": [0.6, 0.6, 0.6],
                "r_azimuth": [0.0, 0.0, 0.0],
                "r_angle": [0.0, 0.0, 0.0],
                "p_explosive": [10.0, 10.0, 10.0],
                "r_explosive": [10.0, 10.0, 10.0],
                "Diameter_m": [0.127, 0.127, 0.127],
                "DetonatingTime": [1000.0, 1100.0, 1200.0],
            }
        )

        first = build_output_frame(merged.copy(), "1234567", "30/04/2026", "06:04:41", cfg)
        second = build_output_frame(merged.copy(), "1234567", "30/04/2026", "06:04:41", cfg)

        self.assertEqual(first["tampao realizado"].tolist(), second["tampao realizado"].tolist())
        for value in first["tampao realizado"]:
            self.assertGreaterEqual(value, 2.88)
            self.assertLessEqual(value, 3.12)
