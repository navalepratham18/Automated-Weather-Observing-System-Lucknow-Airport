import os
import numpy as np
import pandas as pd

# =====================================================
# PATHS
# =====================================================

INPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\lucknow_worked\05_STAGE2_FLAGGED"

OUTPUT_DIR = r"C:\IMD PS Data\Data\Lucknow\lucknow_worked\06_FINAL_LKO_CLEANED"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =====================================================
# CONFIGURATION
# =====================================================

# 5 min at 15 sec resolution
MAX_GAP_ROWS = 20

WIND_COLS = [
    "WIND_Wind_Dir",
    "WIND_Wind_Speed",
    "WIND_Wind_Gust"
]

RAIN_COLS = [
    "PW_Rain_Intensity",
    "PW_Rain_Sum"
]

# =====================================================
# GLOBAL STATISTICS
# =====================================================

successful_files = 0
failed_files = []

cleaning_summary = []
final_flags = []
wind_gap_flags = []

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

print(
    "\nFILES FOUND:",
    len(all_files)
)

# =====================================================
# PROCESS FILES
# =====================================================

for index, file_path in enumerate(
    all_files,
    start=1
):

    file_name = os.path.basename(
        file_path
    )

    print("\n" + "=" * 80)

    print(
        f"[{index}/{len(all_files)}]"
    )

    print(
        file_name
    )

    print(
        f"Progress : "
        f"{(index / len(all_files)) * 100:.2f}%"
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

        # =================================================
        # DATETIME
        # =================================================

        df["Datetime"] = pd.to_datetime(
            df["Datetime"],
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

        df = df.sort_index()

        # =================================================
        # NUMERIC CONVERSION
        # =================================================

        numeric_cols = (
            df.columns
        )

        df[numeric_cols] = (

            df[numeric_cols]
            .apply(
                pd.to_numeric,
                errors="coerce"
            )

        )

        # =================================================
        # INITIAL COUNTERS
        # =================================================

        wind_filled = 0
        rain_filled = 0

        # =================================================
        # WIND INTERPOLATION
        # =================================================

        for col in WIND_COLS:

            if col not in df.columns:
                continue

            series = df[col]

            mask = series.isna()

            if mask.any():

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

                    gap_rows = len(gap)

                    if gap_rows > MAX_GAP_ROWS:

                        wind_gap_flags.append({

                            "File":
                                file_name,

                            "Variable":
                                col,

                            "Start_Time":
                                gap.index[0],

                            "End_Time":
                                gap.index[-1],

                            "Gap_Rows":
                                gap_rows,

                            "Gap_Minutes":
                                round(
                                    gap_rows * 15 / 60,
                                    2
                                ),

                            "Flag":
                                "WIND_LONG_GAP"
                        })

            before = (
                series.isna()
                .sum()
            )

            interp_series = (
                series
                .interpolate(
                    method="time",
                    limit_area="inside"
                )
                .round(2)
            )

            if mask.any():

                for _, gap in nan_groups:

                    gap_rows = len(gap)

                    # Skip long gaps entirely
                    if gap_rows > MAX_GAP_ROWS:
                        continue

                    fill_idx = gap.index

                    series.loc[
                        fill_idx
                    ] = (
                        interp_series
                        .loc[
                            fill_idx
                        ]
                    )

            df[col] = series

            after = (
                df[col]
                .isna()
                .sum()
            )

            wind_filled += (
                before
                -
                after
            )

        # =================================================
        # RAIN INTERPOLATION
        # =================================================

        for col in RAIN_COLS:

            if col not in df.columns:
                continue

            series = df[col]

            mask = (
                series.isna()
            )

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

            interp_series = (

                series
                .interpolate(
                    method="time"
                )
                .round(2)

            )

            for _, gap in nan_groups:

                gap_rows = len(gap)

                # -------------------------------------
                # Gap > 5 min
                # -------------------------------------

                if (
                    gap_rows
                    >
                    MAX_GAP_ROWS
                ):
                    continue

                start = gap.index[0]
                end = gap.index[-1]

                start_loc = (
                    series.index
                    .get_loc(start)
                )

                end_loc = (
                    series.index
                    .get_loc(end)
                )

                prev_exists = (

                    start_loc > 0
                    and
                    pd.notna(
                        series.iat[
                            start_loc - 1
                        ]
                    )

                )

                next_exists = (

                    end_loc
                    <
                    len(series) - 1
                    and
                    pd.notna(
                        series.iat[
                            end_loc + 1
                        ]
                    )

                )

                # -------------------------------------
                # Fill only if bounded
                # -------------------------------------

                if (
                    prev_exists
                    and
                    next_exists
                ):

                    fill_idx = (

                        series.index[
                            start_loc:
                            end_loc + 1
                        ]

                    )

                    series.loc[
                        fill_idx
                    ] = (

                        interp_series
                        .loc[
                            fill_idx
                        ]

                    )

                    rain_filled += (
                        gap_rows
                    )

            df[col] = series

        # =================================================
        # FINAL STATISTICS
        # =================================================

        remaining_nans = int(

            df.isna()
            .sum()
            .sum()

        )

        cleaning_summary.append({

            "File":
                file_name,

            "Wind_Filled":
                wind_filled,

            "Rain_Filled":
                rain_filled,

            "Remaining_NaNs":
                remaining_nans
        })

        if remaining_nans > 0:

            final_flags.append({

                "File":
                    file_name,

                "Remaining_NaNs":
                    remaining_nans
            })

        # =================================================
        # SAVE FILE
        # =================================================

        df = df.reset_index()

        df["Datetime"] = (
            pd.to_datetime(
                df["Datetime"]
            )
            .dt.strftime(
                "%d-%m-%Y %H:%M:%S"
            )
        )

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

        successful_files += 1

        # =================================================
        # REAL-TIME UPDATE
        # =================================================

        print(
            "Wind Filled      :",
            wind_filled
        )

        print(
            "Rain Filled      :",
            rain_filled
        )

        print(
            "Remaining NaNs   :",
            remaining_nans
        )

        print(
            "Saved Successfully"
        )

    except Exception as e:

        failed_files.append({

            "File":
                file_name,

            "Path":
                file_path,

            "Error":
                str(e)
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
# SAVE REPORTS
# =====================================================

pd.DataFrame(
    cleaning_summary
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "cleaning_summary.csv"
    ),

    index=False
)

pd.DataFrame(
    final_flags
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "final_flags.csv"
    ),

    index=False
)

pd.DataFrame(
    wind_gap_flags
).to_csv(

    os.path.join(
        OUTPUT_DIR,
        "wind_gap_flags.csv"
    ),

    index=False
)

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
print("STAGE 3 COMPLETE")
print("=" * 80)

print(
    "Files Found          :",
    len(all_files)
)

print(
    "Files Saved          :",
    successful_files
)

print(
    "Files Failed         :",
    len(failed_files)
)

print(
    "Files With NaNs      :",
    len(final_flags)
)

print(
    "Wind Long Gaps      :",
    len(wind_gap_flags)
)

print("\nOutput Folder:")
print(
    OUTPUT_DIR
)

print("=" * 80)