#!/usr/bin/env bash

set -u

LOG_FILE="logs/generalizability.log"
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
log "Generalizability Analysis started: $(date)"
log "========================================"

# ---- Aceso Solver ----
run_solver "Frankfurt" \
    microservice_optimizer.aceso_solver 100 "Frankfurt" "Zurich|London|Paris|Spain|Stockholm" 1400 0.8 -gen

# ---- Aceso Solver ----
run_solver "Zurich" \
    microservice_optimizer.aceso_solver 100 "Zurich" "Frankfurt|London|Paris|Spain|Stockholm" 1400 0.8 -gen

# ---- Summary ----
echo ""
if [ "$overall_status" -eq 0 ]; then
    echo "All generalizability tests completed successfully."
else
    echo "One or more tests failed. Check $LOG_FILE for details."
fi
echo "Full output is saved in $LOG_FILE"

exit "$overall_status"