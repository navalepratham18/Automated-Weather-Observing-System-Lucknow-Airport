import os
import pandas as pd

# --- Configuration ---
SOURCE_DIR = r"C:\IMD PS Data\Data\2024_mumbai\2024_excel_RWY27"
TARGET_DIR = r"C:\IMD PS Data\Data\2024_mumbai\2024_cleaned_csv_RWY27"

# Columns to keep
KEEP_COLUMNS = {
    "PTU_RWY27": [
        "Date",
        "Time",
        "Pressure_QNH",
        "Temperature",
        "DewPoint",
        "Humidity"
    ],

    "VIS_RWY27": [
        "Date",
        "Time",
        "Visibility_MOR",
        "RVR"
    ],

    "CLOUD_RWY27": [
        "Date",
        "Time",
        "Cloud_Base_1",
        "Cloud_Base_2",
        "Cloud_Base_3",
        "SITE",
        "OCTA1",
        "OCTA2",
        "OCTA3",
        "OCTA4",
        "Vertical_Visibility"
    ],

    "WIND_RWY27": [
        "Date",
        "Time",
        "Wind_Dir",
        "Wind_Speed",
        "Wind_Gust"
    ],

    "PW_RWY27": [
        "Date",
        "Time",
        "Present_Weather_Code"
        
    ]
}

def purge_and_convert_to_csv():

    print("🚀 Starting Strict Column Purge & CSV Conversion...")
    print(f"Source: {SOURCE_DIR}")
    print(f"Target: {TARGET_DIR}\n")

    os.makedirs(TARGET_DIR, exist_ok=True)

    total_converted = 0
    total_failed = 0

    all_items = os.listdir(SOURCE_DIR)

    month_folders = [
        f for f in all_items
        if os.path.isdir(os.path.join(SOURCE_DIR, f))
    ]

    total_folders = len(month_folders)

    for folder_idx, month_folder in enumerate(month_folders, start=1):

        source_month_path = os.path.join(SOURCE_DIR, month_folder)
        target_month_path = os.path.join(TARGET_DIR, month_folder)

        os.makedirs(target_month_path, exist_ok=True)

        print(
            f"\n📁 Processing folder {folder_idx} of {total_folders}: [{month_folder}]"
        )

        excel_files = [
            f for f in os.listdir(source_month_path)
            if f.lower().endswith(".xlsx")
        ]

        for file_idx, filename in enumerate(excel_files, start=1):

            print(
                f"   ↳ Purging & Converting {file_idx}/{len(excel_files)}: {filename}"
            )

            file_prefix = "_".join(filename.split("_")[:2])

            source_file = os.path.join(source_month_path, filename)
            target_file = os.path.join(
                target_month_path,
                filename.replace(".xlsx", ".csv")
            )

            allowed_cols = KEEP_COLUMNS.get(file_prefix, []).copy()

            if not allowed_cols:
                print(f"      ⚠ Skipping unknown file type: {filename}")
                continue

            try:

                df = pd.read_excel(source_file)

                if df.empty:
                    print("      ⚠ Empty file skipped")
                    continue

                # PW Rain Columns Rescue
                if file_prefix == "PW_RWY27":

                    rain_cols = [
                        c for c in df.columns
                        if (
                            "RAIN INT" in str(c).upper()
                            or "RAIN_INT" in str(c).upper()
                            or "RAIN SUM" in str(c).upper()
                            or "RAIN_SUM" in str(c).upper()
                        )
                    ]

                    allowed_cols.extend(rain_cols)

                # Keep only columns that actually exist
                actual_cols_to_keep = [
                    col for col in allowed_cols
                    if col in df.columns
                ]

                df_clean = df[actual_cols_to_keep].copy()

                # Standardize rain column names
                rename_dict = {}

                for c in df_clean.columns:

                    cname = str(c).upper()

                    if "RAIN INT" in cname or "RAIN_INT" in cname:
                        rename_dict[c] = "Rain_Intensity"

                    elif "RAIN SUM" in cname or "RAIN_SUM" in cname:
                        rename_dict[c] = "Rain_Sum"

                if rename_dict:
                    df_clean.rename(
                        columns=rename_dict,
                        inplace=True
                    )

                df_clean.to_csv(
                    target_file,
                    index=False
                )

                total_converted += 1

            except Exception as e:

                print(f"      ❌ Failed: {e}")
                total_failed += 1

    print("\n" + "=" * 60)
    print("✅ PURGE COMPLETE")
    print(f"Converted : {total_converted}")
    print(f"Failed    : {total_failed}")
    print("=" * 60)


if __name__ == "__main__":
    purge_and_convert_to_csv()