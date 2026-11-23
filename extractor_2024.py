import os
import pandas as pd
import re

# --- Configuration ---
SOURCE_DIR = r"C:\IMD PS Data\Data\2024_original_RWY27"
TARGET_DIR = r"C:\IMD PS Data\Data\2024_excel_RWY27"

DYNAMIC_MAPPING = {
    "PTU_RWY27": {
        "Pressure_QNH": ["QNH AERODROME"],
        "Temperature": ["TEMP ("],
        "DewPoint": ["DEWPOINT"],
        "Humidity": ["RH ("]
    },
    "VIS_RWY27": {
        "Visibility_MOR": ["MOR_1A"],
        "RVR": ["RVR_1A"]
    },
    "WIND_RWY27": {
        "Wind_Dir": ["WD10A"],
        "Wind_Speed": ["WS10A"],
        "Wind_Gust": ["GUST_SPEED"]
    },
    "PW_RWY27": {
        "Present_Weather_Code": ["WMO15A", "WMOINS"]
    },
    "CLOUD_RWY27": {
        "Cloud_Base_1": ["LAYER 1", "BASE 1", "BASE1"],
        "Cloud_Base_2": ["LAYER 2", "BASE 2", "BASE2"],
        "Cloud_Base_3": ["LAYER 3", "BASE 3", "BASE3"],
        "Vertical_Visibility": ["VER", "VV"]
    }
}

# ---> THE FIREWALL: Cleans illegal characters that crash Excel <---
def sanitize_for_excel(text):
    if not text:
        return None
    text = str(text)
    # Remove literal "\r" and "\n" strings that AWOS sensors sometimes output
    text = text.replace('\\r', ' ').replace('\\n', ' ')
    # Remove actual carriage returns and newlines
    text = text.replace('\r', ' ').replace('\n', ' ')
    # Remove hidden control characters (ASCII 0-31) except tab/space
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()

def dynamic_his_to_excel():
    print(f"🚀 Starting Dynamic Tab-Separated Conversion...")
    print(f"Source: {SOURCE_DIR}")
    print(f"Target: {TARGET_DIR}\n")

    os.makedirs(TARGET_DIR, exist_ok=True)
    total_converted = 0
    total_failed = 0

    all_items = os.listdir(SOURCE_DIR)
    month_folders = [f for f in all_items if os.path.isdir(os.path.join(SOURCE_DIR, f))]
    total_folders = len(month_folders)

    for folder_idx, month_folder in enumerate(month_folders, 1):
        source_month_path = os.path.join(SOURCE_DIR, month_folder)
        target_month_path = os.path.join(TARGET_DIR, month_folder)
        os.makedirs(target_month_path, exist_ok=True)
        
        print(f"\n📁 Processing folder {folder_idx} of {total_folders}: [{month_folder}]")
        his_files = [f for f in os.listdir(source_month_path) if f.endswith(".his")]

        for file_idx, filename in enumerate(his_files, 1):
            print(f"   ↳ Converting {file_idx}/{len(his_files)}: {filename}")
            file_prefix = "_".join(filename.split("_")[:2]) 
            source_file = os.path.join(source_month_path, filename)
            target_file = os.path.join(target_month_path, filename.replace(".his", ".xlsx"))

            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                if len(lines) < 3:
                    print(f"      ⚠️ Skipped: File too short or empty.")
                    continue

                header_idx = 1 if "History" in lines[0] else 0
                
                # Sanitize the headers to prevent XML crashes in column names
                raw_headers = [sanitize_for_excel(h).upper() for h in lines[header_idx].split('\t')]
                
                index_map = {}
                mapping_rules = DYNAMIC_MAPPING.get(file_prefix, {})
                
                for target_col, keywords in mapping_rules.items():
                    for i, raw_h in enumerate(raw_headers):
                        if raw_h and any(kw in raw_h for kw in keywords):
                            index_map[target_col] = i
                            break
                            
                extracted_data = []
                for line in lines[header_idx + 1:]:
                    if not line.strip(): continue
                    
                    # Split strictly by TAB and heavily sanitize every single cell
                    cols = [sanitize_for_excel(c) for c in line.split('\t')]
                    
                    createdate = cols[0] if len(cols) > 0 and cols[0] else ""
                    if " " in createdate:
                        date_part, time_part = createdate.split(" ", 1)
                    else:
                        date_part, time_part = createdate, ""
                        
                    row_dict = {"Date": date_part, "Time": time_part}
                    
                    for target_col, idx in index_map.items():
                        if idx < len(cols) and cols[idx]:
                            row_dict[target_col] = cols[idx]
                        else:
                            row_dict[target_col] = None
                            
                    for i in range(1, len(cols)):
                        if i not in index_map.values():
                            h_name = raw_headers[i] if i < len(raw_headers) and raw_headers[i] else f"EXTRA_COL_{i}"
                            row_dict[h_name] = cols[i] if i < len(cols) and cols[i] else None
                            
                    extracted_data.append(row_dict)
                    
                df = pd.DataFrame(extracted_data)
                
                vital_cols = ["Date", "Time"] + list(index_map.keys())
                other_cols = [c for c in df.columns if c not in vital_cols]
                df = df[vital_cols + other_cols]

                df.to_excel(target_file, index=False)
                total_converted += 1
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                total_failed += 1

    print(f"\n✅ Pipeline Complete!")
    print(f"Successfully converted: {total_converted} files.")
    print(f"Failed/Skipped files: {total_failed}")

if __name__ == "__main__":
    dynamic_his_to_excel()