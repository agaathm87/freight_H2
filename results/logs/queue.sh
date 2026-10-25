#!/bin/bash
# Shared job queue for several workers: each worker walks the same list of run names and solves the runs that no
# other worker has claimed (a claim is an atomic mkdir in results/logs/claims). Start two workers on two cores:
#   results/logs/queue.sh F1_real F2_real ... &   results/logs/queue.sh F1_real F2_real ... &
# Runs already on disk return at once (run_freight.py skips them). Remove results/logs/claims to reuse names.
cd "$(dirname "$0")/../.."      # the FinalModel_Freight folder
mkdir -p results/logs/claims
for r in "$@"; do
  mkdir "results/logs/claims/$r" 2>/dev/null || continue
  SECONDS=0
  python run_freight.py "$r" > "results/logs/run_$r.txt" 2>&1; rc=$?
  echo "run:$r exit $rc ${SECONDS}s"
done
