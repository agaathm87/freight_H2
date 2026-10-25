# Model notes

This published core contains the merged course and hydrogen model. Hydrogen
is represented as a fixed industrial demand on the `Hydrogen` bus and is
supplied by grey hydrogen, blue hydrogen, and grid electrolysis.

The canonical H2 database is generated from the untouched course database. For
each run, the runner creates and uses
`input_databases/scenarios/<name>/` and writes a
`scenario_manifest.json` with the source fingerprint and resolved scenario
settings. Scenario parameters are applied to in-memory copies before the
network is built.

S1 is the unconstrained reference, S2 uses half of the S1 grid-electrolyser
reference, and S3 allows no new grid-electrolyser capacity. Desalinated-water
electrolysis is an alternative-water lever and is outside this freshwater
capacity limit. Sensitivities cover
costs, CO2 prices, batteries, storage, desalination, subsidies, demand,
plant sizing, and mandates.

Feasible networks are saved under `results/runs`. Result modules aggregate
hydrogen production, capacity, costs, emissions, gas use, electricity, water,
storage, and policy indicators. Generated plots are written under
`results/plots`.
