import os
import numpy as np
import pandas as pd

# =====================================================
# PATHS
# =====================================================

INPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\lucknow_worked\04_STAGE1_PREPROCESSED"

OUTPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\lucknow_worked\05_STAGE2_FLAGGED"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================================================
# CONSTANTS
# =====================================================

MAX_GAP_MINUTES = 5
MAX_GAP_ROWS = 20

PTU_THRESHOLDS = {
    "PTU_Temperature": 0.5,
    "PTU_DewPoint": 0.5,
    "PTU_Humidity": 5.0,
    "PTU_Pressure_QNH": 2.0
}

PTU_COLS = list(
    PTU_THRESHOLDS.keys()
)

# =====================================================
# AUDITS
# =====================================================

gap_audit = []
threshold_audit = []
flagged_files = []

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
# LOOP
# =====================================================

for file_no, file_path in enumerate(
        all_files,
        start=1
):

    file_name = os.path.basename(
        file_path
    )

    print("\n" + "=" * 80)
    print(
        f"[{file_no}/{len(all_files)}]"
    )
    print(file_name)
    print(
        f"Progress : "
        f"{100*file_no/len(all_files):.2f}%"
    )
    print("=" * 80)

    try:

        # =============================================
        # LOAD
        # =============================================

        df = pd.read_csv(
            file_path,
            low_memory=False
        )

        rows_before = len(df)

        # =============================================
        # DATETIME
        # =============================================

        if "Datetime" in df.columns:

            df["Datetime"] = pd.to_datetime(
                df["Datetime"],
                errors="coerce"
            )

        else:

            df["Datetime"] = pd.to_datetime(
                df["Date"].astype(str)
                + " "
                + df["Time"].astype(str),
                dayfirst=True,
                errors="coerce"
            )

        df = df.dropna(
            subset=["Datetime"]
        )

        df = df.sort_values(
            "Datetime"
        )

        df = df.set_index(
            "Datetime"
        )

        # =============================================
        # NUMERIC CONVERSION
        # =============================================

        numeric_cols = (
            df.columns
            .difference(
                [
                    "Datetime",
                    "Date",
                    "Time"
                ]
            )
        )

        df[numeric_cols] = (
            df[numeric_cols]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )
        )


        # =============================================
        # PTU RESOLUTION CONVERSION
        # =============================================

        ptu_interpolated = 0

        for col in PTU_COLS:

            if col not in df.columns:
                continue

            before = (
                df[col]
                .isna()
                .sum()
            )

            df[col] = (
                df[col]
                .interpolate(
                    method="time",
                    limit=3
                )
                .round(2)
            )

            after = (
                df[col]
                .isna()
                .sum()
            )

            ptu_interpolated += (
                before - after
            )

        # =============================================
        # GAP ANALYSIS
        # =============================================

        long_gap_count = 0
        threshold_count = 0
        ptu_interpolated = 0

        file_flagged = False
        for col in PTU_COLS:

            if col not in df.columns:
                continue

            series = df[col]
            mask = series.isna()

            if not mask.any():
                continue

            groups = (
                mask
                !=
                mask.shift(
                    fill_value=False
                )
            ).cumsum()

            nan_groups = (
                series[mask]
                .groupby(
                    groups[mask]
                )
            )

            for _, gap in nan_groups:

                start_time = gap.index[0]
                end_time = gap.index[-1]

                gap_rows = len(gap)

                gap_minutes = round(
                    gap_rows * 15 / 60,
                    2
                )

                start_loc = (
                    series.index.get_loc(
                        start_time
                    )
                )

                end_loc = (
                    series.index.get_loc(
                        end_time
                    )
                )

                prev_val = np.nan
                next_val = np.nan

                if start_loc > 0:

                    prev_val = (
                        series.iat[
                            start_loc - 1
                        ]
                    )

                if end_loc < len(series) - 1:

                    next_val = (
                        series.iat[
                            end_loc + 1
                        ]
                    )

                gap_audit.append({

                    "File":
                        file_name,

                    "Variable":
                        col,

                    "Start_Time":
                        start_time,

                    "End_Time":
                        end_time,

                    "Gap_Minutes":
                        gap_minutes,

                    "Previous_Value":
                        prev_val,

                    "Next_Value":
                        next_val
                })

                if gap_rows > MAX_GAP_ROWS:

                    long_gap_count += 1
                    file_flagged = True
                    continue

                if (
                    pd.notna(prev_val)
                    and
                    pd.notna(next_val)
                ):

                    change = abs(
                        next_val
                        -
                        prev_val
                    )

                    threshold = (
                        PTU_THRESHOLDS[
                            col
                        ]
                    )

                    if change > threshold:

                        threshold_count += 1
                        file_flagged = True
    
                        threshold_audit.append({

                            "File":
                                file_name,

                            "Variable":
                                col,

                            "Start_Time":
                                start_time,

                            "End_Time":
                                end_time,

                            "Gap_Minutes":
                                gap_minutes,

                            "Observed_Change":
                                round(
                                    change,
                                    2
                                ),

                            "Threshold":
                                threshold,

                            "Flag":
                                "THRESHOLD_EXCEEDED"
                        })

        # =============================================
        # SAVE FILE
        # =============================================

        df = df.reset_index()

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

        # =============================================
        # FILE FLAGS
        # =============================================

        if file_flagged:

            flagged_files.append({

                "File":
                    file_name,

                "Long_Gaps":
                    long_gap_count,

                "Threshold_Exceeded":
                    threshold_count
            })

        # =============================================
        # PROGRESS
        # =============================================

        print(
            "Rows Loaded          :",
            rows_before
        )

        print(
            "PTU Values Filled    :",
            ptu_interpolated
        )

        print(
            "Long Gap Flags       :",
            long_gap_count
        )

        print(
            "Threshold Flags      :",
            threshold_count
        )

        print(
            "Saved Successfully"
        )

    except Exception as e:

        print(
            "FAILED:",
            file_name
        )

        print(
            "ERROR:",
            str(e)
        )

# =====================================================
# SAVE AUDITS
# =====================================================

pd.DataFrame(
    gap_audit
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "gap_audit.csv"
    ),

    index=False
)

pd.DataFrame(
    threshold_audit
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "threshold_audit.csv"
    ),

    index=False
)

pd.DataFrame(
    flagged_files
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "flagged_files.csv"
    ),

    index=False
)

# =====================================================
# SUMMARY
# =====================================================

print("\n" + "=" * 80)
print("STAGE 2 COMPLETE")
print("=" * 80)

print(
    "Files Processed :",
    len(all_files)
)

print(
    "Gap Audit Rows :",
    len(gap_audit)
)

print(
    "Threshold Flags :",
    len(threshold_audit)
)

print(
    "Flagged Files :",
    len(flagged_files)
)

print("\nOutput Folder:")
print(OUTPUT_DIR)
print("=" * 80)