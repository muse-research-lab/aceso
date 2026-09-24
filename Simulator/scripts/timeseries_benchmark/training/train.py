#!/usr/bin/env python3
"""Train the six forecasters, save them, and write the results used by the plot.

    python training/train.py

Reproduces final_version.ipynb exactly (same data split, scaler, features, hyper-parameters,
seeds), in two parts:

A. Validation benchmark  (notebook cell 14)  -> results/validation_metrics.csv
   Train on days 1-7, evaluate on days 8-10 (validation).  MAE_norm = MAE on the MinMax-scaled
   series (scaler fitted on train).  These are the MAE values printed in the figure legend.

B. Final models  (notebook cell 16)  -> training/models/, results/test_predictions.csv,
   results/test_metrics.csv
   RF / GBDT / LR: trained on days 1-7 (12 lagged values -> next value; one-step-ahead,
                   fed the TRUE previous 12 values at every step).
   Prophet:        trained on days 1-10, forecasts the test timestamps.
   NHITS/PatchTST: trained on days 1-10, forecast the next 4 days (h = 1152) in one shot.
   Predictions are aligned to the test index as in the notebook (last len(test) values).

Data: data/timeseries_c8c43e_653cdb.csv (see data/prepare_data.py).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import MinMaxScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "timeseries_c8c43e_653cdb.csv"
MODELS = ROOT / "training" / "models"
RESULTS = ROOT / "results"

POINTS_PER_DAY = 288
N_TRAIN, N_VAL, N_TEST = 7 * POINTS_PER_DAY, 3 * POINTS_PER_DAY, 4 * POINTS_PER_DAY
LAGS = 12                                   # 1 hour of history
MAX_STEPS = 300                             # NeuralForecast training steps
WINDOW = ("1970-01-13 05:00", "1970-01-14 04:00")   # the plotted window


def lagged(data, lags=LAGS):
    X, y = [], []
    for i in range(lags, len(data)):
        X.append(data[i - lags:i]); y.append(data[i])
    X, y = np.array(X), np.array(y)
    return X.reshape(X.shape[0], -1), y


def sklearn_models():
    return {"RandomForest": RandomForestRegressor(n_estimators=200, random_state=42),
            "GBDT": GradientBoostingRegressor(random_state=42),
            "LinearRegression": LinearRegression()}


def main() -> int:
    from neuralforecast import NeuralForecast
    from neuralforecast.models.nhits import NHITS
    from neuralforecast.models.patchtst import PatchTST
    from prophet import Prophet
    from prophet.serialize import model_to_json

    MODELS.mkdir(parents=True, exist_ok=True); RESULTS.mkdir(parents=True, exist_ok=True)
    import os; os.chdir(ROOT / "training")      # Lightning writes training/lightning_logs/ here
    ts = pd.read_csv(DATA, index_col="datetime", parse_dates=True)[["value"]].sort_index()
    train, val, test = ts.iloc[:N_TRAIN], ts.iloc[N_TRAIN:N_TRAIN + N_VAL], ts.iloc[N_TRAIN + N_VAL:]
    print(f"train {train.shape}, val {val.shape}, test {test.shape}")

    scaler = MinMaxScaler()
    tr_s = scaler.fit_transform(train); va_s = scaler.transform(val); te_s = scaler.transform(test)
    X_tr, y_tr = lagged(tr_s)
    X_va, y_va = lagged(np.concatenate([tr_s[-LAGS:], va_s]))
    X_te, _ = lagged(np.concatenate([tr_s[-LAGS:], va_s, te_s]))
    inv = lambda a: scaler.inverse_transform(np.asarray(a).reshape(-1, 1)).ravel()
    df_nf = ts.reset_index().rename(columns={"datetime": "ds", "value": "y"})
    df_nf["unique_id"] = "series_1"

    # ── A. validation benchmark (cell 14) ─────────────────────────────────────
    val_rows = {}
    for name, m in sklearn_models().items():
        t0 = time.time(); m.fit(X_tr, y_tr.ravel()); tt = time.time() - t0
        t0 = time.time(); p = m.predict(X_va); it = time.time() - t0
        val_rows[name] = {"MAE_orig": mean_absolute_error(inv(y_va), inv(p)),
                          "MAE_norm": mean_absolute_error(y_va, p), "train_time": tt, "infer_time": it}
    t0 = time.time()
    pm = Prophet(stan_backend="CMDSTANPY").fit(train.reset_index().rename(columns={"datetime": "ds", "value": "y"}))
    tt = time.time() - t0
    t0 = time.time(); fc = pm.predict(val.reset_index().rename(columns={"datetime": "ds", "value": "y"})); it = time.time() - t0
    yp = fc["yhat"].values
    val_rows["Prophet"] = {"MAE_orig": mean_absolute_error(val.values.ravel(), yp),
                           "MAE_norm": mean_absolute_error(scaler.transform(val.values).ravel(),
                                                           scaler.transform(yp.reshape(-1, 1)).ravel()),
                           "train_time": tt, "infer_time": it}
    for cls in (NHITS, PatchTST):
        t0 = time.time()
        nf = NeuralForecast(models=[cls(input_size=LAGS, h=len(val), max_steps=MAX_STEPS)], freq="5min")
        nf.fit(df=df_nf.iloc[:N_TRAIN]); tt = time.time() - t0
        t0 = time.time(); f = nf.predict(); it = time.time() - t0
        col = [c for c in f.columns if c not in ("unique_id", "ds")][0]
        yp = f[col].values; yt = df_nf.iloc[N_TRAIN:N_TRAIN + len(val)]["y"].values
        val_rows[cls.__name__] = {"MAE_orig": mean_absolute_error(yt, yp),
                                  "MAE_norm": mean_absolute_error(scaler.transform(yt.reshape(-1, 1)).ravel(),
                                                                  scaler.transform(yp.reshape(-1, 1)).ravel()),
                                  "train_time": tt, "infer_time": it}
    V = pd.DataFrame(val_rows).T.sort_values("MAE_norm"); V.index.name = "model"
    V.to_csv(RESULTS / "validation_metrics.csv")
    print("\n=== A. validation MAE (legend values) ===\n" + V.round(6).to_string())

    # ── B. final models (cell 16): train, save, predict the test period ──────
    preds = {}
    for name, m in sklearn_models().items():
        m.fit(X_tr, y_tr.ravel())
        preds[name] = inv(m.predict(X_te))
        joblib.dump(m, MODELS / f"{name}.joblib")
    joblib.dump(scaler, MODELS / "minmax_scaler.joblib")

    pm = Prophet(stan_backend="CMDSTANPY").fit(
        pd.concat([train, val]).reset_index().rename(columns={"datetime": "ds", "value": "y"}))
    preds["Prophet"] = pm.predict(test.reset_index().rename(columns={"datetime": "ds", "value": "y"}))["yhat"].values
    (MODELS / "Prophet.json").write_text(model_to_json(pm))

    for cls in (NHITS, PatchTST):
        nf = NeuralForecast(models=[cls(input_size=LAGS, h=N_TEST, max_steps=MAX_STEPS)], freq="5min")
        nf.fit(df=df_nf.iloc[:N_TRAIN + N_VAL])
        f = nf.predict(); col = [c for c in f.columns if c not in ("unique_id", "ds")][0]
        preds[cls.__name__] = f.query("unique_id=='series_1'")[col].values
        nf.save(path=str(MODELS / cls.__name__), overwrite=True, save_dataset=False)

    P = pd.DataFrame({"truth": test["value"].values}, index=test.index)
    for name, p in preds.items():
        P[name] = np.asarray(p)[-len(test):]            # notebook alignment
    P.to_csv(RESULTS / "test_predictions.csv")

    # test metrics: full test (scaled with the train scaler) and the plotted window (/ window max)
    w = P.loc[WINDOW[0]:WINDOW[1]]; wmax = w["truth"].max()
    T = pd.DataFrame({m: {"MAE_test_orig": mean_absolute_error(P.truth, P[m]),
                          "MAE_test_norm": mean_absolute_error(scaler.transform(P[["truth"]].values).ravel(),
                                                               scaler.transform(P[[m]].values).ravel()),
                          "MAE_window_norm": mean_absolute_error(w.truth / wmax, w[m] / wmax)}
                      for m in preds}).T.sort_values("MAE_window_norm")
    T.index.name = "model"
    T.to_csv(RESULTS / "test_metrics.csv")
    print("\n=== B. test MAE (what the plotted predictions actually score) ===\n" + T.round(6).to_string())
    (RESULTS / "run_info.json").write_text(json.dumps({
        "window": WINDOW, "window_max": float(wmax), "lags": LAGS, "max_steps": MAX_STEPS,
        "n_train": N_TRAIN, "n_val": N_VAL, "n_test_points": len(test)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
