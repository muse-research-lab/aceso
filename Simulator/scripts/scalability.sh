#!/usr/bin/env bash

set -u

LOG_FILE="logs/scalability.log"
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
log "Scalability Analysis started: $(date)"
log "========================================"

# ---- Aceso Solver ----
run_solver "10 MS - EU" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650 1.0

# ---- Aceso Solver ----
run_solver "10 MS - EU+US" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan|Northern Virginia|Ohio|Mexico City|Montreal|Calgary|Northern California" 1650 1.0


# ---- Aceso Solver ----
run_solver "10 MS - ALL" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "ALL" 1650 1.0


# ---- Aceso Solver ----
run_solver "10 MS - Relaxed" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 600 1.0


# ---- Aceso Solver ----
run_solver "10 MS - Medium" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 400 0.5


# ---- Aceso Solver ----
run_solver "10 MS - Strict" \
    microservice_optimizer.aceso_scalability \
    10 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 200 0.2


# ---- Aceso Solver ----
run_solver "100 MS - EU" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650 1.0


# ---- Aceso Solver ----
run_solver "100 MS - EU+US" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan|Northern Virginia|Ohio|Mexico City|Montreal|Calgary|Northern California" 1650 0.8


# ---- Aceso Solver ----
run_solver "100 MS - ALL" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "ALL" 1650 0.6


# ---- Aceso Solver ----
run_solver "100 MS - Relaxed" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1650 1.0

# ---- Aceso Solver ----
run_solver "100 MS - Medium" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 700 0.3

#--- Aceso Solver ----
run_solver "100 MS - Strict" \
    microservice_optimizer.aceso_scalability \
    100 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 500 0.1

# ---- Aceso Solver ----
run_solver "1000 MS - EU" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 7000 0.2


# ---- Aceso Solver ----
run_solver "1000 MS - EU+US" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan|Northern Virginia|Ohio|Mexico City|Montreal|Calgary|Northern California" 7000 0.1


# ---- Aceso Solver ----
run_solver "1000 MS - ALL" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "ALL" 7000 0.1


# ---- Aceso Solver ----
run_solver "1000 MS - Relaxed" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 6000 0.2

# ---- Aceso Solver ----
run_solver "1000 MS - Medium" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 2000 0.02

#--- Aceso Solver ----
run_solver "1000 MS - Strict" \
    microservice_optimizer.aceso_scalability \
    1000 "Frankfurt" "Paris|Stockholm|London|Spain|Ireland|Milan" 1000 0.01

# ---- Summary ----
echo ""
if [ "$overall_status" -eq 0 ]; then
    echo "All scalability tests completed successfully."
else
    echo "One or more tests failed. Check $LOG_FILE for details."
fi
echo "Full output is saved in $LOG_FILE"

exit "$overall_status"