#!/bin/bash
# Run jobs one after another: run:<name> (run_freight.py) or grid:<grid>:<a-b> (sensitivity.py --points a-b)
cd "$(dirname "$0")/../.."      # the FinalModel_Freight folder
for j in "$@"; do
  SECONDS=0
  case $j in
    run:*) r=${j#run:}; python run_freight.py $r > results/logs/run_$r.txt 2>&1; rc=$? ;;
    grid:*) g=${j#grid:}; name=${g%%:*}; pts=${g#*:}
            python sensitivity.py $name --points $pts > results/logs/grid_${name}_${pts}.txt 2>&1; rc=$? ;;
  esac
  echo "$j exit $rc ${SECONDS}s"
done
