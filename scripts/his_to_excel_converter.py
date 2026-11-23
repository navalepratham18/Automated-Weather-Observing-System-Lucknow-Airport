import os
import glob
import pandas as pd
import re

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = r"C:\IMD PS Data\Data"
OUTPUT_DIR = r"C:\IMD PS Data\Data\Converted_Excel"

def clean_cell(val):
    """
    Maximum strictness sanitizer. Strips ALL hidden control characters, 
    weird unicode bugs, and unprintable anomalies.
    """
    if pd.isna(val) or val is None:
        return val
        
    val_str = str(val)
    cleaned = re.sub(r'[^\x20-\x7E]', '', val_str)
    
    return cleaned.strip()

def parse_his_file(file_path):
    """Parses the messy .his file and aligns it with the exact requested headers."""
    extracted_data = []
    timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            if timestamp_pattern.match(line):
                parts = re.split(r'\s+', line)
                
                if len(parts) >= 10: 
                    # Split the timestamp to match the Date Time, Date, and Time columns
                    date_val = parts[0]
                    time_val = parts[1]
                    datetime_val = f"{date_val} {time_val}"
                    
                    # Construct the row with the three time columns first, then the rest of the data
                    raw_row_data = [datetime_val, date_val, time_val] + parts[2:]
                    
                    clean_row_data = [clean_cell(cell) for cell in raw_row_data]
                    extracted_data.append(clean_row_data)

    if not extracted_data:
        return None
        
    max_cols = max(len(row) for row in extracted_data)
    
    # --- EXACT HEADERS FROM YOUR SCREENSHOT ---
    headers = [
        "Date Time", "Date", "Time", "1st_Cloud(Ft)", "2nd_Cloud(Ft)", 
        "3rd_Cloud(Ft)", "Vis_Type(Ft)", "Vis_Status(Ft)", "Cloud_Base(Ft)", 
        "St", "Detstat", "Amt_1", "Amt_2", "Amt_3", "Amt_4"
    ]
    
    while len(headers) < max_cols:
        headers.append(f"EXTRA_COL_{len(headers)}")
        
    clean_data = [row + [None]*(max_cols - len(row)) for row in extracted_data]
    df = pd.DataFrame(clean_data, columns=headers[:max_cols])
    return df

def convert_all_his_files():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    search_pattern = os.path.join(BASE_DIR, '**', '*.his')
    all_his_files = glob.glob(search_pattern, recursive=True)
    
    files_by_dir = {}
    for file_path in all_his_files:
        parent_dir = os.path.dirname(file_path)
        if parent_dir not in files_by_dir:
            files_by_dir[parent_dir] = []
        files_by_dir[parent_dir].append(file_path)
        
    print(f"\n🔍 Found {len(all_his_files)} .his files across {len(files_by_dir)} month folders.\n")
    
    for directory, files in files_by_dir.items():
        folder_name = os.path.basename(directory)
        month_identifier = folder_name.replace(" ", "_").replace("(", "").replace(")", "")
        
        out_subdir = os.path.join(OUTPUT_DIR, month_identifier)
        if not os.path.exists(out_subdir):
            os.makedirs(out_subdir)
            
        print(f"\n📂 =========================================")
        print(f"📂 ENTERING FOLDER: {folder_name}")
        print(f"📂 Files to process: {len(files)}")
        print(f"📂 Saving data to: {out_subdir}")
        print(f"📂 =========================================\n")
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(file_name)[0]
            excel_name = f"{name_without_ext}_{month_identifier}.xlsx"
            out_file = os.path.join(out_subdir, excel_name)
            
            try:
                df = parse_his_file(file_path)
                if df is not None and not df.empty:
                    df.to_excel(out_file, index=False)
                    print(f"  ✅ Saved: {excel_name}")
                else:
                    print(f"  ⚠️ Skipped: No valid tabular data found in {file_name}")
            except Exception as e:
                print(f"  ❌ CRASH PREVENTED: Failed to process {file_name}. Error: {e}")

if __name__ == "__main__":
    convert_all_his_files()