# Lucknow Airport Weather Observation and Forecasting Pipeline

An end-to-end pipeline for processing Lucknow airport meteorological observations
and training/evaluating LSTM and classical forecasting models.

## Project overview

The workflow converts raw runway sensor files into sensor-specific CSV files,
merges them into daily observations, performs gap-aware cleaning, creates
machine-learning-ready datasets, and benchmarks forecasting models.

## Repository structure

```text
.
|-- scripts/       Data conversion, cleaning, preprocessing, and benchmarking
|-- notebooks/     Model training, benchmarking, and experimental notebooks
|-- docs/          Reusable pipeline instructions and project documentation
|-- .gitignore     Excludes raw, intermediate, and generated data
`-- README.md
```

## Pipeline

```text
Raw .his files
      |
      v
Sensor CSV conversion
      |
      v
Daily sensor merge
      |
      v
Stage 1: timestamp and basic repair
      |
      v
Stage 2: gap and threshold analysis
      |
      v
Stage 3: final domain-aware cleaning
      |
      v
Stage 4: ML-ready features
      |
      v
Unified chronological dataset
      |
      v
LSTM and baseline model evaluation
```

## Main scripts

| Script | Purpose |
|---|---|
| `2024_filesmove.py` | Selects source files for the configured runway |
| `extractor_2024.py` | Converts source observations to sensor-specific files |
| `2024_merge.py` | Merges same-day sensor observations |
| `stage1_preprocess.py` | Repairs timestamps and basic missing values |
| `stage2_gap_analysis.py` | Flags gaps and threshold violations |
| `stage3_final.py` | Applies final cleaning rules |
| `stage4_mlreadydata.py` | Creates model features |
| `merge_lstm_ready_dataset.py` | Builds the unified chronological dataset |
| `benchmark_lucknow_models.py` | Compares classical baseline models |

## Notebooks

| Notebook | Purpose |
|---|---|
| `train_lucknow_lstm.ipynb` | Standard LSTM training and evaluation |
| `train_lucknow_lstm_range_aware.ipynb` | Range-aware LSTM training |
| `benchmark_lucknow_models.ipynb` | Interactive model benchmarking |
| `test.ipynb` | Development and validation experiments |

## Setup

Create a Python environment and install the required packages:

```powershell
conda create -n weather_pipe python=3.10
conda activate weather_pipe
pip install -r requirements.txt
```

Run scripts from the repository root, for example:

```powershell
python scripts/benchmark_lucknow_models.py
```

## Data handling

Raw, intermediate, and generated data are intentionally excluded from Git. This
keeps the repository small and prevents large weather datasets or model artifacts
from being committed. Store those files in a local `data/` or `lucknow_worked/`
directory and preserve source hashes or a data manifest for reproducibility.

## Detailed documentation

- [Pipeline operating instructions](docs/instructions.md)
- [Scripts guide](scripts/README.md)
- [Notebooks guide](notebooks/README.md)
