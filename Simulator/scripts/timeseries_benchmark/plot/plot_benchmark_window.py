#!/usr/bin/env python3
"""Plot the normalized one-day window of test predictions (timeseries_benchmark_normalized_window_plot.pdf).

    python plot/plot_benchmark_window.py [--legend-mae validation|original|test_window]

Reads results/test_predictions.csv and results/validation_metrics.csv written by training/train.py.
Styling is identical to final_version.ipynb (cell 16): window 1970-01-13 05:00 .. 1970-01-14 04:00,
every curve divided by the window's maximum true value, same colours, ticks and marker lines.

Legend MAE:
  validation   (default) MAE_norm on the validation days, read from results/validation_metrics.csv
               -- what the original legend showed (the notebook typed these numbers in by hand)
  original     the exact numbers printed in the original figure
  test_window  MAE of the plotted curves themselves (window, / window max), from results/test_metrics.csv
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
START, END = "1970-01-13 05:00", "1970-01-14 04:00"
ORIGINAL_MAE = {"GBDT": 0.039261, "RandomForest": 0.040640, "LinearRegression": 0.041352,
                "Prophet": 0.049394, "NHITS": 0.055602, "PatchTST": 0.065310}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legend-mae", default="validation", choices=["validation", "original", "test_window"])
    ap.add_argument("--out", default=str(ROOT / "plot" / "timeseries_benchmark_normalized_window_plot.pdf"))
    a = ap.parse_args()

    P = pd.read_csv(ROOT / "results" / "test_predictions.csv", index_col="datetime", parse_dates=True)
    if a.legend_mae == "validation":
        mae = pd.read_csv(ROOT / "results" / "validation_metrics.csv", index_col="model")["MAE_norm"].to_dict()
    elif a.legend_mae == "test_window":
        mae = pd.read_csv(ROOT / "results" / "test_metrics.csv", index_col="model")["MAE_window_norm"].to_dict()
    else:
        mae = ORIGINAL_MAE

    w = P.loc[START:END]
    norm = w / w["truth"].max()                  # every curve divided by the window's max true value

    palette = sns.color_palette("colorblind")
    color = {"GBDT": palette[3], "RandomForest": palette[2], "LinearRegression": palette[7],
             "Prophet": palette[4], "NHITS": palette[5], "PatchTST": palette[8]}

    plt.figure(figsize=(9, 4))
    sns.set_style("whitegrid")
    plt.plot(norm.index, norm["truth"].values, color="black", linewidth=2, label="Ground Truth")
    for m in ["GBDT", "RandomForest", "LinearRegression", "Prophet", "NHITS", "PatchTST"]:
        plt.plot(norm.index, norm[m].values, color=color[m], label=f"{m} (MAE={mae[m]:.3f})")

    ax = plt.gca()
    base_ts = pd.to_datetime(START)
    for h in [10, 11, 15, 16, 18, 19, 21]:
        plt.axvline(x=base_ts + pd.to_timedelta(h, unit="h"), color="grey", linestyle=":", linewidth=2, alpha=0.8)
    hours = list(range(0, 25, 4))
    ticks = [base_ts + pd.to_timedelta(h, unit="h") for h in hours]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{h:02d}:00" for h in hours], fontsize=15)
    ax.set_xlim(ticks[0], ticks[-1])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1]); ax.set_yticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=15)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Time (Hours)", fontsize=15); ax.set_ylabel("Requests", fontsize=15)
    plt.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=15)
    plt.grid(False)
    plt.tight_layout()
    plt.savefig(a.out, dpi=200)
    print("saved", a.out, "| legend MAE:", a.legend_mae)


if __name__ == "__main__":
    main()
