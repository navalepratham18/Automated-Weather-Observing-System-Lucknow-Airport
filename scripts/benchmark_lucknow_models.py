"""Compare non-range-aware forecasting models with the Lucknow LSTM setup.

The script uses the same unified dataset, targets, chronological split,
one-step horizon, and 96-row history as ``train_lucknow_lstm.ipynb``.

It creates compact tabular features from each 96-row history:
the latest value, rolling mean, and rolling standard deviation for every
numeric input feature. This avoids materialising a 96 x feature_count
flattened matrix for the 2.5M-row dataset while retaining recent-history
information for classical models.

Example:
    python benchmark_lucknow_models.py
    python benchmark_lucknow_models.py --max-train-rows 150000
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


SEED = 42
LOOKBACK = 96
HORIZON = 1
TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TARGET_COLUMNS = ["CLOUD_Vertical_Visibility", "VIS_Visibility_MOR"]
TIMESTAMP_COLUMN = "Datetime"

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILE = (
    BASE_DIR
    / "lucknow_worked"
    / "07_LSTM_READY_DATA"
    / "lucknow_unified_lstm_dataset_aug2024_dec2025.csv"
)
DEFAULT_RESULTS_DIR = BASE_DIR / "result" / "benchmark_lucknow_models"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=150_000,
        help="Maximum chronological training rows used by fitted models. "
        "Use 0 for all training rows.",
    )
    return parser.parse_args()


def load_dataset(path: Path) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    frame = pd.read_csv(path, low_memory=False)
    frame[TIMESTAMP_COLUMN] = pd.to_datetime(frame[TIMESTAMP_COLUMN], errors="coerce")
    frame = (
        frame.dropna(subset=[TIMESTAMP_COLUMN] + TARGET_COLUMNS)
        .drop_duplicates(subset=[TIMESTAMP_COLUMN])
        .sort_values(TIMESTAMP_COLUMN)
        .reset_index(drop=True)
    )

    numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
    feature_columns = [column for column in numeric_columns if frame[column].notna().any()]
    missing_targets = [column for column in TARGET_COLUMNS if column not in feature_columns]
    if missing_targets:
        raise ValueError(f"Missing numeric target columns: {missing_targets}")

    train_end = int(len(frame) * TRAIN_RATIO)
    train_medians = frame.iloc[:train_end][feature_columns].median().fillna(0.0)
    frame[feature_columns] = (
        frame[feature_columns]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(train_medians)
    )
    if not np.isfinite(frame[feature_columns].to_numpy(dtype=np.float64)).all():
        raise ValueError("Non-finite feature values remain after training-only imputation.")
    return frame, feature_columns


def make_history_features(
    features: np.ndarray,
    targets: np.ndarray,
    lookback: int,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return latest/mean/std history features, targets, and persistence values."""
    first_target = lookback + horizon - 1
    if len(features) <= first_target:
        raise ValueError("Split is shorter than LOOKBACK + HORIZON.")

    values = features.astype(np.float64, copy=False)
    prefix_sum = np.vstack(
        [np.zeros((1, values.shape[1])), np.cumsum(values, axis=0)]
    )
    prefix_sq_sum = np.vstack(
        [np.zeros((1, values.shape[1])), np.cumsum(values * values, axis=0)]
    )
    starts = np.arange(0, len(values) - first_target, dtype=np.int64)
    ends = starts + lookback
    counts = float(lookback)
    sums = prefix_sum[ends] - prefix_sum[starts]
    squared_sums = prefix_sq_sum[ends] - prefix_sq_sum[starts]
    means = sums / counts
    variances = np.maximum(squared_sums / counts - means * means, 0.0)
    latest = values[ends - 1]

    x = np.concatenate([latest, means, np.sqrt(variances)], axis=1).astype(np.float32)
    y = targets[first_target : first_target + len(x)].astype(np.float32, copy=False)
    persistence = targets[ends - 1].astype(np.float32, copy=False)
    return x, y, persistence


def make_models() -> dict[str, object]:
    return {
        "linear_regression": make_pipeline(StandardScaler(), LinearRegression()),
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            max_features=1.0,
            n_jobs=-1,
            random_state=SEED,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            max_features=1.0,
            n_jobs=-1,
            random_state=SEED,
        ),
        "hist_gradient_boosting": MultiOutputRegressor(
            HistGradientBoostingRegressor(
                max_iter=150,
                learning_rate=0.08,
                l2_regularization=1.0,
                random_state=SEED,
            )
        ),
    }


def metric_rows(
    model_name: str,
    split_name: str,
    actual: np.ndarray,
    predicted: np.ndarray,
) -> list[dict[str, object]]:
    rows = []
    for index, target in enumerate(TARGET_COLUMNS):
        rows.append(
            {
                "model": model_name,
                "split": split_name,
                "target": target,
                "MAE": mean_absolute_error(actual[:, index], predicted[:, index]),
                "RMSE": mean_squared_error(actual[:, index], predicted[:, index]) ** 0.5,
                "R2": r2_score(actual[:, index], predicted[:, index]),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    np.random.seed(SEED)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    frame, feature_columns = load_dataset(args.data_file)
    n_rows = len(frame)
    train_end = int(n_rows * TRAIN_RATIO)
    validation_end = int(n_rows * (TRAIN_RATIO + VALIDATION_RATIO))
    splits = {
        "train": frame.iloc[:train_end],
        "validation": frame.iloc[train_end:validation_end],
        "test": frame.iloc[validation_end:],
    }

    transformed = {}
    for name, split in splits.items():
        transformed[name] = make_history_features(
            split[feature_columns].to_numpy(),
            split[TARGET_COLUMNS].to_numpy(),
            LOOKBACK,
            HORIZON,
        )

    train_x, train_y, _ = transformed["train"]
    validation_x, validation_y, validation_persistence = transformed["validation"]
    test_x, test_y, test_persistence = transformed["test"]

    if args.max_train_rows > 0 and len(train_x) > args.max_train_rows:
        train_x = train_x[-args.max_train_rows :]
        train_y = train_y[-args.max_train_rows :]

    results: list[dict[str, object]] = []
    results.extend(metric_rows("persistence", "validation", validation_y, validation_persistence))
    results.extend(metric_rows("persistence", "test", test_y, test_persistence))

    train_mean = train_y.mean(axis=0)
    results.extend(
        metric_rows(
            "training_mean",
            "validation",
            validation_y,
            np.broadcast_to(train_mean, validation_y.shape),
        )
    )
    results.extend(
        metric_rows(
            "training_mean",
            "test",
            test_y,
            np.broadcast_to(train_mean, test_y.shape),
        )
    )

    for model_name, model in make_models().items():
        print(f"Fitting {model_name} on {len(train_x):,} rows...")
        started = time.perf_counter()
        model.fit(train_x, train_y)
        elapsed = time.perf_counter() - started
        print(f"  fit_seconds={elapsed:.1f}")
        validation_prediction = np.asarray(model.predict(validation_x))
        test_prediction = np.asarray(model.predict(test_x))
        results.extend(metric_rows(model_name, "validation", validation_y, validation_prediction))
        results.extend(metric_rows(model_name, "test", test_y, test_prediction))

    metrics = pd.DataFrame(results)
    metrics = metrics.sort_values(["split", "target", "RMSE"]).reset_index(drop=True)
    metrics.to_csv(args.results_dir / "model_comparison_metrics.csv", index=False)
    test_metrics = metrics[metrics["split"] == "test"].copy()
    test_metrics.sort_values(["target", "RMSE"]).to_csv(
        args.results_dir / "test_metrics_ranked.csv", index=False
    )

    best = test_metrics.loc[test_metrics.groupby("target")["RMSE"].idxmin()]
    print("\nBest test model by target:")
    print(best[["target", "model", "MAE", "RMSE", "R2"]].to_string(index=False))
    print(f"\nSaved results to: {args.results_dir}")


if __name__ == "__main__":
    main()
