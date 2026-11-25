# Notebooks

This directory contains the interactive training and evaluation workflow.

| Notebook | Description |
|---|---|
| `lucknow_lstm_cloud_30minutes.ipynb` | Trains and evaluates a gap-aware, 30-minute multi-target LSTM forecast for Lucknow |
| `train_lucknow_lstm.ipynb` | Trains and evaluates the standard Lucknow LSTM |
| `train_lucknow_lstm_range_aware.ipynb` | Trains the range-aware LSTM variant |
| `benchmark_lucknow_models.ipynb` | Benchmarks and compares forecasting approaches |
| `test.ipynb` | Development, debugging, and validation experiments |

Notebook outputs and generated model artifacts should not be committed. Keep
large datasets outside Git and use model result directories documented in the
project README.
