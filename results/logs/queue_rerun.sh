#!/bin/bash
# run a list of freight runs one after another; log each
cd "$(dirname "$0")/../.."      # the FinalModel_Freight folder
for r in "$@"; do SECONDS=0; python run_freight.py --rerun $r > results/logs/run_$r.txt 2>&1; echo "$r exit $? ${SECONDS}s"; done
