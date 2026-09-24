#!/usr/bin/env python3
"""
    python plotter.py                  # all figures into plots/
    python plotter.py --only 8a 9b     # just some of them
    python plotter.py --root ../aceso-ae-test --out /tmp/figs

Same inputs, same computations and same styling as the notebook; each figure is written to
plots/<name>.pdf exactly as before.  Paths are resolved relative to --root (the folder holding
this script by default), so the script can be started from anywhere.

Inputs (relative to --root):
    workload-timeseries.csv                                  hourly workload buckets
    Simulator/scripts/results/baseline_results.csv           Figures 8(a)-(d), Table 2
    Simulator/scripts/results/scalability_results.csv        Figures 9(a), 9(b)
    Simulator/scripts/results/region_filtering_results.csv   Figure 6a
    Simulator/scripts/results/weight_sensitivity_results.csv Figure 12(a)
    Simulator/scripts/results/generalizability_results.csv   Figure 12(b)
    Simulator/scripts/timeseries_benchmark/results/*.csv     Figure 11
Figure 10 needs no input; it is computed from the search-space formulas.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# shared setup
# ---------------------------------------------------------------------------
METHODS = ['caribou', 'ga', 'aceso', 'lp']
DESIRED_ORDER = ["Aceso", "Caribou", "GA", "Nautilus", "LP"]
NAME_MAP = {'aceso': 'Aceso', 'caribou': 'Caribou', 'ga': 'GA',
            'nautilus': 'Nautilus', 'lp': 'LP'}
COLOR_MAP = {'aceso': "moccasin", 'caribou': "sandybrown", 'ga': "#C8685B",
             'nautilus': "#A1393F", 'lp': "#4A1C20"}
RC = {'font.size': 11, 'axes.titlesize': 11, 'axes.labelsize': 11,
      'xtick.labelsize': 11, 'ytick.labelsize': 11}


def load_methods(root: Path) -> pd.DataFrame:
    """baseline_results.csv with the method name and load bucket parsed out."""
    df = pd.read_csv(root / 'Simulator' / 'scripts' / 'results' / 'baseline_results.csv')
    df['method'] = df['experiment_id'].str.split('-').str[0]
    df['bucket'] = df['experiment_id'].apply(
        lambda x: int(m.group(1)) if (m := re.search(r'load(\d+)', x)) else None)
    return df


def load_timeseries(root: Path) -> pd.DataFrame:
    return pd.read_csv(root / 'workload-timeseries.csv', parse_dates=['datetime'])


def hourly(timeseries_df: pd.DataFrame, column: str = 'bucket_pred') -> pd.DataFrame:
    """Hourly frame holding the max bucket of each hour (notebook: resample('h'))."""
    return timeseries_df.resample('h', on='datetime').agg({column: 'max'}).reset_index()


def per_hour_values(hourly_df: pd.DataFrame, methods_df: pd.DataFrame, column: str,
                    prefix: str, lp_scale: float = 1.0) -> pd.DataFrame:
    """Map each hour's bucket to the per-bucket mean of `column`; LP is one value everywhere."""
    for method in METHODS:
        sub = methods_df[methods_df['method'] == method]
        if method == 'lp':
            hourly_df[f'{prefix}_lp'] = sub[column].mean() * lp_scale
        else:
            lookup = sub.groupby('bucket')[column].mean().to_dict()
            hourly_df[f'{prefix}_{method}'] = hourly_df['bucket_pred'].map(lookup)
    return hourly_df


def ordered(df: pd.DataFrame) -> pd.DataFrame:
    """Add the pretty label and sort into the figures' bar order."""
    df['method_pretty'] = pd.Categorical(df['method'].map(NAME_MAP),
                                         categories=DESIRED_ORDER, ordered=True)
    return df.sort_values('method_pretty')


def parse_assignment(assignment_str) -> dict:
    """Parse assignment string 'msX:regionA; msY:regionB' into a dict."""
    if pd.isna(assignment_str):
        return {}
    assignments = {}
    for part in assignment_str.split(';'):
        if ':' in part:
            ms, region = part.split(':')
            assignments[ms.strip()] = region.strip()
    return assignments


def count_per_region(assignment_str) -> dict:
    """Return {region: count} for one assignment string."""
    counts = {}
    for region in parse_assignment(assignment_str).values():
        counts[region] = counts.get(region, 0) + 1
    return counts


def bar_figure(df: pd.DataFrame, values: str, ylabel: str, figsize, ylim, fmt,
               out: Path, label_rotation: int = 0):
    """The bar chart shared by Figures 8(a)-(d): value labels on top, x labels rotated 35."""
    import matplotlib.pyplot as plt

    plt.rcParams.update(RC)
    plt.figure(figsize=figsize)
    bars = plt.bar(df['method_pretty'], df[values],
                   color=[COLOR_MAP[m] for m in df['method']])
    plt.ylabel(ylabel)
    plt.ylim(*ylim)
    for bar, method, value in zip(bars, df['method'], df[values]):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), fmt(method, value),
                 ha='center', va='bottom', fontsize=11, rotation=label_rotation)
    plt.xticks(rotation=35)
    plt.tight_layout()
    save(out)


def text_figure(blocks: list[list[str]], out: Path):
    """Render monospaced text blocks on one letter-size page (Table 2 and Figure 6a)."""
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor('white')
    line_height_frac = 0.022
    y = 0.98
    for lines in blocks:
        fig.text(0.02, y, "\n".join(lines), va='top', ha='left',
                 family='monospace', fontsize=9)
        y -= line_height_frac * len(lines) + 0.05
    plt.axis('off')
    save(out, facecolor='white')


def save(out: Path, **kwargs):
    import matplotlib.pyplot as plt

    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, bbox_inches="tight", **kwargs)
    print("saved", out)


# ---------------------------------------------------------------------------
# Figures 8(a)-(d): carbon, cost, latency and solve time per method
# ---------------------------------------------------------------------------
def figure_8a(root: Path, out_dir: Path):
    methods_df = load_methods(root)
    methods_df['carbon_emissions_g'] = (methods_df['carbon_emissions_g']
                                        .astype(str).str.replace('g', '', regex=False).astype(float))
    hourly_df = per_hour_values(hourly(load_timeseries(root)), methods_df,
                                'carbon_emissions_g', 'carbon')

    agg = {m: hourly_df[f'carbon_{m}'].sum() / 10000 for m in METHODS}
    baseline_total = 1.0
    df = pd.DataFrame({'method': METHODS + ['nautilus'],
                       'total_carbon': [agg[m] for m in METHODS] + [baseline_total]})
    df['value_vs_nautilus'] = df['total_carbon'] / baseline_total
    df = ordered(df)

    bar_figure(df, 'value_vs_nautilus', "Normalized AVG\nCE (x Nautilus)", (3.0, 2),
               (0.35, df['value_vs_nautilus'].max() * 1.13),
               lambda m, v: f"{v:.2f}", out_dir / "Figure-8(a).pdf")


def figure_8b(root: Path, out_dir: Path):
    methods_df = load_methods(root)
    methods_df['total_cost_usd'] = (methods_df['total_cost_usd'].astype(str)
                                    .str.replace('$', '', regex=False)
                                    .str.replace('USD', '', regex=False)
                                    .str.replace('g', '', regex=False)
                                    .str.strip().astype(float))
    hourly_df = per_hour_values(hourly(load_timeseries(root)), methods_df,
                                'total_cost_usd', 'cost')

    avg = {m: hourly_df[f'cost_{m}'].mean() / 100 for m in METHODS}
    baseline_avg = 1.0
    df = pd.DataFrame({'method': METHODS + ['nautilus'],
                       'avg_cost': [avg[m] for m in METHODS] + [baseline_avg]})
    df['value_vs_nautilus'] = df['avg_cost'] / baseline_avg
    df = ordered(df)

    vmax, vmin = df['value_vs_nautilus'].max(), df['value_vs_nautilus'].min()
    bar_figure(df, 'value_vs_nautilus', "Normalized AVG\nCost (x Nautilus)", (3.5, 2),
               (vmin * 0.97, vmax * 1.05),
               lambda m, v: f"{v:.3f}", out_dir / "Figure-8(b).pdf")


def figure_8c(root: Path, out_dir: Path):
    methods_df = load_methods(root)
    methods_df['total_latency_s'] = (methods_df['total_latency_ms'].astype(str)
                                     .str.replace(',', '', regex=False)
                                     .astype(float).div(1000.0).round(3))
    # the notebook doubles the single LP experiment's latency
    hourly_df = per_hour_values(hourly(load_timeseries(root)), methods_df,
                                'total_latency_s', 'latency', lp_scale=2)

    agg = {m: hourly_df[f'latency_{m}'].mean() for m in METHODS}
    df = pd.DataFrame({'method': METHODS + ['nautilus'],
                       'avg_latency': [agg[m] for m in METHODS] + [0.34]})
    df = ordered(df)

    vmax, vmin = df['avg_latency'].max(), df['avg_latency'].min()
    bar_figure(df, 'avg_latency', "AVG Latency (s)", (3.0, 2), (vmin * 0.6, vmax * 1.15),
               lambda m, v: f"{v:.2f}", out_dir / "Figure-8(c).pdf")


def figure_8d(root: Path, out_dir: Path):
    methods_df = load_methods(root)
    methods_df['solve_time_seconds'] = (methods_df['solve_time_seconds'].astype(str)
                                        .str.replace(',', '', regex=False)
                                        .astype(float).round(3))
    hourly_df = per_hour_values(hourly(load_timeseries(root)), methods_df,
                                'solve_time_seconds', 'solve')

    agg = {m: hourly_df[f'solve_{m}'].mean() for m in METHODS}
    df = ordered(pd.DataFrame({'method': METHODS + ['nautilus'],
                               'avg_solve': [agg[m] for m in METHODS] + [0.0]}))

    def fmt_label(seconds):
        if seconds >= 3600:
            return seconds / 3600.0, "h"
        if seconds >= 60:
            return seconds / 60.0, "m"
        return seconds, "s"

    def label(method, value):
        if method == 'nautilus':
            return "0s"
        display, unit = fmt_label(value)
        return f"{display:.1f}{unit}"

    bar_figure(df, 'avg_solve', "AVG Solve Time", (3.0, 2),
               (0, df['avg_solve'].max() * 1.15), label,
               out_dir / "Figure-8(d).pdf", label_rotation=45)


# ---------------------------------------------------------------------------
# Table 2: microservices per region, and migrations triggered by load changes
# ---------------------------------------------------------------------------
def table_2(root: Path, out_dir: Path):
    methods_df = load_methods(root)
    timeseries_df = load_timeseries(root)
    hourly_df = hourly(timeseries_df)

    def bucket_assignment(method):
        sub = methods_df[methods_df['method'] == method]
        return sub.dropna(subset=['bucket']).groupby('bucket')['assignment'].first().to_dict()

    # --- (a) average microservices per region ------------------------------
    region_avgs = {}
    for method in ['aceso', 'caribou', 'ga']:
        assignments = hourly_df['bucket_pred'].map(bucket_assignment(method)).tolist()
        totals, hours_counted = {}, 0
        for a in assignments:
            if not isinstance(a, str):
                continue
            counts = count_per_region(a)
            if not counts:
                continue
            for region, c in counts.items():
                totals[region] = totals.get(region, 0) + c
            hours_counted += 1
        region_avgs[method] = ({r: totals[r] / hours_counted for r in totals}
                               if hours_counted > 0 else {})

    # LP: read from file (load5 broadcast to all buckets), same as the other figures
    lp_sub = methods_df[methods_df['method'] == 'lp']
    region_avgs['lp'] = {}
    if not lp_sub.empty and lp_sub['assignment'].notna().any():
        region_avgs['lp'] = {r: float(c) for r, c
                             in count_per_region(lp_sub['assignment'].dropna().iloc[0]).items()}
    region_avgs['nautilus'] = {'Frankfurt': 100.0}                 # dummy 100% Frankfurt

    # --- (b) load-change-triggered migrations ------------------------------
    hourly_buckets = hourly(timeseries_df, 'bucket_true')
    results = {}
    for method in ['aceso', 'ga']:                                 # Caribou & LP removed
        assignments = hourly_buckets['bucket_true'].map(bucket_assignment(method)).tolist()
        loads = hourly_buckets['bucket_true'].tolist()

        load_change_indices = [i for i in range(1, len(loads)) if loads[i] != loads[i - 1]]
        total_load_changes = len(load_change_indices)

        migration_counts = []
        prev = parse_assignment(assignments[0]) if assignments else {}
        for i in load_change_indices:
            current = parse_assignment(assignments[i])
            all_ms = set(prev.keys()) | set(current.keys())
            moved = sum(current.get(ms, prev.get(ms)) != prev.get(ms) for ms in all_ms)
            if moved > 0:
                migration_counts.append(moved)
            prev = current

        results[method] = {
            "total_load_changes": total_load_changes,
            "adaptation_rate": ((len(migration_counts) / total_load_changes) * 100
                                if total_load_changes > 0 else 0),
            "avg_ms_moved_per_trigger": np.mean(migration_counts) if migration_counts else 0,
        }

    # --- text blocks -------------------------------------------------------
    lines_2a = ["Average microservices per region", "=" * 50, ""]
    for method in ['aceso', 'caribou', 'ga', 'nautilus', 'lp']:
        lines_2a.append(f"{NAME_MAP[method]}:")
        if region_avgs[method]:
            lines_2a += [f"  {region}: {avg:.1f}" for region, avg in region_avgs[method].items()]
        else:
            lines_2a.append("  (no data)")
        lines_2a.append("")

    lines_2b = ["LOAD-CHANGE TRIGGERED MIGRATION ANALYSIS", "=" * 60, ""]
    for method, r in results.items():
        rate, moved = r['adaptation_rate'], r['avg_ms_moved_per_trigger']
        lines_2b.append(f"Method: {NAME_MAP.get(method, method)}")
        lines_2b.append(f"  Total load changes: {r['total_load_changes']}")
        lines_2b.append(f"  Adaptation rate: {rate}" if isinstance(rate, str)
                        else f"  Adaptation rate: {rate:.1f}%")
        lines_2b.append(f"  Avg microservices moved per triggering event: {moved}%"
                        if isinstance(moved, str) else
                        f"  Avg microservices moved per triggering event: {moved:.2f}")
        lines_2b.append("")

    text_figure([lines_2a, lines_2b], out_dir / "Table-2.pdf")


# ---------------------------------------------------------------------------
# Figures 9(a)/9(b): scalability of the solver
# ---------------------------------------------------------------------------
EU = {"Paris", "Stockholm", "London", "Spain", "Ireland", "Milan"}
EU_US = EU | {"Northern Virginia", "Ohio", "Mexico City", "Montreal", "Calgary",
              "Northern California"}


def _scalability_axes(avg_data, series_labels, colors, hlines, hlabels, out: Path,
                      ylim_top: float):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    methods = ["10", "100", "1000"]
    x = np.arange(len(methods))
    width = 0.25

    plt.figure(figsize=(3.5, 2.5))
    for i, label in enumerate(series_labels):
        plt.bar(x + (i - 1) * width, [avg_data[m][i] for m in methods], width,
                label=label, color=colors[i])

    plt.xticks(x, methods, fontsize=12, rotation=15)
    plt.ylabel("AVG Solve Time (s)", fontsize=12)
    plt.xlabel("Number of Microservices", fontsize=12)

    for y in hlines:
        plt.axhline(y=y, linestyle='--', linewidth=0.8, color='gray')
    for y, text, va in hlabels:
        plt.text(-0.4, y, text, color="gray", fontsize=12, va=va)

    plt.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), ncol=1, fontsize=12, frameon=True)
    plt.yscale('log')
    plt.gca().yaxis.set_major_locator(ticker.FixedLocator([1, 10, 100]))
    plt.gca().yaxis.set_minor_locator(ticker.NullLocator())
    plt.yticks([1, 10, 100], ["1", "10", "100"], fontsize=12)
    plt.ylim(0, ylim_top)
    plt.tight_layout()
    save(out)


def figure_9a(root: Path, out_dir: Path):
    """Solve time by candidate-region set, for the three fastest runs of each configuration."""
    df = pd.read_csv(root / "Simulator" / "scripts" / "results" / "scalability_results.csv")
    df = df.sort_values("solve_time").groupby(["num_ms", "slo", "candidate_regions"],
                                              as_index=False).head(3)
    regions = ["EU", "EU+US", "All"]
    slo_map = {"10": 1650, "100": 1650, "1000": 7000}

    avg_data = {}
    for m in ["10", "100", "1000"]:
        sub = df[(df["num_ms"] == int(m)) & (df["slo"] == slo_map[m])]
        avg_data[m] = []
        for region in regions:
            if region == "EU":
                mask = sub["candidate_regions"].apply(lambda r: set(r.split("|")) == EU)
            elif region == "EU+US":
                mask = sub["candidate_regions"].apply(lambda r: set(r.split("|")) == EU_US)
            else:
                mask = sub["candidate_regions"].apply(lambda r: set(r.split("|")) not in (EU, EU_US))
            avg_data[m].append(sub.loc[mask, "solve_time"].mean())

    _scalability_axes(avg_data, regions, ["#99C8FF", "#2C7BFF", "#004E9E"],
                      [0.5, 15, 180],
                      [(15, "15 s", 'bottom'), (0.5, "0.5 s", 'bottom'), (180, "3 min", 'top')],
                      out_dir / "Figure-9(a).pdf", ylim_top=3.9 * 60)


def figure_9b(root: Path, out_dir: Path):
    """Solve time by SLO tightness, for the three fastest runs of each configuration."""
    df = pd.read_csv(root / "Simulator" / "scripts" / "results" / "scalability_results.csv")
    df = df.sort_values("solve_time").groupby(["num_ms", "slo"], as_index=False).head(3)
    regions = ["Relaxed", "Medium", "Strict"]

    avg_data = {}
    for m in ["10", "100", "1000"]:
        sub = df[df["num_ms"] == int(m)]
        slos = sorted(sub["slo"].unique())
        # Relaxed = smallest SLO, Strict = largest, Medium = in-between
        slo_map = {"Relaxed": slos[0], "Medium": slos[1], "Strict": slos[-1]}
        avg_data[m] = [sub.loc[sub["slo"] == slo_map[r], "solve_time"].mean() for r in regions]

    _scalability_axes(avg_data, regions, ["#99C8FF", "#2C7BFF", "#004E9E"],
                      [0.5, 10, 3 * 60],
                      [(10, "10 s", 'bottom'), (0.5, "0.5 s", 'bottom'), (3 * 60, "3 min", 'top')],
                      out_dir / "Figure-9(b).pdf", ylim_top=3.8 * 60)


# ---------------------------------------------------------------------------
# Figure 6a: which regions survive filtering, and which ones Aceso uses
# ---------------------------------------------------------------------------
def figure_6a(root: Path, out_dir: Path):
    df = pd.read_csv(root / 'Simulator' / 'scripts' / 'results' / 'region_filtering_results.csv')

    lines_block1 = ["Filtered Regions", "=" * 60, ""]
    for city in ['Frankfurt', 'Calgary', 'Hong Kong']:
        row = df[df['base_region'] == city]
        if row.empty:
            lines_block1 += [f"{city}: Not found in CSV", ""]
            continue
        regions = [r.strip() for r in row['filtered_regions'].values[0].split(',')]
        regions = [r for r in regions if r != city]
        lines_block1 += [f"{city} ({len(regions)} filtered regions):", f"  {regions}", ""]

    lines_block2 = ["Used Regions", "=" * 60, ""]
    for region in ['Aceso-Frankfurt', 'Aceso-Calgary', 'Aceso-Hong Kong']:
        row = df[df['base_region'] == region]
        lines_block2.append(f"Used regions for {region}:")
        if row.empty:
            lines_block2 += ["  Not found in CSV", ""]
            continue
        regions = [r.strip() for r in row['filtered_regions'].values[0].split(',')]
        base_city = region.split('-', 1)[1] if '-' in region else region
        regions = [r for r in regions if r != base_city]
        lines_block2 += [f"  {', '.join(regions)}", ""]

    text_figure([lines_block1, lines_block2], out_dir / "Figure-6a.pdf")


# ---------------------------------------------------------------------------
# Figure 10: search space with and without pruning (formulas, no input file)
# ---------------------------------------------------------------------------
def figure_10(root: Path, out_dir: Path):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    MS_values = [10, 100, 1000]
    categories = ["Aceso", "W/o MS pruning", "W/o Region pruning", "W/o both"]
    colors = ["#DCEEB5", "#9ABB52", "#628F32", "#2C4A18"]

    # pinned MS * movable MS * # of candidate regions * MS size
    # pinned MS is always 20% (DBs, frontends etc.); 20% movable MS due to tight SLO
    # candidate regions after filtering: 5 for Frankfurt vs 33 unfiltered
    formulas = [lambda MS: 0.8 * 0.2 * 5 * MS,        # Aceso
                lambda MS: 0.8 * 1 * 5 * MS,          # W/o MS pruning
                lambda MS: 0.8 * 0.2 * 33 * MS,       # W/o region pruning
                lambda MS: 0.8 * 1 * 33 * MS]         # W/o both
    values = np.array([[f(MS) for f in formulas] for MS in MS_values])   # shape (3, 4)

    bar_width = 0.2
    x = np.arange(len(MS_values))
    fig, ax = plt.subplots(figsize=(6, 2.5))

    for i, category in enumerate(categories):
        bars = ax.bar(x + i * bar_width, values[:, i], width=bar_width,
                      color=colors[i], label=category)
        for j, (bar, val) in enumerate(zip(bars, values[:, i])):
            if i == 0 and j == 0:                      # Aceso at 10 MS: label above the bar
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{val:.0f}',
                        ha='center', va='bottom', color='black', fontsize=12, rotation=90)
            else:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 4, f'{val:.0f}',
                        ha='center', va='center', color='white' if i > 1 else 'black',
                        fontsize=12, rotation=90)

    ax.set_xlabel("Microservice Size", fontsize=12)
    ax.set_ylabel("Search Space", fontsize=12)
    ax.set_xticks(x + bar_width * 1.5)
    ax.set_xticklabels(MS_values, fontsize=12)
    plt.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), ncol=1, fontsize=12, frameon=True)
    plt.yscale('log')
    plt.gca().yaxis.set_major_locator(ticker.FixedLocator([1, 10, 100]))
    plt.gca().yaxis.set_minor_locator(ticker.NullLocator())
    plt.yticks([10, 100, 1000, 10000], [r'$10^1$', r'$10^2$', r'$10^3$', r'$10^4$'], fontsize=12)
    plt.tight_layout()
    save(out_dir / "Figure-10.pdf")


# ---------------------------------------------------------------------------
# Figure 12(a): carbon/cost as the objective weights change
# ---------------------------------------------------------------------------
def figure_12a(root: Path, out_dir: Path):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # average duplicates by (region, carbon_weight, cost_weight)
    buckets = defaultdict(lambda: {'carbon': [], 'cost': []})
    with open(root / 'Simulator' / 'scripts' / 'results' / 'weight_sensitivity_results.csv') as f:
        for row in csv.DictReader(f):
            key = (row['base_region'].strip(), float(row['carbon_weight']), float(row['cost_weight']))
            buckets[key]['carbon'].append(float(row['carbon_remaining_pct']) / 100.0)
            buckets[key]['cost'].append(float(row['cost_remaining_pct']) / 100.0)
    data = {k: {'carbon': sum(v['carbon']) / len(v['carbon']),
                'cost': sum(v['cost']) / len(v['cost'])} for k, v in buckets.items()}

    weight_configs = [(1.0, 0.0), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.0, 1.0)]
    weight_labels = ['(1,0)', '(0.75,0.25)', '(0.5,0.5)', '(0.25,0.75)', '(0,1)']

    def series(region, field):                      # default 1.0 if missing
        return [data.get((region, cw, kw), {}).get(field, 1.0) for cw, kw in weight_configs]

    fig, ax = plt.subplots(figsize=(2.5, 2.6))
    ax.spines['top'].set_visible(False)
    for region, style in [('Frankfurt', '-'), ('Hong Kong', '--')]:   # solid / dashed
        ax.plot(weight_labels, series(region, 'carbon'), 'o' + style, color='#9ABB52',
                linewidth=2, markersize=6, label='Carbon' if style == '-' else '_nolegend_')
        ax.plot(weight_labels, series(region, 'cost'), 'o' + style, color='#A9CCE3',
                linewidth=2, markersize=6, label='Cost' if style == '-' else '_nolegend_')

    ax.set_xlabel('Weights (Carbon, Cost)', fontsize=10)
    ax.set_ylabel('Norm. AVG Carbon &\nCost (x Base Region)', fontsize=10)
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_xticks(range(len(weight_labels)))
    ax.set_xticklabels(weight_labels, rotation=25, ha='right', fontsize=10)
    ax.set_yticks(np.arange(0.6, 1.01, 0.1))
    ax.set_ylim(0.4, 1)

    legend1 = ax.legend(handles=[
        Line2D([0], [0], color='#9ABB52', linewidth=2, marker='o', markersize=6, label='Carbon'),
        Line2D([0], [0], color='#A9CCE3', linewidth=2, marker='o', markersize=6, label='Cost'),
    ], loc='best', fontsize=9)
    ax.add_artist(legend1)
    legend1.set_bbox_to_anchor((1, 0.75))

    legend2 = ax.legend(handles=[
        Line2D([0], [0], color='gray', linewidth=2, linestyle='-', label='Frankfurt'),
        Line2D([0], [0], color='gray', linewidth=2, linestyle='--', label='Hong Kong'),
    ], loc='lower right', fontsize=9)
    legend2.set_bbox_to_anchor((1, 0.06))

    for tick in ax.get_xticklabels():               # colour the dominant-weight labels
        t = tick.get_text()
        tick.set_color('#628F32' if t == '(1,0)' else '#5499C7' if t == '(0,1)' else 'black')

    plt.tight_layout()
    save(out_dir / 'Figure-12(a).pdf')


# ---------------------------------------------------------------------------
# Figure 12(b): generalizability across base regions
# ---------------------------------------------------------------------------
REGION_STYLE = {
    # Europe
    'Frankfurt': ('Europe', '#7FA844', '*'), 'Milan': ('Europe', '#7FA844', '*'),
    'Paris': ('Europe', '#7FA844', '*'), 'Spain': ('Europe', '#7FA844', '*'),
    'Ireland': ('Europe', '#7FA844', '*'), 'London': ('Europe', '#7FA844', '*'),
    'Zurich': ('Europe', '#7FA844', '*'), 'Stockholm': ('Europe', '#7FA844', '*'),
    # America
    'Calgary': ('America', '#A9CCE3', 'o'), 'Montreal': ('America', '#A9CCE3', 'o'),
    'Mexico C.': ('America', '#A9CCE3', 'o'), 'Oregon': ('America', '#A9CCE3', 'o'),
    'Northern California': ('America', '#A9CCE3', 'o'), 'Sao Paolo': ('America', '#A9CCE3', 'o'),
    'Ohio': ('America', '#A9CCE3', 'o'), 'Northern Virginia': ('America', '#A9CCE3', 'o'),
    # Asia
    'Hong Kong': ('Asia', '#E6AE65', 's'), 'Hyderabad': ('Asia', '#E6AE65', 's'),
    'Bahrain': ('Asia', '#E6AE65', 's'), 'Israel (Tel Aviv)': ('Asia', '#E6AE65', 's'),
    'Jakarta': ('Asia', '#E6AE65', 's'), 'Kuala Lumpur': ('Asia', '#E6AE65', 's'),
    'Mumbai': ('Asia', '#E6AE65', 's'), 'Osaka': ('Asia', '#E6AE65', 's'),
    'Seoul': ('Asia', '#E6AE65', 's'), 'Singapore': ('Asia', '#E6AE65', 's'),
    'Taipei': ('Asia', '#E6AE65', 's'), 'Thailand': ('Asia', '#E6AE65', 's'),
    'Tokyo': ('Asia', '#E6AE65', 's'), 'UAE (Dubai)': ('Asia', '#E6AE65', 's'),
    # Oceania
    'Auckland': ('Oceania', '#A1393F', 'D'), 'Melbourne': ('Oceania', '#A1393F', 'D'),
    'Sydney': ('Oceania', '#A1393F', 'D'),
    # Africa
    'Cape Town': ('Africa', '#C39BD3', '^'),
    # No change
    'Stockholm, Oregon, Ohio, Northern Virginia': ('NoChange', 'black', 'x'),
}
AREA_STYLES = {
    'Europe': ('*', '#7FA844', 'EU'), 'America': ('o', '#A9CCE3', 'America'),
    'Asia': ('s', '#E6AE65', 'Asia'), 'Oceania': ('D', '#A1393F', 'Oceania'),
    'Africa': ('^', '#C39BD3', 'Africa'), 'NoChange': ('x', 'black', 'No change'),
    'Other': ('o', '#808080', 'Other'),
}


def figure_12b(root: Path, out_dir: Path):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    csv_file = root / 'Simulator' / 'scripts' / 'results' / 'generalizability_results.csv'
    if not csv_file.is_file():
        raise FileNotFoundError(f"Could not find {csv_file}. Please run the optimizer with -gen first.")

    region_values = {}                              # base_region -> [(carbon, cost), ...]
    with open(csv_file, newline='') as f:
        for row in csv.DictReader(f):
            region_values.setdefault(row['base_region'].strip(), []).append(
                (float(row['carbon_remaining_pct']) / 100.0,   # 1.0 == baseline
                 float(row['cost_remaining_pct']) / 100.0))
    if not region_values:
        raise ValueError(f"No data points found in {csv_file}.")

    data_points = {region: (np.array(v)[:, 0].mean(), np.array(v)[:, 1].mean())
                   for region, v in region_values.items()}

    fig, ax = plt.subplots(figsize=(5, 4))
    for base_region, (carbon, cost) in data_points.items():
        area, color, marker = REGION_STYLE.get(base_region, ('Other', '#808080', 'o'))
        ax.scatter(carbon, cost, color=color, marker=marker, s=45,
                   edgecolors='black', linewidth=0.3, zorder=3)
        ax.annotate(f"{base_region}\n{(1 - carbon) * 100:.0f}% Carbon Reduction\n"
                    f"{(1 - cost) * 100:.0f}% Cost Reduction", (carbon, cost), fontsize=9,
                    xytext=(1, 5), textcoords='offset points', ha='left', va='bottom')

    ax.set_xlabel('Norm. AVG Carbon (x Base Region)', fontsize=10)
    ax.set_ylabel('Norm. AVG Cost (x Base Region)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--', zorder=0)

    present_areas = {REGION_STYLE.get(r, ('Other', '#808080', 'o'))[0] for r in data_points}
    legend_elements = [Line2D([0], [0], marker=marker, color='w', markerfacecolor=color,
                              markersize=10, label=label, markeredgecolor='black',
                              markeredgewidth=0.2)
                       for area, (marker, color, label) in AREA_STYLES.items()
                       if area in present_areas]
    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.45, 1.6),
              fontsize=9, framealpha=0.009, ncol=3, columnspacing=0.001,
              handletextpad=0.1, title='Continent of Base Region', title_fontsize=10)
    plt.tight_layout()
    save(out_dir / 'Figure-12(b).pdf')


# ---------------------------------------------------------------------------
# Figure 11: workload forecasting over one day
# ---------------------------------------------------------------------------
START, END = "1970-01-13 05:00", "1970-01-14 04:00"
ORIGINAL_MAE = {"GBDT": 0.039261, "RandomForest": 0.040640, "LinearRegression": 0.041352,
                "Prophet": 0.049394, "NHITS": 0.055602, "PatchTST": 0.065310}


def figure_11(root: Path, out_dir: Path, legend_mae: str = "validation"):
    import matplotlib.pyplot as plt
    import seaborn as sns

    results = root / "Simulator" / "scripts" / "timeseries_benchmark" / "results"
    P = pd.read_csv(results / "test_predictions.csv", index_col="datetime", parse_dates=True)
    if legend_mae == "validation":
        mae = pd.read_csv(results / "validation_metrics.csv", index_col="model")["MAE_norm"].to_dict()
    elif legend_mae == "test_window":
        mae = pd.read_csv(results / "test_metrics.csv", index_col="model")["MAE_window_norm"].to_dict()
    else:
        mae = ORIGINAL_MAE

    w = P.loc[START:END]
    norm = w / w["truth"].max()                  # every curve divided by the window's max truth

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
        plt.axvline(x=base_ts + pd.to_timedelta(h, unit="h"), color="grey",
                    linestyle=":", linewidth=2, alpha=0.8)
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

    # the notebook saved this one with dpi=200 and without bbox_inches
    (out_dir).mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "Figure-11.pdf", dpi=200)
    print("saved", out_dir / "Figure-11.pdf")


FIGURES = {
    "8a": figure_8a, "8b": figure_8b, "8c": figure_8c, "8d": figure_8d,
    "table2": table_2, "9a": figure_9a, "9b": figure_9b, "6a": figure_6a,
    "10": figure_10, "12a": figure_12a, "12b": figure_12b, "11": figure_11,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent),
                    help="folder holding workload-timeseries.csv and Simulator/ (default: this script's folder)")
    ap.add_argument("--out", default=None, help="output folder (default: <root>/plots)")
    ap.add_argument("--only", nargs="+", choices=list(FIGURES), metavar="FIG",
                    help=f"figures to produce; one or more of: {', '.join(FIGURES)}")
    ap.add_argument("--legend-mae", default="validation",
                    choices=["validation", "original", "test_window"],
                    help="which MAE Figure 11 prints in its legend")
    ap.add_argument("--show", action="store_true", help="also open the figures in a window")
    ap.add_argument("--keep-going", action="store_true",
                    help="skip figures whose input files are missing instead of stopping")
    a = ap.parse_args()

    if not a.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # the notebook set these in its first cell and every later figure inherited them,
    # so apply them once here: that way --only gives the same output as a full run
    plt.rcParams.update(RC)

    root = Path(a.root).resolve()
    out_dir = Path(a.out).resolve() if a.out else root / "plots"
    failed = []
    for name in (a.only or list(FIGURES)):
        fn = FIGURES[name]
        try:
            fn(root, out_dir, a.legend_mae) if name == "11" else fn(root, out_dir)
        except (FileNotFoundError, OSError) as e:
            if not a.keep_going:
                raise
            failed.append(f"{name}: {e}")
        finally:
            if not a.show:
                plt.close("all")

    if a.show:
        plt.show()
    for f in failed:
        print("skipped", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
