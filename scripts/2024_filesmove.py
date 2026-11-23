import os
import shutil

# --- Configuration ---
# Update these paths if your setup is slightly different
SOURCE_DIR = r"C:\IMD PS Data\Data\2024\2024"
TARGET_DIR = r"C:\IMD PS Data\Data\2024_original_RWY27"

# The exact prefixes we want to keep (STRICTLY RWY27 ONLY)
TARGET_PREFIXES = (
    "CLOUD_RWY27",
    "PTU_RWY27",
    "PW_RWY27",
    "VIS_RWY27",
    "WIND_RWY27"
)

def segregate_rwy27_data():
    print(f"🚀 Starting segregation pipeline...")
    print(f"Source: {SOURCE_DIR}")
    print(f"Target: {TARGET_DIR}\n")
    
    total_files_copied = 0

    # Ensure the main target directory exists
    os.makedirs(TARGET_DIR, exist_ok=True)

    # Loop through the items in the source directory (Aug, Dec, Jul, etc.)
    for month_folder in os.listdir(SOURCE_DIR):
        month_path = os.path.join(SOURCE_DIR, month_folder)

        # Skip files, we only want the month directories
        if not os.path.isdir(month_path):
            continue

        # ---> THIS ENSURES NO MIXING <---
        # It creates a dedicated folder for the current month in the target directory
        target_month_path = os.path.join(TARGET_DIR, month_folder)
        os.makedirs(target_month_path, exist_ok=True)
        
        print(f"📁 Opening source month: {month_folder}")
        print(f"   ↳ Target dedicated folder created at: {target_month_path}")
        
        files_in_month = 0
        
        # Scan inside the current month folder
        for filename in os.listdir(month_path):
            # Check if it's a file we actually want
            if filename.startswith(TARGET_PREFIXES) and filename.endswith(".his"):
                source_file = os.path.join(month_path, filename)
                # Ensure the target path includes the specific month folder
                target_file = os.path.join(target_month_path, filename) 

                # Copy safely (copy2 preserves original timestamps)
                shutil.copy2(source_file, target_file)
                files_in_month += 1
                total_files_copied += 1
                
        print(f"   ✓ Locked in {files_in_month} useful files for {month_folder}\n")

    print(f"✅ Pipeline Complete! {total_files_copied} files safely organized month-by-month.")

if __name__ == "__main__":
    segregate_rwy27_data()