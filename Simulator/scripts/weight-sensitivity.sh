#!/usr/bin/env bash

set -u

LOG_FILE="logs/weight_sensitivity.log"
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
log "Weight Sensitivity Analysis started: $(date)"
log "========================================"

# ---- Frankfurt ----
run_solver "Frankfurt 1" \
    microservice_optimizer.aceso_solver 100 Frankfurt "Stockholm|Paris|London|Spain|Milan|Ireland" 2000 0.9 -weights 1 0 

run_solver "Frankfurt 2" \
    microservice_optimizer.aceso_solver 100 Frankfurt "Stockholm|Paris|London|Spain|Milan|Ireland" 2000 0.9 -weights 0.75 0.25 

run_solver "Frankfurt 3" \
    microservice_optimizer.aceso_solver 100 Frankfurt "Stockholm|Paris|London|Spain|Milan|Ireland" 2000 0.9 -weights 0.5 0.5 

run_solver "Frankfurt 4" \
    microservice_optimizer.aceso_solver 100 Frankfurt "Stockholm|Paris|London|Spain|Milan|Ireland" 2000 0.9 -weights 0.25 0.75 

run_solver "Frankfurt 5" \
    microservice_optimizer.aceso_solver 100 Frankfurt "Stockholm|Paris|London|Spain|Milan|Ireland" 2000 0.9 -weights 0 1 

# ---- Hong Kong ----
run_solver "Hong Kong 1" \
    microservice_optimizer.aceso_solver 100 "Hong Kong" "Auckland|Kuala Lumpur|Oregon|Paris|Seoul|Stockholm|Zurich" 3000 0.5 -weights 1 0 

run_solver "Hong Kong 2" \
    microservice_optimizer.aceso_solver 100 "Hong Kong" "Auckland|Kuala Lumpur|Oregon|Paris|Seoul|Stockholm|Zurich" 3000 0.5 -weights 0.75 0.25 

run_solver "Hong Kong 3" \
    microservice_optimizer.aceso_solver 100 "Hong Kong" "Auckland|Kuala Lumpur|Oregon|Paris|Seoul|Stockholm|Zurich" 3000 0.5 -weights 0.5 0.5 

run_solver "Hong Kong 4" \
    microservice_optimizer.aceso_solver 100 "Hong Kong" "Auckland|Kuala Lumpur|Oregon|Paris|Seoul|Stockholm|Zurich" 3000 0.5 -weights 0.25 0.75 

run_solver "Hong Kong 5" \
    microservice_optimizer.aceso_solver 100 "Hong Kong" "Auckland|Kuala Lumpur|Oregon|Paris|Seoul|Stockholm|Zurich" 3000 0.5 -weights 0 1 



# ---- Summary ----
echo ""
if [ "$overall_status" -eq 0 ]; then
    echo "All weight sensitivity tests completed successfully."
else
    echo "One or more tests failed. Check $LOG_FILE for details."
fi
echo "Full output is saved in $LOG_FILE"

exit "$overall_status"