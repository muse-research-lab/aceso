#!/usr/bin/env python3
"""Run inference with the saved models (no retraining) and write the results used by the plot.

    python inference/infer.py [--check]

Loads training/models/ (written by training/train.py) and predicts the test period exactly as
train.py part B does:
   RF / GBDT / LR: one-step-ahead from the TRUE previous 12 values (MinMax-scaled).
   Prophet:        predicts the test timestamps.
   NHITS/PatchTST: forecast the 4 test days in one shot from the end of days 1-10.
Writes results/test_predictions.csv and results/test_metrics.csv.

--check  compare against the existing results/test_predictions.csv first and report the largest
         difference per model (the file is still overwritten afterwards).

results/validation_metrics.csv (the legend MAE) is NOT recomputed: Prophet/NHITS/PatchTST were
saved after re-training on days 1-10, so their validation score can only come from train.py.
"""
from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training"))
from train import DATA, MODELS, RESULTS, N_TRAIN, N_VAL, LAGS, WINDOW, lagged  # noqa: E402

SKLEARN = ["RandomForest", "GBDT", "LinearRegression"]
ORDER = ["RandomForest", "GBDT", "LinearRegression", "Prophet", "NHITS", "PatchTST"]


def predict() -> pd.DataFrame:
    from neuralforecast import NeuralForecast
    from prophet.serialize import model_from_json

    ts = pd.read_csv(DATA, index_col="datetime", parse_dates=True)[["value"]].sort_index()
    train, val, test = ts.iloc[:N_TRAIN], ts.iloc[N_TRAIN:N_TRAIN + N_VAL], ts.iloc[N_TRAIN + N_VAL:]
    scaler = joblib.load(MODELS / "minmax_scaler.joblib")
    tr_s, va_s, te_s = scaler.transform(train), scaler.transform(val), scaler.transform(test)
    X_te, _ = lagged(np.concatenate([tr_s[-LAGS:], va_s, te_s]))
    inv = lambda a: scaler.inverse_transform(np.asarray(a).reshape(-1, 1)).ravel()

    preds = {}
    for name in SKLEARN:
        preds[name] = inv(joblib.load(MODELS / f"{name}.joblib").predict(X_te))

    pm = model_from_json((MODELS / "Prophet.json").read_text())
    preds["Prophet"] = pm.predict(test.reset_index().rename(columns={"datetime": "ds"})[["ds"]])["yhat"].values

    df_nf = ts.reset_index().rename(columns={"datetime": "ds", "value": "y"})
    df_nf["unique_id"] = "series_1"
    for name in ("NHITS", "PatchTST"):
        nf = NeuralForecast.load(path=str(MODELS / name))
        f = nf.predict(df=df_nf.iloc[:N_TRAIN + N_VAL])
        col = [c for c in f.columns if c not in ("unique_id", "ds")][0]
        preds[name] = f.query("unique_id=='series_1'")[col].values

    P = pd.DataFrame({"truth": test["value"].values}, index=test.index)
    for name in ORDER:
        P[name] = np.asarray(preds[name])[-len(test):]      # same alignment as train.py
    return P, scaler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with the existing test_predictions.csv")
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    logging.getLogger("lightning").setLevel(logging.ERROR)
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

    P, scaler = predict()
    P.index.name = "datetime"

    old_path = RESULTS / "test_predictions.csv"
    if a.check and old_path.exists():
        old = pd.read_csv(old_path, index_col="datetime", parse_dates=True)
        print("max |new - saved| per model (original units):")
        for m in ORDER:
            print(f"  {m:17s} {np.max(np.abs(P[m].values - old[m].values)):.2e}")

    P.to_csv(old_path)
    w = P.loc[WINDOW[0]:WINDOW[1]]; wmax = w["truth"].max()
    T = pd.DataFrame({m: {"MAE_test_orig": mean_absolute_error(P.truth, P[m]),
                          "MAE_test_norm": mean_absolute_error(scaler.transform(P[["truth"]].values).ravel(),
                                                               scaler.transform(P[[m]].values).ravel()),
                          "MAE_window_norm": mean_absolute_error(w.truth / wmax, w[m] / wmax)}
                      for m in ORDER}).T.sort_values("MAE_window_norm")
    T.index.name = "model"
    T.to_csv(RESULTS / "test_metrics.csv")
    print("\n=== test MAE ===\n" + T.round(6).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
