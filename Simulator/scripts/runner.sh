#!/bin/bash

# runner.sh - Execute all experiment scripts sequentially

# Exit immediately if a command exits with a non-zero status
set -e

# List of scripts to run in order
SCRIPTS=(
    "baselines.sh"
    "scalability.sh"
    "region-filter.sh"
    "weight-sensitivity.sh"
    "generalizability.sh"
)

# Get the directory where this runner script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log file with timestamp
LOG_FILE="${SCRIPT_DIR}/logs/runner_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "Starting runner at $(date)"
echo "Logging to: ${LOG_FILE}"
echo "=========================================="

# Loop through each script and execute it
for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="${SCRIPT_DIR}/${script}"

    if [[ ! -f "${SCRIPT_PATH}" ]]; then
        echo "ERROR: ${script} not found at ${SCRIPT_PATH}" | tee -a "${LOG_FILE}"
        exit 1
    fi

    if [[ ! -x "${SCRIPT_PATH}" ]]; then
        echo "Making ${script} executable..."
        chmod +x "${SCRIPT_PATH}"
    fi

    echo "" | tee -a "${LOG_FILE}"
    echo "------------------------------------------" | tee -a "${LOG_FILE}"
    echo "[$(date +%H:%M:%S)] Running ${script}..." | tee -a "${LOG_FILE}"
    echo "------------------------------------------" | tee -a "${LOG_FILE}"

    # Run the script and tee output to the log file
    if bash "${SCRIPT_PATH}" 2>&1 | tee -a "${LOG_FILE}"; then
        echo "[$(date +%H:%M:%S)] ✓ ${script} completed successfully" | tee -a "${LOG_FILE}"
    else
        echo "[$(date +%H:%M:%S)] ✗ ${script} FAILED (exit code: $?)" | tee -a "${LOG_FILE}"
        echo "Aborting runner due to failure in ${script}." | tee -a "${LOG_FILE}"
        exit 1
    fi
done

# Run inference check after all experiments complete
echo "" | tee -a "${LOG_FILE}"
echo "------------------------------------------" | tee -a "${LOG_FILE}"
echo "[$(date +%H:%M:%S)] Running timeseries_benchmark/inference/infer.py --check..." | tee -a "${LOG_FILE}"
echo "------------------------------------------" | tee -a "${LOG_FILE}"

if python3 "${SCRIPT_DIR}/timeseries_benchmark/inference/infer.py" --check 2>&1 | tee -a "${LOG_FILE}"; then
    echo "[$(date +%H:%M:%S)] ✓ timeseries_benchmark/inference/infer.py completed successfully" | tee -a "${LOG_FILE}"
else
    echo "[$(date +%H:%M:%S)] ✗ timeseries_benchmark/inference/infer.py FAILED (exit code: $?)" | tee -a "${LOG_FILE}"
    exit 1
fi

echo "" | tee -a "${LOG_FILE}"
echo "=========================================="
echo "All scripts completed at $(date)"
echo "=========================================="