# Aceso: Latency-Aware Geo-Distribution of Microservices for Cost-Effective Carbon Reduction

**Artifact repository for the paper:**


This repository contains the source code, scripts, and supporting materials required to reproduce the simulation-based experiments presented in:

> **Aceso: Latency-Aware Geo-Distribution of Microservices for Cost-Effective Carbon Reduction**
> Georgia Christofidi (IMDEA Software Institute, Universidad Politécnica de Madrid), Francisco Álvarez-Terribas (Telefonica Research, Universidad Pompeu Fabra), Ioannis Roumpos (IMDEA Software Institute, Universidad Politécnica de Madrid), Nicolas Kourtellis (Keysight Technologies), Jesus Omaña Iglesias (Telefonica Research), Thaleia Dimitra Doudali (IMDEA Software).
> *Proceedings of the ACM International Middleware 2026 Conference*.

The artifact was created specifically to support the experimental evaluation presented in this paper and is intended to facilitate **artifact evaluation, reproducibility, and reuse**.

---

## 📌 Overview

This repository contains the simulation implementation used to obtain the results reported in the paper. Ιt is designed so that the experiments can be automatically reproduced without requiring manual modification of the source code.

In particular, the artifact provides:

* the simulation/source code;
* scripts for executing each of the paper's simulation experiments;
* scripts to automate the execution of all experiments;
* a script and a jupiter notebook for generating the figures reported in the paper;
* simulation input data and workloads required for the experiments;
* documentation describing how the artifact can be used and extended.

---

## 🏆 Artifact Evaluation

This artifact is submitted for evaluation under the following criteria:

* **Artifacts Available**
* **Artifacts Functional**
* **Results Reproduced**

> **For artifact evaluators:** The recommended evaluation path is described in [Getting Started](#-getting-started).

### Artifact availability

A permanent archival copy of this artifact is available at:

**DOI:** <TODO ZENODO DOI>

**Artifact URL:** <TODO PERMANENT ARTIFACT URL>


### Relationship between the artifact and the paper

The artifact corresponds to the simulation and experimental evaluation described in the paper.

The following components of the paper are directly supported by this repository:

| Paper component | Artifact component                        | Reproduction instructions |
| --------------- | ----------------------------------------- | ------------------------- |
| Figure 8        | `<scripts/baselines.sh>`                | [Experiment 1]            |
| Table  2        | `<scripts/baselines.sh>`.               | [Experiment 1]            |
| Figure 9        | `<scripts/scalability.sh>`              | [Experiment 2]            |
| Figure 6a       | `<scripts/region-filter.sh>`            | [Experiment 3]            |
| Figure 10       | `<scripts/region-filter.sh>`            | [Experiment 3]            |
| Figure 12a      | `<scripts/weight-sensitivity.sh>`       | [Experiment 4]            |
| Figure 12b      | `<scripts/generalizability.sh>`         | [Experiment 5]            |
| Figure 11       | `<scripts/timeseries_benchmark/inference/infer.py>` | [Experiment 6]            |


Disclamer: The real-world paper results, which are not reproduced in this artifact, require multiple day access to AWS clusters in 4 different continents and 8 countries. We therefore focus on the reproducibility of all simulation-based results.

---


# 📂 Repository Structure

The main directories and files are organized as follows:

```text
.
├── README.md
├── LICENSE.txt
├── requirements.txt
├── setup.sh
├── workload-timeseries.csv
├── plotter.ipynb
├── plotter.py
├── assets/
├── Simulator/
└── plots/
```

### Top-level files

| File               | Description                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| `README.md`        | This document. It describes the artifact, installation, execution, and reproduction procedures. |
| `LICENSE.txt`          | License governing the use and redistribution of the artifact.                                   |
| `requirements.txt` | Python/software dependencies required by the artifact.                                          |
| `setup.sh`     | Facilitates the installation of necessary python packages for the execution.                                                                         |
| `workload-timeseries.csv`     | Includes a sample of a timeseries of the actual incoming workload and the predicted workload by our gradient boosted decision tree (GBDT)-based traffic prediction model.  This is a sample of the [Azure Functions production traces](https://github.com/Azure/AzurePublicDataset/blob/master/AzureFunctionsInvocationTrace2021.md).                                                                     |
| `plotter.ipynb`  &  `plotter.py`  | These two files are equivalent and reviewers are invited to use either, according to personal preference. They are used to parse the generated results and produce the final figures to directly compare with the paper.                                                       |

### `Simulator/scripts`

Contains the scripts for automating the experiment execution and the main implementation of the simulation.

| File                          | Description                                                                |
| ----------------------------- | -------------------------------------------------------------------------- |
| `runner.sh`                   | Automates the sequential execution of all the following |
| `baselines.sh`                | Runs the comparison between the different baselines compared in the paper. |
| `scalability.sh`              | Executes all scalability experiments.                                      |
| `region-filter.sh`            | Launches the region filtering algorithm.                                   |
| `weight-sensitivity.sh`      | Executes all weight sensitivity experiments.                               |
| `generalizability.sh`         | Launches the necessary experiments for the generalizability claims.        |
| `timeseries_benchmark/inference/infer.py` | Runs inference on the pretrained models for traffic forecasting.           |

### `Simulator/scripts/microservice_optimizer/`

Contains the scripts of all the different solvers, along with carbon intensity, resource costs and latency data.

| Main Files            | Description                          |
| --------------------- | ------------------------------------ |
| `aceso_solver.py`     | Aceso Optimizer.                     |
| `caribou_solver.py`   | Caribou Optimizer.                   |
| `ga_solver.py`        | Vanilla Genetic Algorithm Optimizer. |
| `approx_lp_solver.py` | Linear Programming Optimizer.        |
| `nautilus.py`         | Nautilus (Single Region Placement).  |



### `plots/`

Contains figures generated from the experimental results. These are expected to match the trends of the Figures 6a and 8-12 of the paper.

### `assets/`

Contains the corresponding logos.

---

# 💻 Hardware Requirements

This is a lightweight simulation that has been tested in several different platforms and is expected to run on any recent mac-OS/linux based hardware. 

The experiments are expected to take approximately:

| Experiment        | Expected runtime | 
| ----------------- | ---------------: | 
| Experiment 1      |    `~6-12 hours` |   
| Experiment 2      |   `~1.1-3 hours` |  
| Experiment 3      | `~0.5-2 minutes` |  
| Experiment 4      |    `~15 min-1 h` |  
| Experiment 5      |  `~5-30 minutes` |  
| Experiment 6      |   `~1-2 minutes` |  
| Full reproduction |   `~8-16 hours~` | 

Runtime may vary heavily depending on the hardware and system configuration.

---


### Dependencies

The required dependencies are listed in: `requirements.txt`.

---

# 🚀 Getting Started

The following instructions provide the shortest path for an evaluator to verify that the artifact has been installed correctly.

## 1. Clone the repository

```bash
git clone <REPOSITORY URL> TODO
cd Aceso
```

---

## 2. Install dependencies

Create the required environment and install the dependencies:

```bash
./setup.sh
source venv/bin/activate
```

# 🔬 Reproducing the Results

This section describes how to reproduce the experimental results presented in the paper.

## Recommended reproduction workflow

The complete experimental workflow can be executed by simply running the runner.sh file as following:

```bash
cd Simulator/scripts
./runner.sh
```

Then run the plotter to create all figures and compare them with the paper results. 

```bash
cd "$(git rev-parse --show-toplevel)"
python3 plotter.py
```

The generated figures will be in the ~/plots folder. By comparing those with the paper Figures as described in [Relationship between the artifact and the paper](#relationship-between-the-artifact-and-the-paper), you can complete the evaluation of this artifact.

```text
1. Configure environment
        ↓
2. Run simulation
        ↓
5. Generate figures and tables
        ↓
6. Compare with paper
        ↓
7. Done!
```
---

# 🎯 Claims Supported by the Artifact

This section provides a direct mapping between the main claims of the paper and the experiments available in the artifact. The experiments can also be ran in batch, as explained above, and directly compared to the figures of the paper, without running all the scripts separately.

## Claim 1 — Relative Performance of Aceso

**Baseline Comparison:**

> Aceso achieves similar performance to the rest of the paper baselines, while solving the problem significantly faster than Caribou and LP.

**Artifact support:**
This claim is evaluated using `Simulator/scripts/baselines.sh`.

**Run:**

```bash
cd Simulator/scripts
./baselines.sh
```

After running the script, you can execute the first 5 cells of jupiter notebook and compare the results with Figure 8 and Table 2. Alternatively, you can proceed to the next experiment and confirm the results of all the figures at the end. 

**Expected result:**

Aceso converges in seconds while Caribou and LP converge in multiple minutes and hours, respectively. Furthermore, Aceso achieves better performace than GA. All baselines achieve similar latency. In all the graphs, lower is better. Also, Aceso distributes microservices across different regions.

**Corresponding paper result:**

* Figure: `8`
* Table: `2`
* Section: `5.2`

---

## Claim 2 — Scalability

**Paper claim:**

> Aceso converges in minutes even for 1000-microservice deployments. It converges in seconds for deployments of 10s and 100s of microservices.

**Artifact support:**
This claim is evaluated using `Simulator/scripts/scalability.sh`.

**Run:**

```bash
cd Simulator/scripts
./scalability.sh
```

**Expected result:**

Aceso converges in less than a second for deployments of 10 microservices, in around 10 seconds for deployments of 100 microservices and in less than 5 minutes for applications of 1000 microservices.

**Corresponding paper result:**

* Figure: `Figure 9`
* Section: `5.3`

---

## Claim 3 — Search Space Prunning

**Paper claim:**

> Aceso effectively prunes the search space by filtering out the regions with higher carbon or cost.

**Artifact support:**
This claim is evaluated using `Simulator/scripts/region-filter.sh`.

**Run:**

```bash
cd Simulator/scripts
./region-filter.sh
```

**Expected result:**

Aceso reduces the search space by almost two orders of magnitude.

**Corresponding paper result:**

* Figure: `6a` and `10`
* Section: `5.1` and `5.2`

---

## Claim 4 — Weight Sensitivity

**Paper claim:**

> As the optimization weights prioritize carbon over cost, carbon benefits are either stable or increase and vise versa.

**Artifact support:**
This claim is evaluated using `Simulator/scripts/weight-sensitivity.sh`.

**Run:**

```bash
cd Simulator/scripts
./weight-sensitivity.sh
```

**Expected result:**

Aceso is able to produce carbon and/or cost reductions relative to the optimization weights. If the reduction of any metric does not increase by prioritizing it, it stays stable. 

**Corresponding paper result:**

* Figure: `12a`
* Section: `5.5`

---

## Claim 5 — Generalizability

**Paper claim:**

> Aceso generalizes across different regions and can achieve up to 38.5 % (or more) carbon reduction and up to 6.8 % (or more) cost reduction.

**Artifact support:**
This claim is evaluated using `Simulator/scripts/generalizability.sh`.

**Run:**

```bash
cd Simulator/scripts
./generalizability.sh
```

**Expected result:**

Aceso achieves at least 38.5% carbon reduction for Frankfurt and at least 6.8 cost reduction for Zurich. 

**Corresponding paper result:**

* Figure: `12b`
* Section: `5.6`

---

## Claim 6 — Traffic Forecasting

**Paper claim:**

> Aceso uses a gradient boosted decision tree (GBDT)-based model for the prediction of incoming traffic, due to its low Mean Absolute Error (MAE).

**Artifact support:**
This claim is evaluated using `Simulator/scripts/timeseries_benchmark`. This folder contains the (already) trained models and the script to run inference.

**Run:**

```bash
cd "$(git rev-parse --show-toplevel)"
cd Simulator/scripts/timeseries_benchmark
python3 inference/infer.py --check
```

**Expected result:**

The GBDT-based model achieves the lowest error across all tested ML models.

**Corresponding paper result:**

* Figure: `11`
* Section: `5.4`


### Output files


The experiments results are saved in the following directory:

```text
Aceso/Simulator/scripts/results
```

This directory, after completing all the experiments (1-6) should include:

| Output                           | Description                                                       |
| -------------------------------  | ----------------------------------------------------------------- |
| `baseline_results.csv`           | Performance of each solver (carbon, cost, region assignment etc.) |
| `scalability_results.csv`        | Solve times, number of MS, SLO etc. for each run                  |
| `region_filtering_results.csv`   | Region Set after filtering (for all base regions)                 |
| `weight_sensitivity_results.csv` | Carbon & cost reductions, weights for each run                    |
| `generalizability_results.csv`   | Carbon & cost reductions per base region                          |
| `validation_metrics.csv`         | MAE, training and prediction time of models                       |
| `test_predictions.csv`           | Number of requests and models' predictions                        |
| `test_metrics.csv`               | Model MAE on test dataset                                         |
| `run_info.json`                  | Settings (test window, training steps etc.)                       |

The last four files, which are relative to the traffic forecasting component can be found under scripts/timeseries_benchmark/results.

### Generate the figures

```bash
 cd "$(git rev-parse --show-toplevel)"
python3 plotter.py
```

Alternatively, you can produce all figures by running the jupiter notebook plotter.ipynb and inspect them one by one. 

In any case, the resulting figures will be generated at:

```text
~/plots
```

### Expected result

The generated plots should reproduce the qualitative and quantitative trends shown in **Figures `6a & 8-12`** and **Table `2`** of the paper. Small numerical differences may occur because of hardware differences and the non-deterministic nature of certain algorithms.


# 🧩 Re-running with Different Parameters and Solver

The artifact can also be used to explore configurations beyond those reported in the paper. Each solver (optimizer) allows for the specification of the base region and the number of microservies as command-line arguments. In the case of Aceso, Caribou, GA and LP, the user can also specify the candidate regions and the SLO. In the case of Aceso, the user can specify the percentage of movable microservices, *e.g.,python -m microservice_optimizer.aceso_solver 100 "Frankfurt" "Zurich|London|Paris|Spain|Stockholm" 400 0.8* . 

This is an extensible simulation and any other optimizers can be plugged in for further experimentation. This functionality allows evaluators and researchers to investigate scenarios beyond the exact configurations used in the paper.


---

## Data Sources & Disclaimer

This artifact contains cached and snapshot data gathered for academic research, reference, and evaluation purposes only.

### External Data References
* **Cloudping.com:** Inter-region latency snapshots.
* **Amazon Web Services (AWS):** Historical pricing lists and instance data.
* **Electricity Maps:** Carbon intensity and power grid telemetry datasets.

> **Disclaimer:** All trademarks, service marks, and company names belong to their respective owners. The data included in this repository consists of static historical snapshots collected solely to ensure experimental reproducibility. It is **neither maintained nor guaranteed to be up-to-date or accurate** for commercial or operational decision-making. No endorsement or affiliation by these platforms is implied.

# 📜 License

This artifact is distributed under the `Apache-2.0` license.

---

# 📚 Citation

If you use this artifact, please cite the paper:
Aceso: Latency-Aware Geo-Distribution of Microservices for Cost-Effective Carbon Reduction



# 🙏 Acknowledgements

The work by the authors at the IMDEA Software Institute was partially funded by the Madrid Regional Government through the César Nombela grant (2024-T1/COM-31302) and by the Comunidad de Madrid through the DATIA project, co-funded by the European Union's FEDER funds. Their work was also supported by grant PID2022-142290OB-I00, funded by MCIN/AEI/10.13039/501100011033 and FEDER, UE, and by grant CEX2024-001471-M, funded by MICIU/AEI/10.13039/ 501100011033. The work by J.O.I is partially supported by the EU EDGELESS project funded by the EU programme (agreement No. 101092950) and by the Smart Networks and Services Joint Undertaking (SNS JU) under the EU HE programme (agreement No. 101293102).

---


## 🔗 Links

* **Paper:** TODO
* **DOI:** TODO
* **Artifact:** [todo zenodo link] 
* **Repository:** [https://github.com/muse-research-lab/aceso]
* **Middleware 2026:** [https://middleware-conf.github.io/2026/]

---

<p align="center">
  <img src="./assets/logo1.png" alt="Company Logo" height="100" />
  <br /><br />
  <img src="./assets/logo2.jpg" alt="Partner Logo" height="60" />
  <br /><br />
  <img src="./assets/logo3.png" alt="Partner Logo" height="60" />
</p>