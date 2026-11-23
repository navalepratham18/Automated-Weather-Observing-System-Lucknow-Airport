import os
import re
import pandas as pd
from collections import defaultdict

SOURCE_DIR = r"C:\IMD PS Data\Data\2024_mumbai\2024_cleaned_csv_RWY27"
TARGET_DIR = r"C:\IMD PS Data\Data\2024_mumbai\2024_merged_daily_RWY27"

os.makedirs(TARGET_DIR, exist_ok=True)

month_map = {
    "Jan":1,"Feb":2,"Mar":3,"Apr":4,
    "May":5,"Jun":6,"Jul":7,"Aug":8,
    "Sep":9,"Oct":10,"Nov":11,"Dec":12
}

files_by_day = defaultdict(list)

print("Scanning files...")

for month_folder in os.listdir(SOURCE_DIR):

    month_path = os.path.join(SOURCE_DIR, month_folder)

    if not os.path.isdir(month_path):
        continue

    for file in os.listdir(month_path):

        if not file.lower().endswith(".csv"):
            continue

        full_path = os.path.join(month_path, file)

        match = re.search(r'_(\d{2})\.csv$', file)

        if not match:
            continue

        day = match.group(1)

        files_by_day[(month_folder, day)].append(full_path)

print(f"Found {len(files_by_day)} daily groups")

for (month_name, day), file_list in sorted(files_by_day.items()):

    print(f"\nProcessing {month_name}-{day}")

    merged_df = None

    for file_path in file_list:

        filename = os.path.basename(file_path)

        sensor = filename.split("_")[0]

        try:

            df = pd.read_csv(file_path)

            df.columns = (
                df.columns
                .str.strip()
                .str.replace('\ufeff','',regex=False)
            )

            if 'Date' not in df.columns or 'Time' not in df.columns:
                print(f"Skipping {filename}")
                continue

            rename_dict = {}

            for col in df.columns:

                if col not in ['Date','Time']:

                    rename_dict[col] = f"{sensor}_{col}"

            df.rename(columns=rename_dict, inplace=True)

            df.drop_duplicates(
                subset=['Date','Time'],
                inplace=True
            )

            if merged_df is None:

                merged_df = df

            else:

                merged_df = pd.merge(
                    merged_df,
                    df,
                    on=['Date','Time'],
                    how='outer'
                )

            print(f"   merged {filename}")

        except Exception as e:

            print(f"ERROR {filename}: {e}")

    if merged_df is None:
        continue

    merged_df.sort_values(
        by=['Date','Time'],
        inplace=True
    )

    output_month = os.path.join(
        TARGET_DIR,
        month_name
    )

    os.makedirs(output_month, exist_ok=True)

    output_file = f"2024_{month_name}_{day}.csv"

    merged_df.to_csv(
        os.path.join(output_month, output_file),
        index=False
    )

    print(f"Saved {output_file}")

print("\nDONE")