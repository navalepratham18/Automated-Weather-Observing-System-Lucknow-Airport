import os
import glob
import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
# Source directory where your previous script saved the excel files
INPUT_DIR = r"C:\IMD PS Data\Data\Converted_Excel"
# Destination directory for the clean Runway 27 CSV data
OUTPUT_DIR = r"C:\IMD PS Data\Data\Cleaned_RWY27_CSV"

# The exact core column arrangement we want to keep
CORE_COLUMNS = [
    "Date Time", "Date", "Time", "1st_Cloud(Ft)", "2nd_Cloud(Ft)", 
    "3rd_Cloud(Ft)", "Vis_Type(Ft)", "Vis_Status(Ft)", "Cloud_Base(Ft)", 
    "St", "Detstat", "Amt_1", "Amt_2", "Amt_3", "Amt_4"
]

def process_and_clean_files():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Find all generated Excel files recursively
    search_pattern = os.path.join(INPUT_DIR, '**', '*.xlsx')
    excel_files = glob.glob(search_pattern, recursive=True)
    
    print(f"\n🔍 Found {len(excel_files)} Excel files total in storage. Filtering for RWY27...")

    # Group target Runway 27 files by folder to maintain transparency
    files_by_dir = {}
    rwy27_count = 0
    
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        
        # --- FILTRATION STEP: ONLY ALLOW RUNWAY 27 ---
        if "RWY27" in file_name.upper():
            rwy27_count += 1
            parent_dir = os.path.dirname(file_path)
            if parent_dir not in files_by_dir:
                files_by_dir[parent_dir] = []
            files_by_dir[parent_dir].append(file_path)

    print(f"🎯 Target locked onto {rwy27_count} files belonging to Runway 27 (Discarding RWY14 data).\n")

    # Process folder by folder
    for directory, files in files_by_dir.items():
        folder_name = os.path.basename(directory)
        
        # Recreate the precise month folder layout inside the new output directory
        out_subdir = os.path.join(OUTPUT_DIR, folder_name)
        if not os.path.exists(out_subdir):
            os.makedirs(out_subdir)

        print(f"📂 =========================================")
        print(f"📂 PROCESSING BATCH: {folder_name}")
        print(f"📂 Runway 27 Files: {len(files)}")
        print(f"📂 =========================================\n")

        for file_path in files:
            file_name = os.path.basename(file_path)
            
            # Setup destination filename with .csv extension
            csv_name = file_name.replace('.xlsx', '.csv')
            out_file = os.path.join(out_subdir, csv_name)
            
            try:
                # Read the excel spreadsheet
                df = pd.read_excel(file_path)
                
                # --- COLUMN SIFTING STEP ---
                # Check which of our target core columns actually exist in this sheet
                existing_core_cols = [col for col in CORE_COLUMNS if col in df.columns]
                
                # Sift out only those core columns, completely leaving 'EXTRA_COL_...' behind
                cleaned_df = df[existing_core_cols].copy()
                
                # Save out to CSV format (using index=False to prevent empty unnamed column index)
                cleaned_df.to_csv(out_file, index=False)
                print(f"  💾 Exported Clean CSV: {csv_name}")
                
            except Exception as e:
                print(f"  ❌ Failed to refine {file_name}. Error details: {e}")

    print(f"\n✨ All done! Cleaned Runway 27 data is stored neatly at: {OUTPUT_DIR}\n")

if __name__ == "__main__":
    process_and_clean_files()