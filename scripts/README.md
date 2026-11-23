# Scripts

This directory contains the executable stages of the Lucknow weather-data pipeline.

## Data conversion

- `2024_filesmove.py` - segregates source observations for a selected runway.
- `extractor_2024.py` - extracts source data into sensor-specific CSV or Excel files.
- `his_to_excel_converter.py` - converts HIS files to Excel workbooks.
- `clean_rwy27_processor.py` - applies RWY27-specific source cleaning.
- `columndrop_2024.py` - removes unwanted 2024 source columns.

## Dataset preparation

- `2024_merge.py` - merges same-day 2024 sensor observations.
- `stage1_preprocess.py` - normalizes timestamps and repairs basic values.
- `stage2_gap_analysis.py` - detects gaps and sensor threshold violations.
- `stage3_final.py` - applies final domain-aware cleaning.
- `stage4_mlreadydata.py` - creates ML-ready features.
- `merge_lstm_ready_dataset.py` - combines daily files into one chronological dataset.

## Model benchmarking

- `benchmark_lucknow_models.py` - compares classical models using compact history features.

Run a script with `python scripts/<script-name>.py`. Update each script's local
input and output paths before processing a new station or data period.
