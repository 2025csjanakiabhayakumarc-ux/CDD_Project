"""Evaluate anomaly detection precision and recall on employees.csv.

Copies the sample file, plants 10 known outliers, runs the anomalies rule
and prints precision/recall so the numbers can be quoted in a viva.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

from src.anomalies import check
from src.loader import load_csv

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "employees.csv"
NUM_OUTLIERS = 10


def main() -> None:
    folder = Path(tempfile.mkdtemp(prefix="eval_anomaly_"))
    try:
        path = folder / "employees_eval.csv"
        shutil.copy(SAMPLES, path)
        df = load_csv(str(path))

        # Remove the existing duplicate so we have clean base rows
        df = df.drop_duplicates(subset=["emp_id"]).reset_index(drop=True)

        original_len = len(df)

        # Plant 10 outliers with extreme salaries
        outlier_indices = set()
        for i in range(NUM_OUTLIERS):
            new_row = {
                "emp_id": f"X{i:03d}",
                "name": f"Outlier {i}",
                "email": f"outlier{i}@test.com",
                "phone": "9876500000",
                "join_date": "2024-01-01",
                "salary": 9_000_000 + i * 500_000,  # 9M–13.5M vs typical 48K–71K
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            outlier_indices.add(original_len + i)

        print(f"Dataset: {len(df)} rows ({original_len} original + {NUM_OUTLIERS} planted outliers)")
        print(f"Planted outlier rows: {sorted(outlier_indices)}")
        print()

        actual_contamination = NUM_OUTLIERS / len(df)
        findings = check(df, numeric_columns=["salary"], contamination=actual_contamination)
        flagged_rows = {f.row for f in findings}
        print(f"Flagged rows: {sorted(flagged_rows)}")
        print()

        true_positives = flagged_rows & outlier_indices
        false_positives = flagged_rows - outlier_indices
        false_negatives = outlier_indices - flagged_rows

        precision = len(true_positives) / len(flagged_rows) if flagged_rows else 0.0
        recall = len(true_positives) / len(outlier_indices) if outlier_indices else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        print(f"True positives:  {len(true_positives)}")
        print(f"False positives: {len(false_positives)}")
        print(f"False negatives: {len(false_negatives)}")
        print()
        print(f"Precision: {precision:.2%}")
        print(f"Recall:    {recall:.2%}")
        print(f"F1 score:  {f1:.2%}")

        for f in findings:
            tag = "TP" if f.row in outlier_indices else "FP"
            print(f"  [{tag}] row {f.row}: {f.message}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()
