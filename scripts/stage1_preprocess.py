import os
import numpy as np
import pandas as pd

# =====================================================
# PATHS
# =====================================================

INPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\Lucknow_MERGED_Daily"

OUTPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\lucknow_worked\04_STAGE1_PREPROCESSED"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================================================
# GLOBAL STATISTICS
# =====================================================

successful_files = 0
failed_files = []

total_duplicates = 0
total_datetime_errors = 0
total_cells_repaired = 0
total_rows_repaired = 0

# =====================================================
# FIND FILES
# =====================================================

all_files = []

for root, dirs, files in os.walk(INPUT_DIR):

    for f in files:

        if f.lower().endswith(".csv"):

            all_files.append(
                os.path.join(root, f)
            )

all_files.sort()

print("\nFILES FOUND:", len(all_files))

# =====================================================
# PROCESS FILES
# =====================================================

for index, file_path in enumerate(all_files, start=1):

    file_name = os.path.basename(file_path)

    print("\n" + "=" * 80)
    print(f"[{index}/{len(all_files)}]")
    print(file_name)
    print(
        f"Progress : {(index / len(all_files)) * 100:.2f}%"
    )
    print("=" * 80)

    try:

        # =================================================
        # LOAD FILE
        # =================================================

        df = pd.read_csv(
            file_path,
            low_memory=False
        )

        rows_before = len(df)

        # =================================================
        # CREATE DATETIME
        # =================================================

        df["Datetime"] = pd.to_datetime(
            df["Date"].astype(str)
            + " "
            + df["Time"].astype(str),
            dayfirst=True,
            errors="coerce"
        )

        datetime_errors = (
            df["Datetime"]
            .isna()
            .sum()
        )

        total_datetime_errors += (
            datetime_errors
        )

        df = df.dropna(
            subset=["Datetime"]
        )

        # =================================================
        # SORT
        # =================================================

        df = df.sort_values(
            "Datetime"
        )

        # =================================================
        # REMOVE DUPLICATES
        # =================================================

        duplicates = (
            len(df)
            -
            len(
                df.drop_duplicates(
                    subset=["Datetime"]
                )
            )
        )

        total_duplicates += duplicates

        df = df.drop_duplicates(
            subset=["Datetime"]
        )

        # =================================================
        # USE DATETIME AS INDEX
        # =================================================

        df = df.set_index(
            "Datetime"
        )

        # =================================================
        # DROP DATE/TIME
        # =================================================

        cols_to_drop = []

        if "Date" in df.columns:
            cols_to_drop.append("Date")

        if "Time" in df.columns:
            cols_to_drop.append("Time")

        if len(cols_to_drop) > 0:

            df.drop(
                columns=cols_to_drop,
                inplace=True
            )

        # =================================================
        # DROP PRESENT WEATHER
        # =================================================

        if (
            "PW_Present_Weather_Code"
            in df.columns
        ):

            df.drop(
                columns=[
                    "PW_Present_Weather_Code"
                ],
                inplace=True
            )

        # =================================================
        # NUMERIC CONVERSION
        # =================================================

        for col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        # =================================================
        # SINGLE MISSING CELL REPAIR
        # =================================================

        cells_repaired = 0

        for col in df.columns:

            s = df[col]

            repair_mask = (

                s.isna()
                &
                s.shift(1).notna()
                &
                s.shift(-1).notna()

            )

            repaired = int(
                repair_mask.sum()
            )

            if repaired > 0:

                df.loc[
                    repair_mask,
                    col
                ] = s.shift(1)

                cells_repaired += repaired

        total_cells_repaired += (
            cells_repaired
        )

        # =================================================
        # SINGLE COMPLETELY EMPTY ROW REPAIR
        # =================================================

        empty_mask = (
            df.isna().all(axis=1)
        )

        repair_mask = (

            empty_mask
            &
            (
                ~empty_mask.shift(
                    1,
                    fill_value=True
                )
            )
            &
            (
                ~empty_mask.shift(
                    -1,
                    fill_value=True
                )
            )

        )

        rows_repaired = int(
            repair_mask.sum()
        )

        if rows_repaired > 0:

            df.loc[
                repair_mask
            ] = (
                df.shift(1)
                .loc[
                    repair_mask
                ]
                .values
            )

        total_rows_repaired += (
            rows_repaired
        )

        # =================================================
        # CYCLICAL TIME FEATURES
        # =================================================

        decimal_hour = (

            df.index.hour
            +
            df.index.minute / 60
            +
            df.index.second / 3600

        )

        df["Hour_Sin"] = np.sin(
            2
            * np.pi
            * decimal_hour
            / 24
        ).round(2)

        df["Hour_Cos"] = np.cos(
            2
            * np.pi
            * decimal_hour
            / 24
        ).round(2)

        # =================================================
        # RESTORE DATETIME COLUMN
        # =================================================

        df = df.reset_index()

        cols = (
            ["Datetime"]
            +
            [
                c
                for c in df.columns
                if c != "Datetime"
            ]
        )

        df = df[cols]

        # =================================================
        # SAVE
        # =================================================

        rel_path = os.path.relpath(
            file_path,
            INPUT_DIR
        )

        out_file = os.path.join(
            OUTPUT_DIR,
            rel_path
        )

        os.makedirs(
            os.path.dirname(
                out_file
            ),
            exist_ok=True
        )

        df.to_csv(
            out_file,
            index=False
        )

        if os.path.exists(
            out_file
        ):

            successful_files += 1

        else:

            raise Exception(
                "File was not written to disk."
            )

        # =================================================
        # PROGRESS OUTPUT
        # =================================================

        print(
            "Rows Loaded            :",
            rows_before
        )

        print(
            "Rows Saved             :",
            len(df)
        )

        print(
            "Datetime Errors        :",
            datetime_errors
        )

        print(
            "Duplicates Removed     :",
            duplicates
        )

        print(
            "Cells Repaired         :",
            cells_repaired
        )

        print(
            "Rows Repaired          :",
            rows_repaired
        )

        print(
            "Saved Successfully"
        )

    except Exception as e:

        failed_files.append({

            "File": file_name,
            "Path": file_path,
            "Error": str(e)

        })

        print(
            "FAILED:",
            file_name
        )

        print(
            "ERROR:",
            str(e)
        )

# =====================================================
# SAVE FAILED FILE REPORT
# =====================================================

if len(failed_files) > 0:

    pd.DataFrame(
        failed_files
    ).to_csv(

        os.path.join(
            OUTPUT_DIR,
            "failed_files.csv"
        ),

        index=False
    )

# =====================================================
# FINAL SUMMARY
# =====================================================

print("\n" + "=" * 80)
print("STAGE 1 COMPLETE")
print("=" * 80)

print(
    "Files Found            :",
    len(all_files)
)

print(
    "Files Saved            :",
    successful_files
)

print(
    "Files Failed           :",
    len(failed_files)
)

print(
    "Datetime Errors        :",
    total_datetime_errors
)

print(
    "Duplicates Removed     :",
    total_duplicates
)

print(
    "Cells Repaired         :",
    total_cells_repaired
)

print(
    "Rows Repaired          :",
    total_rows_repaired
)

if len(failed_files) > 0:

    print(
        "\nFailed file report:"
    )

    print(
        os.path.join(
            OUTPUT_DIR,
            "failed_files.csv"
        )
    )

print("\nOutput Folder:")
print(OUTPUT_DIR)

print("=" * 80)