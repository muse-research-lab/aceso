#!/usr/bin/env python3
"""Build the training series from the raw Azure Functions trace.

    python data/prepare_data.py

Input : data/raw/AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt.gz  (or the plain .txt)
        (Azure Functions invocation trace, two weeks, Jan 2021; one row per invocation:
         app, func, end_timestamp [s], duration [s])
        The repository ships the gzipped trace; pandas reads it directly, so there is
        nothing to unpack.  An uncompressed .txt next to it is used in preference.
Steps : identical to the original notebook (final_version.ipynb, cells 0-2):
        1. parse end_timestamp -> datetime
        2. keep 11 hand-picked (app, func) pairs  (filter_top_functions)
        3. count invocations per 5-minute bin per function  (build_timeseries)
        4. keep function c8c43e_653cdb
Output: data/timeseries_c8c43e_653cdb.csv      datetime, value  (invocations per 5 min)
        data/split_{train,val,test}.csv          7 / 3 / 4 days, as used for training

Note: the pivot only has rows for 5-min bins in which at least one of the 11 functions was
invoked, so the series has 4,029 points instead of 14 x 288 = 4,032 (3 bins are absent).
The splits are made by POSITION (7x288, 3x288, rest), exactly as in the notebook.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RAW_TXT = HERE / "raw" / "AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt"
RAW = RAW_TXT if RAW_TXT.exists() else RAW_TXT.with_suffix(".txt.gz")
FUNC_ID = "c8c43e_653cdb"
PREFIXES = {("a594f9", "155e47"), ("7958f8", "cc5bb2"), ("70b9ce", "30aa43"), ("5fb02c", "8e5f53"),
            ("d27353", "905e66"), ("734272", "9b61fd"), ("17c37a", "c9f8e3"), ("734272", "556ccf"),
            ("b1034a", "7b0f28"), ("938e7f", "6b2db9"), ("c8c43e", "653cdb")}
POINTS_PER_DAY = 288


def main():
    df = pd.read_csv(RAW, sep=",", dtype={"app": str, "func": str,
                                          "end_timestamp": float, "duration": float})
    df["datetime"] = pd.to_datetime(df["end_timestamp"], unit="s")
    keep = [(a[:6], f[:6]) in PREFIXES for a, f in zip(df["app"], df["func"])]
    df = df[keep]
    ts = (df.groupby([pd.Grouper(key="datetime", freq="5min"), "app", "func"])
            .agg(invocations=("duration", "count")).reset_index())
    ts["func_id"] = ts["app"].str[:6] + "_" + ts["func"].str[:6]
    wide = ts.pivot_table(index="datetime", columns="func_id", values="invocations",
                          fill_value=0).sort_index()
    s = wide[FUNC_ID].astype(float).rename("value")
    s.index.name = "datetime"
    s.to_frame().to_csv(HERE / f"timeseries_{FUNC_ID}.csv")
    n_train, n_val = 7 * POINTS_PER_DAY, 3 * POINTS_PER_DAY
    s.iloc[:n_train].to_frame().to_csv(HERE / "split_train.csv")
    s.iloc[n_train:n_train + n_val].to_frame().to_csv(HERE / "split_val.csv")
    s.iloc[n_train + n_val:].to_frame().to_csv(HERE / "split_test.csv")
    print(f"{FUNC_ID}: {len(s)} points, {s.index.min()} .. {s.index.max()}; "
          f"train {n_train}, val {n_val}, test {len(s) - n_train - n_val}")


if __name__ == "__main__":
    main()
