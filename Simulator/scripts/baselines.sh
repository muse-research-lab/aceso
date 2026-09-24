#!/usr/bin/env bash

set -u

LOG_FILE="logs/baseline-optimizers.log"
overall_status=0

log() {
    # Echo to terminal AND append to log file
    echo "$1" | tee -a "$LOG_FILE"
}

run_solver() {
    local name="$1"; shift

    log ""
    log "=== Starting $name: $(date) ==="

    python -m "$@" >> "$LOG_FILE" 2>&1
    local status=$?

    log "=== $name finished with exit code $status: $(date) ==="

    if [ "$status" -ne 0 ]; then
        echo "$name FAILED (exit code $status). Check $LOG_FILE"
        overall_status=1
    else
        echo ""
    fi
}

# ---- Header ----
log "========================================"
log "Baseline evaluation started: $(date)"
log "========================================"

# ---- Aceso Solver ----
run_solver "Aceso Solver" \
    microservice_optimizer.aceso_solver \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650 1.0

# ---- Caribou Solver ----

run_solver "Caribou Solver" \
    microservice_optimizer.caribou_solver \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650

# ---- GA Solver ----

run_solver "GA Solver" \
    microservice_optimizer.ga_solver \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650

run_solver "LP Solver" \
    microservice_optimizer.approx_lp_solver 100 "Frankfurt" "London|Spain|Stockholm|Paris|Ireland|Milan" 2000 

# ---- Summary ----
echo ""
if [ "$overall_status" -eq 0 ]; then
    echo "All baseline solvers completed successfully."
else
    echo "One or more solvers failed. Check $LOG_FILE for details."
fi
echo "Full output is saved in $LOG_FILE"

exit "$overall_status"