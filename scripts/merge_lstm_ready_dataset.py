import os
from typing import List, Set

import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(
    BASE_DIR,
    "lucknow_worked",
    "07_LSTM_READY_DATA",
)
OUTPUT_FILE = os.path.join(
    INPUT_DIR,
    "lucknow_unified_lstm_dataset_aug2024_dec2025.csv",
)
SUMMARY_FILE = os.path.join(
    INPUT_DIR,
    "lucknow_unified_lstm_dataset_summary.csv",
)

START_DATE = pd.Timestamp("2024-08-01 00:00:00")
END_DATE = pd.Timestamp("2026-01-01 00:00:00")

REPORT_FILES = {
    "dataset_summary.csv",
    "uniformity_report.csv",
    "failed_files.csv",
    "lucknow_unified_lstm_dataset_summary.csv",
    "lucknow_unified_lstm_dataset_aug2024_dec2025.csv",
}


def find_data_files() -> List[str]:
    """Return daily stage-4 data files in deterministic chronological order."""
    data_files: List[str] = []

    for root, _, files in os.walk(INPUT_DIR):
        for file_name in files:
            if (
                file_name.lower().endswith(".csv")
                and file_name.lower() not in REPORT_FILES
            ):
                data_files.append(os.path.join(root, file_name))

    def file_date_key(file_path: str) -> tuple:
        file_stem = os.path.splitext(os.path.basename(file_path))[0]
        file_date = pd.to_datetime(
            file_stem,
            format="%Y_%b_%d",
            errors="coerce",
        )
        if pd.isna(file_date):
            return (pd.Timestamp.max, file_path)
        return (file_date, file_path)

    return sorted(data_files, key=file_date_key)


def discover_columns(data_files: List[str]) -> List[str]:
    """Build the union of columns while retaining first-seen column order."""
    columns: List[str] = []
    known_columns: Set[str] = set()

    for file_path in data_files:
        header = pd.read_csv(file_path, nrows=0)
        for column in header.columns:
            if column not in known_columns:
                known_columns.add(column)
                columns.append(column)

    if "Datetime" not in known_columns:
        raise ValueError("No input file contains the required 'Datetime' column.")

    return ["Datetime"] + [column for column in columns if column != "Datetime"]


def sort_unified_output() -> None:
    """Sort the completed CSV by actual timestamps, not folder or file names."""
    df = pd.read_csv(OUTPUT_FILE, low_memory=False)
    df["Datetime"] = pd.to_datetime(
        df["Datetime"],
        errors="raise",
    )
    df = df.sort_values("Datetime", kind="mergesort")
    df["Datetime"] = df["Datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(OUTPUT_FILE, index=False)


def merge_dataset() -> None:
    if not os.path.isdir(INPUT_DIR):
        raise FileNotFoundError(
            f"Input directory does not exist: {INPUT_DIR}"
        )

    data_files = find_data_files()
    if not data_files:
        raise FileNotFoundError(
            f"No daily CSV files were found in: {INPUT_DIR}"
        )

    columns = discover_columns(data_files)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    seen_timestamps: Set[int] = set()
    first_write = True
    files_processed = 0
    files_failed = 0
    rows_read = 0
    rows_in_range = 0
    duplicate_rows = 0
    invalid_datetime_rows = 0
    output_rows = 0
    failures = []

    for file_number, file_path in enumerate(data_files, start=1):
        file_name = os.path.relpath(file_path, INPUT_DIR)
        print(f"[{file_number}/{len(data_files)}] {file_name}")

        try:
            df = pd.read_csv(file_path, low_memory=False)
            files_processed += 1
            rows_read += len(df)

            if "Datetime" not in df.columns:
                raise ValueError("Missing required 'Datetime' column")

            parsed_datetime = pd.to_datetime(
                df["Datetime"],
                dayfirst=True,
                errors="coerce",
            )
            invalid_datetime_rows += int(parsed_datetime.isna().sum())

            in_range = (
                parsed_datetime.notna()
                & (parsed_datetime >= START_DATE)
                & (parsed_datetime < END_DATE)
            )
            df = df.loc[in_range].copy()
            parsed_datetime = parsed_datetime.loc[in_range]
            rows_in_range += len(df)

            if df.empty:
                continue

            # Use nanosecond integers for compact, exact cross-file deduplication.
            timestamp_keys = parsed_datetime.astype("int64")
            unique_mask = ~timestamp_keys.isin(seen_timestamps)
            duplicate_rows += int((~unique_mask).sum())
            df = df.loc[unique_mask].copy()
            parsed_datetime = parsed_datetime.loc[unique_mask]
            timestamp_keys = timestamp_keys.loc[unique_mask]

            if df.empty:
                continue

            seen_timestamps.update(timestamp_keys.tolist())
            df["Datetime"] = parsed_datetime
            df = df.reindex(columns=columns)
            df = df.sort_values("Datetime")
            df["Datetime"] = df["Datetime"].dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            df.to_csv(
                OUTPUT_FILE,
                mode="w" if first_write else "a",
                header=first_write,
                index=False,
            )
            first_write = False
            output_rows += len(df)

        except Exception as error:
            files_failed += 1
            failures.append(
                {
                    "File": file_name,
                    "Error": str(error),
                }
            )
            print(f"FAILED: {file_name}: {error}")

    if first_write:
        raise RuntimeError(
            "No rows remained after parsing and date filtering; "
            "the unified dataset was not created."
        )

    sort_unified_output()

    summary = pd.DataFrame(
        [
            {
                "Input_Directory": INPUT_DIR,
                "Output_File": OUTPUT_FILE,
                "Start_Date_Inclusive": START_DATE,
                "End_Date_Exclusive": END_DATE,
                "Files_Discovered": len(data_files),
                "Files_Processed": files_processed,
                "Files_Failed": files_failed,
                "Rows_Read": rows_read,
                "Rows_In_Date_Range": rows_in_range,
                "Invalid_Datetime_Rows": invalid_datetime_rows,
                "Duplicate_Timestamp_Rows_Removed": duplicate_rows,
                "Rows_Written": output_rows,
                "Columns_Written": len(columns),
                "Column_Names": ", ".join(columns),
            }
        ]
        + failures
    )
    summary.to_csv(SUMMARY_FILE, index=False)

    print("\nUNIFIED DATASET CREATED")
    print(f"Output : {OUTPUT_FILE}")
    print(f"Rows   : {output_rows:,}")
    print(f"Columns: {len(columns)}")
    print(f"Summary: {SUMMARY_FILE}")


if __name__ == "__main__":
    merge_dataset()
