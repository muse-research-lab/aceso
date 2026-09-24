#!/usr/bin/env bash

set -u

LOG_FILE="logs/region-filter.log"
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
log "Region filter evaluation started: $(date)"
log "========================================"

# ---- Region Filter ----
run_solver "Region Filter" \
    microservice_optimizer.aceso_filtering

run_solver "Region Filter - Frankfurt" \
    microservice_optimizer.aceso_solver 16 "Frankfurt" "ALL" 200 1.0 -rselection

run_solver "Region Filter - Calgary" \
    microservice_optimizer.aceso_solver 16 "Calgary" "ALL" 300 0.3 -rselection

run_solver "Region Filter - Hong Kong" \
    microservice_optimizer.aceso_solver 20 "Hong Kong" "ALL" 400 0.4 -rselection

# ---- Summary ----
echo ""
if [ "$overall_status" -eq 0 ]; then
    echo "Region filter completed successfully."
else
    echo "One or more solvers failed. Check $LOG_FILE for details."
fi
echo "Full output is saved in $LOG_FILE"

exit "$overall_status"