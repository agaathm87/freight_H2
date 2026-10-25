"""Constants and adjustable presets for the heavy-duty road freight study and the water module.

Everything a scenario can change is a setting in FREIGHT_DEFAULTS (merged into h2_presets.DEFAULTS), so runs are
defined as make_scenario('S1', bet_costs='decrease', gasoline_price='sharp', water_scarcity='driver', ...).
All money values in 2024 euros. Units follow the course database (CAPEX/FOM per kW of OUTPUT, VOM per kWh of INPUT).
"""

# --------------------------------------------------------------------------------------------------------------
# Freight topology (names in technologies.xlsx / demand.xlsx, written by build_freight_database.py)
# --------------------------------------------------------------------------------------------------------------
FREIGHT_BUS = 'Freight transport'           # demand bus, energy terms (MWh of useful transport energy)
FREIGHT_LOAD = 'freight_road'               # 90 PJ in 2020 (assignment), projected with GDP
FREIGHT_PJ_2020 = 90.0
FREIGHT_GDP_EXPONENT = 0.6                  # elasticity to GDP (KiM: ~1.0 for truck-km in the short run; lower
                                            # long-run because of decoupling and logistics efficiency)
ICE_TRUCKS = ['ICE truck', 'ICE truck - existing']
BET_TIER_TECHS = ['BET - urban', 'BET - long haul']   # realistic layer: BETs by duty cycle (bet_tiers)
BETS = ['BET', 'BET - existing'] + BET_TIER_TECHS
FCETS = ['FCET']
H2ICE_TRUCKS = ['H2-ICE truck']             # hydrogen combustion engine truck (extension, with the FCET)
HYDROGEN_TRUCKS = FCETS + H2ICE_TRUCKS
# Zero-emission in the EU HDV CO2 standards (Reg. 2019/1242 as revised in 2024: below 3 g CO2/tkm, which includes
# hydrogen combustion engines) and so in the CO2 class of the Dutch truck toll; counted in ze_min/max_share.
ZE_TRUCKS = BETS + FCETS + H2ICE_TRUCKS
TRUCKS = ICE_TRUCKS + ZE_TRUCKS
FREIGHT_ETS2 = ICE_TRUCKS                   # road transport fuels fall under EU ETS2 (from 2028)

# --------------------------------------------------------------------------------------------------------------
# Scenario axes (assignment): X = BET costs, Y = gasoline price.  CAPEX €/kW output, VOM €/kWh input.
# 'constant': CAPEX and VOM stay at the assignment values. 'decrease': battery systems -64..-75% by 2035
# (Link et al., 2024) -> truck CAPEX -35% (2030), -50% (2040), -55% (2050); the charging penalty (VOM) halves by
# 2030 with the AFIR megawatt-charging roll-out and falls to 0.02 €/kWh by 2050.
# --------------------------------------------------------------------------------------------------------------
BET_COSTS = {
    'constant': {'CAPEX': {2020: 650, 2030: 650, 2040: 650, 2050: 650},
                 'VOM':   {2020: 0.10, 2030: 0.10, 2040: 0.10, 2050: 0.10}},
    'decrease': {'CAPEX': {2020: 650, 2030: 420, 2040: 325, 2050: 290},
                 'VOM':   {2020: 0.10, 2030: 0.05, 2040: 0.03, 2050: 0.02}},
}
# Gasoline (stand-in for diesel) price, €/MWh_th, incl. excise as in the course database (200 in 2020).
GASOLINE_PRICES = {
    'constant': {2020: 200, 2030: 200, 2040: 200, 2050: 200},
    'moderate': {2020: 200, 2030: 220, 2040: 240, 2050: 260},     # +0.9%/yr: flat real crude, excise indexation
    'sharp':    {2020: 200, 2030: 300, 2040: 400, 2050: 500},     # +3.1%/yr: course database path
    'untaxed':  {2020: 70, 2030: 75, 2040: 80, 2050: 85},         # test: pre-tax diesel level (F1_untaxed_nofcet)
}
# Realism check (Oct 2026): hauliers pay DIESEL excluding VAT (VAT is reclaimed), not the gasoline consumer price.
#   Diesel 12 Oct 2026 (EU Oil Bulletin): product 1.491 + excise 0.552 + other 0.008 = 2.051 €/L ex VAT = 206 €/MWh
#   (9.97 kWh/L) during the 2026 oil shock; Oct 2025: 1.702 €/L incl. VAT = 141 €/MWh ex VAT; 2020 ~105 €/MWh.
#   'diesel_nl': pre-shock level plus IEA Current Policies crude (+60% by 2050 on the ~40% product share), excise
#   constant in real terms. Used with truck_fuel_price (ICE trucks only; cars keep the gasoline price).
TRUCK_FUEL_PRICES = {'diesel_nl': {2020: 105, 2030: 150, 2040: 155, 2050: 160},
                     # the course's sharp/moderate ratio (300/220, 400/240, 500/260) on diesel_nl: keeps the Y axis
                     'diesel_nl_sharp': {2020: 105, 2030: 205, 2040: 258, 2050: 308}}
FREIGHT_SCENARIOS = {        # name: (BET costs, gasoline price)
    'F1': ('constant', 'moderate'),    # BET costs stay, gasoline moderate
    'F2': ('decrease', 'moderate'),    # BET costs fall, gasoline moderate
    'F3': ('constant', 'sharp'),       # BET costs stay, gasoline sharp
    'F4': ('decrease', 'sharp'),       # BET costs fall, gasoline sharp
}
FREIGHT_LABELS = {'F1': 'F1 BET-flat / fuel-moderate', 'F2': 'F2 BET-cheap / fuel-moderate',
                  'F3': 'F3 BET-flat / fuel-sharp', 'F4': 'F4 BET-cheap / fuel-sharp'}

# Fuel-cell electric truck (hydrogen as fuel, an extension): CAPEX 1.2-1.4x BET until 2040 (Basma & Rodriguez,
# 2023: FCET TCO 10-20% above BET in the long run; Link et al., 2024: fuel-cell systems < 100 €/kW only in the early
# 2040s). VOM = hydrogen delivery + station cost above the production cost: 5 €/kg (2020), 4 (2030), 3 (2040),
# 2.5 (2050); NREL (Chung & Wang, 2024) gives $2.3-10.2/kg for heavy-duty stations in 2030. Efficiency relative to
# ICE 40% / BET 70%.
FCET_PARAMS = {
    'CAPEX':      {2020: 900, 2030: 750, 2040: 550, 2050: 450},
    'FOM':        {2020: 7, 2030: 6, 2040: 5, 2050: 5},
    'VOM':        {2020: 0.15, 2030: 0.12, 2040: 0.09, 2050: 0.075},
    'Efficiency': {2020: 0.45, 2030: 0.50, 2040: 0.52, 2050: 0.55},
    'Lifetime':   {2020: 10, 2030: 10, 2040: 10, 2050: 10},
}
# Hydrogen combustion engine truck (H2-ICE, the third zero-emission type of the extension; MAN hTGX small series of
# 200 from 2025: 520 hp, 56 kg H2 at 700 bar, 600 km, so ~9.3 kg/100 km = 310 kWh/100 km).
#   CAPEX: a diesel truck with hydrogen tanks. ICCT (2023, US long haul): the engine costs about the same as a diesel
#   engine, the tanks add ~$120k to a $158k diesel tractor in 2022 (x1.8); cheaper and smaller tanks bring this to
#   ~x1.5 (2030) and ~x1.25-1.3 (2040-2050). Anchored on the ICE truck (120 €/kW), not on the BET/FCET, which
#   favours the H2-ICE: the assignment's zero-emission trucks cost 5-6x an ICE truck per kW (real price ratio ~2).
#   FOM 2.5% of CAPEX like the ICE truck; lifetime 12 years like the ICE truck.
#   VOM: the FCET's hydrogen delivery + station cost (same stations) + the ICE truck's 0.01 €/kWh for the engine.
#   Efficiency: ~10% more energy per km than diesel now (ICCT 2023: 13%; hTGX 310 vs ~280-300 kWh/100 km for a
#   diesel tractor), at diesel level by 2050 (peak efficiency 44% -> 50%, ICCT 2023). FCET / H2-ICE energy ratio
#   1.35-1.37 (ICCT 2023: 1.23-1.31; the model's FCET is relatively efficient).
#   Literature: ICCT (2023, Europe): H2-ICE trucks 25-45% above BETs in TCO by 2040, parity with diesel 'beyond
#   2040 or not at all'; ICCT (2023, US): H2-ICE ~20% above FCET in 2030, cheaper than FCET only while hydrogen is
#   cheap and fuel cells expensive; Magnino et al. (2024): H2-ICE best for 42-76 t long haul today, FCET later.
H2ICE_ENGINE_VOM = 0.01                     # €/kWh_H2: engine part of the H2-ICE VOM (the rest is hydrogen delivery)
H2ICE_PARAMS = {
    'CAPEX':      {2020: 215, 2030: 180, 2040: 160, 2050: 150},
    'FOM':        {2020: 5.4, 2030: 4.5, 2040: 4.0, 2050: 3.8},
    'VOM':        {y: round(v + H2ICE_ENGINE_VOM, 4) for y, v in FCET_PARAMS['VOM'].items()},
    'Efficiency': {2020: 0.35, 2030: 0.37, 2040: 0.38, 2050: 0.40},
    'Lifetime':   {2020: 12, 2030: 12, 2040: 12, 2050: 12},
}

# --------------------------------------------------------------------------------------------------------------
# Water: operational consumption (m3 per MWh of MAIN output) and the share that is freshwater (Dutch siting).
#   Power plants: Macknick et al. (2012), medians for recirculating (tower) cooling: NGCC 198 gal/MWh, NGCC+CCS 393,
#   nuclear 672, biomass steam 553, PV 26, wind 0.  Freshwater share: Dutch nuclear is seawater-cooled (Borssele),
#   about half of the gas/biomass capacity sits on rivers and canals.  Biomass + CCS: biomass x the NGCC CCS ratio.
#   Hydrogen: IRENA (2023) 17.5-22.3 L/kg for electrolysis incl. treatment and cooling; SMR 10, SMR + CCS 28 L/kg
#   (the group's Table "water"); 1 MWh_H2 = 30 kg.
#   Industrial CCS: 2.0 m3 per t CO2 captured (the NGCC+CCS increment of Macknick et al. per t captured).
# Adjust any value with the scenario setting water_intensity={tech: (m3/MWh, freshwater share)}.
# --------------------------------------------------------------------------------------------------------------
KG_PER_MWH = 30.0
WATER_INTENSITY = {
    'Electrolyser':             (22.0 * KG_PER_MWH / 1e3, 1.0),
    'Electrolyser - seawater':  (22.0 * KG_PER_MWH / 1e3, 0.0),
    'SMR':                      (10.0 * KG_PER_MWH / 1e3, 1.0),
    'SMR - existing':           (10.0 * KG_PER_MWH / 1e3, 1.0),
    'SMR CCS':                  (28.0 * KG_PER_MWH / 1e3, 1.0),
    'CCGT':                     (0.75, 0.5),
    'CCGT - existing':          (0.75, 0.5),
    'CCGT CCS':                 (1.49, 0.5),
    'Biomass plant':            (2.09, 0.5),
    'Biomass plant CCS':        (4.15, 0.5),
    'Nuclear plant':            (2.54, 0.0),
    'Solar PV':                 (0.10, 1.0),
    'Wind turbine - onshore':   (0.0, 1.0),
    'Wind turbine - offshore':  (0.0, 0.0),
    # pure green and pink routes: the same water as their grid counterparts (electrolysis on freshwater)
    'Electrolyser - pure green': (22.0 * KG_PER_MWH / 1e3, 1.0),
    'Electrolyser - pink':       (22.0 * KG_PER_MWH / 1e3, 1.0),
    'Nuclear plant - dedicated': (2.54, 0.0),
    'Solar PV - dedicated':      (0.10, 1.0),
    'Wind turbine - offshore - dedicated': (0.0, 0.0),
    'Wind turbine - onshore - dedicated':  (0.0, 1.0),
}
# Every other technology in the system, listed explicitly so the water account covers all of them: operational
# water use is negligible (closed loops, no cooling towers or process water). Industrial CCS uses water per t captured.
WATER_INTENSITY.update({t: (0.0, 1.0) for t in [
    'Battery', 'H2 storage',
    'Industrial HTP - fossil', 'Industrial HTP - fossil - existing', 'Industrial HTP - fossil CCS',
    'Industrial machinery - electricity', 'Industrial machinery - fossil', 'Industrial machinery - fossil - existing',
    'Industrial machinery - fossil CCS',
    'Residential Appliance', 'Residential gas boiler', 'Residential gas boiler - existing', 'Residential heat pump',
    'ICE car', 'ICE car - existing', 'BEV', 'BEV - existing',
    'ICE truck', 'ICE truck - existing', 'BET', 'BET - existing', 'FCET', 'H2-ICE truck', 'BET - urban',
    'BET - long haul']})
WATER_SECTOR = {   # for the whole-system water account
    'Power': ['CCGT', 'CCGT - existing', 'CCGT CCS', 'Biomass plant', 'Biomass plant CCS', 'Nuclear plant', 'Solar PV',
              'Wind turbine - onshore', 'Wind turbine - offshore', 'Battery'],
    'Hydrogen': ['Electrolyser', 'Electrolyser - seawater', 'SMR', 'SMR - existing', 'SMR CCS', 'H2 storage',
                 'Electrolyser - pure green', 'Electrolyser - pink'],
    'Dedicated power for H2': ['Nuclear plant - dedicated', 'Solar PV - dedicated',
                               'Wind turbine - offshore - dedicated', 'Wind turbine - onshore - dedicated'],
    'Industry': ['Industrial HTP - fossil', 'Industrial HTP - fossil - existing', 'Industrial HTP - fossil CCS',
                 'Industrial machinery - electricity', 'Industrial machinery - fossil',
                 'Industrial machinery - fossil - existing', 'Industrial machinery - fossil CCS'],
    'Buildings': ['Residential Appliance', 'Residential gas boiler', 'Residential gas boiler - existing',
                  'Residential heat pump'],
    'Transport': ['ICE car', 'ICE car - existing', 'BEV', 'BEV - existing', 'ICE truck', 'ICE truck - existing', 'BET',
                  'BET - existing', 'FCET', 'H2-ICE truck', 'BET - urban', 'BET - long haul'],
}
WATER_PER_TCO2_CAPTURED = {'Industrial HTP - fossil CCS': (2.0, 1.0), 'Industrial machinery - fossil CCS': (2.0, 1.0)}
THERMAL_FRESHWATER = ['CCGT', 'CCGT - existing', 'CCGT CCS', 'Biomass plant', 'Biomass plant CCS']
SUMMER_MONTHS = (6, 7, 8, 9)

# Groups that a water cap can limit: carriers, and whether the cap is in MW of input (p_nom) or of output.
WATER_GROUPS = {
    'Electrolysers': dict(component='Link', basis='input',                                    # MW_el, all on freshwater
                          carriers=['Electrolyser', 'Electrolyser - pure green', 'Electrolyser - pink']),
    'Thermal power': dict(component='Link', carriers=THERMAL_FRESHWATER, basis='output'),    # MW_e
    'Blue hydrogen': dict(component='Link', carriers=['SMR CCS'], basis='output'),           # MW_H2
    'Nuclear':       dict(component='Link', carriers=['Nuclear plant'], basis='output'),     # MW_e
}

# Verdringingsreeks (Besluit kwaliteit leefomgeving art. 3.14; IPLO). In a water shortage the water managers serve:
#   1 safety and irreversible damage; 2 utilities: drinking water and energy supply (when security of supply is at
#   stake); 3 small-scale high-value use: industrial process water, irrigation of capital-intensive crops; 4 all other
#   use (agriculture, shipping, industry and energy without a supply-security issue, nature, ...). Within categories
#   3 and 4 the order follows economic and social damage. It applies to surface water in an actual or impending
#   shortage (the province can extend categories 3-4 to groundwater).
# Every energy technology that uses freshwater belongs to a group; each group has a category. Electrolysis is a
# setting: electrolysis_category = 2 (supply security), 3 (process water, default) or 4 (other industry), the three
# options of the group's Table 1.
WATER_USE_GROUP = {
    'CCGT': 'power', 'CCGT - existing': 'power', 'CCGT CCS': 'power', 'Biomass plant': 'power',
    'Biomass plant CCS': 'power', 'Nuclear plant': 'power', 'Nuclear plant - dedicated': 'power',
    'SMR': 'process', 'SMR - existing': 'process', 'SMR CCS': 'process',            # hydrogen process water
    'Industrial HTP - fossil CCS': 'process', 'Industrial machinery - fossil CCS': 'process',   # CO2 capture
    'Electrolyser': 'electrolysis', 'Electrolyser - pure green': 'electrolysis', 'Electrolyser - pink': 'electrolysis',
    'Solar PV': 'pv', 'Solar PV - dedicated': 'pv',                                  # panel cleaning: can wait
}
WATER_GROUP_CATEGORY = {'power': 2, 'process': 3, 'pv': 4, 'electrolysis': None}   # None = electrolysis_category

# Freshwater that each group uses in the drought season (June-September) of the reference run F1 (no water limits),
# Mm3. The water available in a drought is fixed in m3, like the group's electrolyser limit: it does not change when
# costs change or technologies are added. (Computed from results/runs/F1.nc with freight_water.season_use.)
WATER_REFERENCE_DRY = {
    'power':        {2030: 2.20, 2040: 0.72, 2050: 0.00},
    'process':      {2030: 4.64, 2040: 12.96, 2050: 15.95},
    'electrolysis': {2030: 0.00, 2040: 0.00, 2050: 7.05},
    'pv':           {2030: 0.44, 2040: 1.18, 2050: 4.70},
}

# Droughts: the share of its reference drought-season water that each category may use (1 = unrestricted).
#   dry_1in20     the planning year of the Deltaprogramma Zoetwater (1-in-20 dry year): category 4 restricted
#                 (sprinkling and abstraction bans for part of the season or area), 1-3 served
#   extreme_2018  a 2018-type drought (precipitation deficit 309 mm, about 1-in-30 nationally; Rhine at Lobith below
#                 1,000 m3/s from August, minimum ~750 m3/s, about a third of the mean ~2,200 m3/s; close to normal
#                 summers under KNMI'23 Hd around 2050): category 4 gets nothing, process water -25% (in 2018 Nouryon
#                 Hengelo cut production by 25% at the Twentekanaal's 30 °C cooling-water limit), category 2 served
# The shares for categories 3 and 4 are stylised: the verdringingsreeks gives an order, not quantities.
DROUGHTS = {
    'dry_1in20':    {2: 1.0, 3: 1.0, 4: 0.5},
    'extreme_2018': {2: 1.0, 3: 0.75, 4: 0.0},
}

# Price of alternative water (desalination, effluent reuse) above a quota or budget, €/m3. Default 1.4: the group's
# desalination lever (€0.03/kg H2 at 22 L/kg). Realistic range for the Netherlands: demineralised water $0.66-1.02/m3
# (Intratec, NL, 2023); large seawater RO $0.5-1.0/m3 (Ghaffour et al., 2013), up to $1.84/m3 (Carlsbad; Bouma et al.,
# 2022); effluent reuse is already used by industry (Dow Terneuzen, 2.5 Mm3/yr). water_alt_cost takes a number, a key
# below, or None (hard limit: no alternative water).
WATER_ALT_COSTS = {'group': 1.4, 'low': 0.6, 'central': 1.0, 'high': 1.5}

# Water scarcity: 'none' (every run except the driver runs) or the driver. Every part is adjustable per run:
#   drought  key of DROUGHTS or a path {year: key}: the verdringingsreeks in the drought season. With
#            water_allocation='verdringingsreeks' each restricted category has its own quota; with 'cost_optimal' the
#            same total water is one pool that goes to whichever use saves the most cost (no priority order). Water
#            above a quota or the pool comes from alternative sources (desalination, effluent reuse) at water_alt_cost
#            (€1.4/m3), so runs stay feasible.
#   derate   share of freshwater-cooled thermal capacity unavailable in June-September (cooling-water temperature)
#   caps, budget, summer  capacity caps {group: {period: MW}} (the group's electrolyser lever), an annual freshwater
#            budget (Mm3/yr) and its summer share: not used by the driver, available through water_caps /
#            water_budget / water_summer_factor
WATER_SCARCITY = {
    'none':   dict(caps=None, drought=None, budget=None, summer=None, derate=0.0),
    # The water-scarcity driver: an outside path, like GDP for the demands. The drought-season water of each
    # verdringingsreeks category tightens over time on a KNMI'23 Hd-type climate path (dry summers more frequent): the
    # Deltaprogramma Zoetwater's 1-in-20 dry year in 2030 and 2040, a 2018-type drought in 2050 (close to a normal
    # summer under KNMI'23 Hd around 2050), with more summer derating of river-cooled plants. No capacity caps: water
    # above a quota is desalinated or reused water at water_alt_cost (€1.4/m3), the backstop.
    'driver': dict(caps=None, drought={2030: 'dry_1in20', 2040: 'dry_1in20', 2050: 'extreme_2018'},
                   budget=None, summer=None, derate={2030: 0.10, 2040: 0.15, 2050: 0.25}),
}

# --------------------------------------------------------------------------------------------------------------
# Net-zero policy, mandates and subsidies (adjustable; off in the core and extension F1-F4; the realistic layer
# uses the CO2-standards floor, the toll, AanZET, SWiM, OWE, the Dutch industry obligation and RED III transport)
#   co2_cap: annual CO2 to the atmosphere of the whole modelled system (Mt/yr). 'netzero' follows the Dutch
#   Klimaatwet (-55% vs 1990 in 2030, climate neutral in 2050) and the EU 2040 target (-90% net, up to 5% from
#   international credits from 2036, so -85% domestic). NL emissions in 2020 were about 25% below 1990, so relative
#   to the model's own 2020 emissions (100.5 Mt): 2030 = 0.45/0.75 = 60%, 2040 = 0.15/0.75 = 20%, 2050 = 0.05/0.75
#   = 6.7% (the last 5% left to sinks and removals that the model does not contain).
#   ze_min_share: a floor on the zero-emission share of freight; 'eu_hdv_fleet' (realistic layer, below) translates
#   the CO2 standards for new trucks into fleet shares per period.
#   green_mandate: share of the industrial hydrogen from renewable electrolysis (RFNBO; not pink). 'red3' = 60% from
#   2040 (RED III: 42% in 2030 and 60% in 2035; 42% in 2030 cannot be built within the 3 GW electrolyser limit), used by
#   '_real_h2eu'; 'nl_jaarverplichting' is the Dutch obligation of the realistic layer.
# --------------------------------------------------------------------------------------------------------------
CO2_CAPS = {'netzero': {2030: 60.7, 2040: 20.1, 2050: 6.7}}
# Hydrogen as a road fuel (RED III art. 25): >= 1% RFNBO in transport by 2030 (counted x2, so ~0.5% physically),
# within a combined 5.5% with advanced biofuels; kept at 1% after 2030. 'ambition': a stronger path (2% as argued by
# T&E, then rising). Share of the final energy of road transport (cars and trucks); the hydrogen trucks (FCET, H2-ICE)
# must use it and renewable electrolysis (not pink) must supply it on top of any industrial mandate.
# Battery-electric truck policies (NL), adjustable:
#   truck_toll  CO2-differentiated vrachtwagenheffing (since 1 July 2026), €/km; heaviest class (>32 t): regular 2027
#               tariffs = temporary Sep-Dec 2026 tariffs / 0.777: Euro-6 diesel 0.156 -> 0.20, zero-emission 0.030 ->
#               0.039 €/km (Stcrt. 2026, 18058). Converted per MWh of truck output with TOLL_KWH_OUT_PER_KM (3.0 kWh
#               diesel per km at 40%); applied to all truck-km (an upper bound: not every road is tolled).
#   bet_capex_subsidy  AanZET: 11.1% / 21% / 29% of a zero-emission N3 tractor's price (large / medium / small
#               firms), max €115,200; 2026 budget €119.2 M, oversubscribed on 1 October 2026; fully funded from the
#               truck toll (RVO, 2026) -> 20% of BET CAPEX in the 2030 period (an upper bound on the volume: the
#               budget covers some 1,000-2,500 trucks a year).
#   charging support   SPULA (20% of public heavy-duty charging costs), SPRILA (private chargers): bet_vom_factor 0.8.
TOLL_KWH_OUT_PER_KM = 1.2
TRUCK_TOLLS = {'nl2026': {'ICE': {2020: 0.0, 2030: 0.20, 2040: 0.20, 2050: 0.20},
                          'ZE': {2020: 0.0, 2030: 0.039, 2040: 0.039, 2050: 0.039}}}
BET_SUBSIDIES = {'aanzet': {2020: 0.0, 2030: 0.20, 2040: 0.0, 2050: 0.0}}
RFNBO_TRANSPORT = {'red3': {2030: 0.01, 2040: 0.01, 2050: 0.01}, 'ambition': {2030: 0.02, 2040: 0.05, 2050: 0.10}}
ROAD_TRANSPORT = ['ICE car', 'ICE car - existing', 'BEV', 'BEV - existing'] + TRUCKS
ZE_MANDATES = {'eu_hdv_fleet': {2030: 0.30, 2040: 0.65, 2050: 0.75},   # realistic layer: policy floor (a minimum)
               'market': {2030: 0.40, 2040: 0.90}}      # realistic layer: market ramp-up (a maximum, see below)
GREEN_MANDATES = {'red3': {2040: 0.60, 2050: 0.60},
                  # realistic layer: the Dutch annual RFNBO obligation for industry (bill 36 936, sent to parliament
                  # on 29 April 2026; start postponed to 1 January 2028, KGG letter of 23 September 2026): 4% in
                  # 2030 rising to 9.9% in 2035, kept after 2035; the measures together reach 8-15% instead of RED
                  # III's 42% in 2030 (Kamerstuk 36 936 nr. 4)
                  'nl_jaarverplichting': {2030: 0.04, 2040: 0.099, 2050: 0.099}}
# Hydrogen policies in the realistic layer (adjustable):
#   h2truck_capex_subsidy  SWiM (Subsidieregeling Waterstof in Mobiliteit, RVO 2026): 80% of the extra cost of a
#               hydrogen truck over a diesel truck (at most €300,000 for a heavy N3 fuel-cell truck; H2-ICE trucks
#               qualify) and 40% of heavy-duty stations; 2026 budget €45 M (a tender) -> 60% of the FCET and H2-ICE
#               CAPEX in the 2030 period (80% of the gap to a diesel truck); the volume fits the small RED III niche.
#   electrolyser_subsidy  OWE (Opschaling volledig hernieuwbare waterstof via elektrolyse): round 2 granted more
#               than €700 M to 602 MW (August 2025), the gap between green and fossil hydrogen -> 50% of the CAPEX of
#               electrolysers built in the 2030 period (OWE_SUBSIDY, an h2_scenario setting).
H2TRUCK_SUBSIDIES = {'swim': {2020: 0.0, 2030: 0.60, 2040: 0.0, 2050: 0.0}}
OWE_SUBSIDY = {2020: 0.0, 2030: 0.50, 2040: 0.0, 2050: 0.0}

# --------------------------------------------------------------------------------------------------------------
# Realistic layer (October 2026): the four scenarios under the policies in force and the real-world frictions they act
# on (all off in the core and extension runs). Policies (run_freight.TRUCK_POLICIES and H2_POLICIES;
# '_real_nopolicy' drops them):
#   EU CO2 standards for new trucks (Regulation (EU) 2024/1610: -45% 2030, -65% 2035, -90% 2040; zero-emission = below
#     3 g CO2/tkm, so H2-ICE counts) -> ze_min_share='eu_hdv_fleet', a floor on the zero-emission share of freight: the
#     fleet shares of the sales the standards imply EU-wide (~30% in 2030, ~55% in 2035, >= 75% from 2040; T&E, 2024;
#     1.9% in 2025, Mulholland & Benoit, 2026) with a 12-year truck life and new trucks driving more (vintage
#     calculation: 31% on average in the 2030s, 68% in the 2040s, 75% in the 2050s -> 0.30 / 0.65 / 0.75).
#     Dutch zero-emission zones for city logistics (from 2025; all trucks by 2030) fall within the urban segment.
#   ETS2 (from 2028) -> the CO2 price of road fuels in co2_price 'low' (PBL's low ETS2 path, 55 €/t; 170 in 2050).
#   Truck toll (vrachtwagenheffing, since 1 July 2026, CO2-differentiated under the Eurovignette Directive) ->
#     truck_toll='nl2026'; its revenue funds AanZET purchase subsidies -> bet_capex_subsidy='aanzet' (20% in the 2030s).
#   RED III (Directive (EU) 2023/2413) transport target for RFNBO, in NL through the ERE system (Energie voor Vervoer,
#     2026) -> rfnbo_transport='red3' (>= 1% of road transport energy, counted double, used by hydrogen trucks).
#   AFIR (Regulation (EU) 2023/1804): truck charging pools and hydrogen stations on the TEN-T network by 2030 -> the
#     market ramp-up and the hydrogen-truck availability below (infrastructure roll-out).
#   Hydrogen: the Dutch annual RFNBO obligation for industry -> green_mandate='nl_jaarverplichting' (4% in 2030, 9.9%
#     from 2035); OWE electrolyser subsidies -> electrolyser_subsidy=OWE_SUBSIDY; SWiM support for hydrogen trucks
#     -> h2truck_capex_subsidy='swim' (see below); RED III transport as above.
#   bet_tiers='nl'  BETs by duty cycle. One freight bus, but BETs come in three duty types with their own CAPEX and
#     charging penalty, each limited to its segment's share of freight energy (a stepwise supply curve, cheapest first):
#       urban and construction, depot charging, ~250 kWh battery      25%    CAPEX x0.8, VOM x0.5 (0.05 €/kWh)
#       regional and national distribution (the assignment's BET)     35%    CAPEX x1.0, VOM x1.0 (0.10 €/kWh)
#       long haul and international, ~800 kWh, half public charging   rest   CAPEX x1.3, VOM x2.5 (0.25 €/kWh)
#     Shares: TNO (2021) logistics CO2 in 2019 (10.6 Mt): 41% hinterland and continental transport, 34% city logistics
#     (incl. vans, which are not heavy-duty freight), 25% other national transport; part of the hinterland transport
#     (port to inland terminals) is regional. CAPEX: the battery pack is ~60% of a BET tractor's cost in 2020 and pack
#     costs halve by 2030 (Sharpe & Basma, 2022), so ~40% in 2030; BET packs are 400-900 kWh (Sharpe & Basma, 2022):
#     urban ~250 kWh, regional ~450 kWh, long haul ~800 kWh (0.55 / 1 / 1.8; CAPEX 0.6 + 0.4 x size ratio = 0.8 / 1 /
#     1.3). Charging: public megawatt charging costs €0.399/kWh ex VAT in NL from 1 January 2026 (Milence, 2025),
#     ~0.30 above wholesale; depot charging 8-21 ct/kWh in six European cities, Amsterdam 10.7 ex VAT (Basma et al.,
#     2022); long haul charges about half en route, plus a payload penalty. The X axis (BET costs) and BET policies
#     apply to all three types; FOM scales with CAPEX.
#   ze_max_share='market'  market ramp-up: zero-emission share of freight at most 40% (2030s average) and 90% (2040s):
#     the fleet shares that follow from Dutch sales running ahead of the EU (NL 9.3% of new heavy trucks in 2025 and
#     14% in Q4 2025, EU 1.9%; Mulholland & Benoit, 2026): sales of 45% in 2030, 80% in 2035 and 95% in 2040 give 46%
#     on average in the 2030s and 89% in the 2040s (same vintage calculation); 40% leaves room for delays in charging
#     roll-out and grid connections. Represents fleet turnover, charging roll-out (AFIR) and grid connections.
#   h2_truck_max_share='market'  hydrogen-truck availability: FCET + H2-ICE truck at most 3% of freight in the 2030s
#     (hydrogen trucks < 1% of sales; FCET series production not before 2030; ~27 public stations) and 25% in the
#     2040s (AFIR station network on the TEN-T corridors; long haul).
#   freight_heavy_share=0.05  heavy-duty special transport (heavy haulage, construction tippers and mixers, abnormal
#     loads; an assumption of ~5% of freight energy) where neither batteries (payload, charging time) nor fuel cells
#     (heat rejection is an issue in Class-8 fuel-cell trucks because of the higher radiator heat load; Wang &
#     Ahluwalia, 2026) fit: only ICE or H2-ICE trucks, the niche hydrogen combustion engines are built for (MAN, 2024:
#     'special transport tasks that require a special axle configuration', heavy goods such as construction, tank
#     and timber transport; Xue et al., 2025: high power requirements). So the segments are urban 25%, regional 35%,
#     long haul 35%, heavy 5%.
#   truck_fuel_price='diesel_nl' (moderate Y) / 'diesel_nl_sharp' (sharp Y): diesel ex VAT for the trucks.
#   truck_toll='nl2026' (in force since 1 July 2026) and hydrogen delivery at the middle of NREL's range
#   (fcet_vom_factor=1.5, ~€6/kg in 2030).
BET_TIERS = {'nl': {'BET - urban': dict(share=0.25, capex=0.8, vom=0.5),
                    'BET': dict(share=0.35, capex=1.0, vom=1.0),
                    'BET - long haul': dict(share=None, capex=1.3, vom=2.5)}}
H2_TRUCK_SHARES = {'market': {2030: 0.03, 2040: 0.25}}

# Alternative temporal profiles of the freight demand (columns of the sheet 'freight_profiles' in demand.xlsx)
FREIGHT_PROFILES = {'base': 'freight_road', 'sunday_ban': 'freight_sunday_ban', 'night_ban': 'freight_night_ban'}

FREIGHT_DEFAULTS = dict(
    # --- freight (assignment) ---
    bet_costs=None,               # 'constant' / 'decrease' / {'CAPEX': {..}, 'VOM': {..}}; None = database
    bet_vom_factor=1.0,           # multiplier on the BET VOM (charging penalty), for sensitivities
    gasoline_price=None,          # key of GASOLINE_PRICES or {year: €/MWh}; None = database
    fcet=True,                    # fuel-cell trucks (hydrogen as fuel) allowed
    fcet_capex_factor=1.0,        # multiplier on FCET CAPEX
    fcet_vom_factor=1.0,          # multiplier on the hydrogen delivery + station cost (VOM of FCET and H2-ICE truck)
    h2ice=None,                   # hydrogen combustion trucks allowed; None = as fcet (the hydrogen trucks together)
    h2ice_capex_factor=1.0,       # multiplier on H2-ICE truck CAPEX
    ice_only=False,               # counterfactual: no new zero-emission trucks (cost of switching)
    truck_stock=True,             # calibration test: False = no 2020 truck stock ('ICE truck - existing' and
                                  #   'BET - existing' off) and new ICE trucks and BETs allowed in the base year
    freight_profile='base',       # 'base', 'sunday_ban', 'night_ban' (time restrictions)
    freight_scale=1.0,            # multiplier on the freight demand (all periods)
    ze_max_share=None,            # {year: max ZE share of freight} or 'market' (diffusion / turnover limit)
    ze_min_share=None,            # {year: min share} or 'eu_hdv_fleet' (the CO2-standards floor)
    co2_cap=None,                 # {year: Mt CO2/yr} or 'netzero': a cap on the emissions of the whole system
    rfnbo_transport=None,         # {year: share} or 'red3' / 'ambition': renewable hydrogen in road transport
    truck_toll=None,              # 'nl2026' or {'ICE': {year: €/km}, 'ZE': {year: €/km}}: CO2-differentiated toll
    truck_fuel_price=None,        # 'diesel_nl' / 'diesel_nl_sharp' or {year: €/MWh}: own fuel price for ICE trucks
    bet_capex_subsidy=None,       # 'aanzet' or {year: share of BET CAPEX paid by subsidy}
    h2truck_capex_subsidy=None,   # 'swim' or {year: share of FCET and H2-ICE truck CAPEX paid by subsidy}
    h2_trucks_rfnbo=False,        # policy test: all hydrogen the trucks use is renewable (RFNBO at the pump)
    bet_tiers=None,               # realistic layer: 'nl' = BETs by duty cycle (urban / regional / long haul)
    h2_truck_max_share=None,      # realistic layer: 'market' or {year: max share of freight from FCET + H2-ICE truck}
    freight_heavy_share=None,     # realistic layer: share of freight that BETs and FCETs cannot serve (ICE or H2-ICE)
    rfnbo_multiplier=2.0,         # RED III counts RFNBO in transport double
    # --- water ---
    water_scarcity='none',        # key of WATER_SCARCITY ('none', 'driver') or a dict with
                                  #   caps/drought/budget/summer/derate
    water_drought=None,           # overrides the drought of the level: key of DROUGHTS, {category: share}, or a
                                  #   path {year: key or shares} (the driver)
    water_drought_months=None,    # months of the drought season (default June-September)
    water_allocation='verdringingsreeks',   # 'verdringingsreeks' (a quota per category) or 'cost_optimal' (one pool)
    electrolysis_category=3,      # verdringingsreeks category of freshwater electrolysis: 2, 3 or 4
    water_caps=None,              # overrides the caps of the level: {group: {year: MW}}
    water_cap_factor=1.0,         # multiplier on all caps (1 = as defined)
    water_budget=None,            # overrides the budget: {year: Mm3/yr} or a number
    water_budget_factor=1.0,      # multiplier on the budget
    water_summer_factor=None,     # overrides 'summer'
    thermal_summer_derate=None,   # overrides 'derate': a share or a path {year: share}
    water_alt_cost=1.4,           # €/m3 of alternative water (desalination, reuse) above a quota or the budget, or a
                                  #   key of WATER_ALT_COSTS ('low' 0.6 / 'central' 1.0 / 'high' 1.5 / 'group' 1.4,
                                  #   the group's desalination lever, 0.03 €/kg H2 at 22 L/kg). None = hard limit
    water_intensity=None,         # {tech: (m3/MWh, freshwater share)} overrides of WATER_INTENSITY
)
