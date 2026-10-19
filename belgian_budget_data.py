"""
Belgian General Government Budget Dataset & Policy Measures Catalog (2025-2029)
===============================================================================
Calibrated on projections from the Federal Planning Bureau (Federaal Planbureau),
the High Council of Finance (Hoge Raad van Financien), the National Bank of Belgium (NBB),
and estimates from the 2024-2025 federal coalition negotiations ("Supernota").

All monetary figures are expressed in Billions of Euros (€B) unless stated otherwise.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MacroYear:
    year: int
    gdp_nominal: float             # Nominal GDP (€B)
    baseline_deficit_pct: float    # Unchanged-policy budget deficit (% of GDP)
    baseline_debt_pct: float       # Unchanged-policy public debt (% of GDP, before new measures)
    ageing_cost_Increment: float   # Cumulative extra ageing cost vs 2024 (€B, pensions + healthcare)
    baseline_interest_bill: float  # Baseline interest expenditure (€B)
    marginal_olo_rate: float       # Marginal 10y Belgian OLO interest rate on new debt (fraction)

    @property
    def baseline_deficit_eur(self) -> float:
        return self.gdp_nominal * (self.baseline_deficit_pct / 100.0)


# 5-Year Horizon (2025 - 2029) representing the Belgian legislature / EU fiscal adjustment period
BASELINE_TRAJECTORY: List[MacroYear] = [
    MacroYear(
        year=2025,
        gdp_nominal=616.0,
        baseline_deficit_pct=4.7,
        baseline_debt_pct=105.8,
        ageing_cost_Increment=2.1,
        baseline_interest_bill=14.2,
        marginal_olo_rate=0.030,
    ),
    MacroYear(
        year=2026,
        gdp_nominal=636.5,
        baseline_deficit_pct=5.0,
        baseline_debt_pct=107.9,
        ageing_cost_Increment=4.3,
        baseline_interest_bill=15.6,
        marginal_olo_rate=0.031,
    ),
    MacroYear(
        year=2027,
        gdp_nominal=657.5,
        baseline_deficit_pct=5.3,
        baseline_debt_pct=110.3,
        ageing_cost_Increment=6.7,
        baseline_interest_bill=17.1,
        marginal_olo_rate=0.032,
    ),
    MacroYear(
        year=2028,
        gdp_nominal=679.2,
        baseline_deficit_pct=5.5,
        baseline_debt_pct=112.9,
        ageing_cost_Increment=9.2,
        baseline_interest_bill=18.7,
        marginal_olo_rate=0.033,
    ),
    MacroYear(
        year=2029,
        gdp_nominal=701.6,
        baseline_deficit_pct=5.7,
        baseline_debt_pct=115.6,
        ageing_cost_Increment=11.8,
        baseline_interest_bill=20.4,
        marginal_olo_rate=0.034,
    ),
]

# Belgium's semi-elasticity of the budget balance to GDP (automatic stabilizers / tax-to-GDP ratio)
BELGIAN_TAX_ELASTICITY_TAU = 0.48


@dataclass
class PolicyMeasure:
    id: str
    name: str
    dutch_name: str
    category: str                  # "Labour & Activation", "Pensions", "Healthcare & Social", "Wealth & Corporate Tax", "Consumption & Eco Tax", "Government Efficiency"
    measure_type: str              # "Expenditure Cut", "Structural Activation", "Revenue Increase"
    entity: str                    # "Entity I (Federal)", "Entity I (Social Security)", "Entity II (Regions/Communities)", "Joint (Entity I + II)"
    description: str
    
    # Budgetary parameters at benchmark scale (x = 1.0)
    structural_yield_eur: float    # Gross annual budgetary yield at full maturity when x = 1.0 (€B)
    max_intensity: float           # Upper bound u_i on decision variable x_i (e.g., 1.5 = 150% of benchmark scope)
    max_annual_ramp: float         # Maximum change per year dx_{i,t} (captures implementation speed constraints)
    maturation_profile: List[float] # Multiplier on yield across years if enacted immediately (or speed of realization)
    
    # Macroeconomic feedback
    keynesian_multiplier: float    # Short/medium-run GDP impact per €1B of gross fiscal yield.
                                   # > 0 means contractionary (demand drag); < 0 means expansionary (labour supply boost)
    
    # Multi-dimensional Social Cost Scores (scale 0.0 to 10.0 at x = 1.0)
    # 1. Equity & Poverty Protection (impact on lowest deciles, vulnerability, Gini)
    cost_equity: float
    # 2. Middle-Class Purchasing Power (impact on net wages, household consumption, indexation)
    cost_purchasing_power: float
    # 3. Economic Competitiveness & Investment (Laffer effect, capital flight, wage handicap)
    cost_competitiveness: float
    # 4. Public Service & Healthcare Quality (wait times, public administration capacity, infrastructure)
    cost_public_service: float
    
    # Convexity parameter: how sharply marginal social cost escalates as intensity x_i increases
    # Cost(x) ~ w_i * (linear_term * x + 0.5 * convexity * x^2)
    convexity_factor: float = 2.2
    
    # Fixed political/legislative friction cost if activated (z_i = 1)
    fixed_political_cost: float = 1.0


POLICY_MEASURES: List[PolicyMeasure] = [
    # =========================================================================
    # 1. LABOUR MARKET & ACTIVATION (Arbeidsmarkt & Activering)
    # =========================================================================
    PolicyMeasure(
        id="M01",
        name="Time-limit Unemployment Benefits (24 months) & Stronger Degressivity",
        dutch_name="Beperking werkloosheidsuitkeringen in de tijd (2 jaar) & sterkere degressiviteit",
        category="Labour & Activation",
        measure_type="Structural Activation",
        entity="Entity I (Social Security)",
        description=(
            "Cap standard unemployment benefits at 24 months with steeper degressivity after 6 and 12 months, "
            "combined with intensive VDAB/Forem/Actiris job-matching and partial outflow shift to municipal CPAS/OCMW."
        ),
        structural_yield_eur=1.95,
        max_intensity=1.5,
        max_annual_ramp=0.45,
        maturation_profile=[0.35, 0.70, 0.90, 1.00, 1.00],
        keynesian_multiplier=-0.15,  # Positive GDP supply effect via higher employment rate!
        cost_equity=6.8,
        cost_purchasing_power=3.0,
        cost_competitiveness=0.5,
        cost_public_service=2.5,    # Burden on local OCMW/CPAS
        convexity_factor=2.4,
        fixed_political_cost=2.5,
    ),
    PolicyMeasure(
        id="M02",
        name="Re-integration of Long-Term Sick (>500k) & Responsibility Contributions",
        dutch_name="Activering langdurig zieken (RIZIV-terugkeertrajecten & responsabilisering)",
        category="Labour & Activation",
        measure_type="Structural Activation",
        entity="Entity I (Social Security)",
        description=(
            "Mandatory re-integration pathways for the >500,000 workers in invalidity, financial incentives "
            "for employers/employees/mutuelles, and medical reassessment of residual work capacity."
        ),
        structural_yield_eur=2.20,
        max_intensity=1.5,
        max_annual_ramp=0.35,       # Takes institutional capacity to ramp up
        maturation_profile=[0.25, 0.55, 0.80, 0.95, 1.00],
        keynesian_multiplier=-0.25,  # Strong positive labour supply and GDP boost
        cost_equity=5.2,
        cost_purchasing_power=2.2,
        cost_competitiveness=1.5,
        cost_public_service=2.0,
        convexity_factor=2.6,
        fixed_political_cost=2.0,
    ),
    PolicyMeasure(
        id="M03",
        name="Labour Market Flexibility, Net Overtime Expansion & End of Early Exit (SWT)",
        dutch_name="Arbeidsmarktflexibiliteit, fiscaal voordelige overuren & uitdoof SWT",
        category="Labour & Activation",
        measure_type="Structural Activation",
        entity="Entity I (Federal)",
        description=(
            "Abolish remaining early retirement schemes (SWT/brugpensioen), annualize working time, "
            "simplify night/weekend work rules for e-commerce, and expand voluntary fiscal overtime."
        ),
        structural_yield_eur=1.25,
        max_intensity=1.4,
        max_annual_ramp=0.50,
        maturation_profile=[0.45, 0.75, 0.95, 1.00, 1.00],
        keynesian_multiplier=-0.20,  # Expands hours worked and output
        cost_equity=3.2,
        cost_purchasing_power=2.5,
        cost_competitiveness=0.2,
        cost_public_service=1.0,
        convexity_factor=2.0,
        fixed_political_cost=1.8,
    ),
    PolicyMeasure(
        id="M04",
        name="Regional Job-Placement Efficiency & Conditional Living Wage (Leefloon)",
        dutch_name="Resultaatsverbintenis VDAB/Forem/Actiris & voorwaardelijk leefloon",
        category="Labour & Activation",
        measure_type="Structural Activation",
        entity="Joint (Entity I + II)",
        description=(
            "Tie federal/regional transfers to activation performance of Forem and Actiris, "
            "introduce mandatory community service and language/training conditions for leefloon recipients."
        ),
        structural_yield_eur=1.10,
        max_intensity=1.5,
        max_annual_ramp=0.40,
        maturation_profile=[0.30, 0.60, 0.85, 1.00, 1.00],
        keynesian_multiplier=-0.10,
        cost_equity=5.8,
        cost_purchasing_power=2.0,
        cost_competitiveness=0.4,
        cost_public_service=1.8,
        convexity_factor=2.3,
        fixed_political_cost=1.6,
    ),

    # =========================================================================
    # 2. PENSIONS & AGEING (Pensioenen & Vergrijzing)
    # =========================================================================
    PolicyMeasure(
        id="M05",
        name="Harmonization of Civil Servant Pensions (Perequation & Career Calculation)",
        dutch_name="Harmonisatie ambtenarenpensioenen (afschaffing perequatie & langere referteperiode)",
        category="Pensions",
        measure_type="Expenditure Cut",
        entity="Entity I (Social Security)",
        description=(
            "Replace automatic link of civil servant pensions to active civil servant wage scales (perequation) "
            "with standard inflation indexation, and extend reference salary calculation from last 10 years to full career."
        ),
        structural_yield_eur=2.15,
        max_intensity=1.5,
        max_annual_ramp=0.40,
        maturation_profile=[0.30, 0.55, 0.75, 0.90, 1.00],
        keynesian_multiplier=0.25,
        cost_equity=2.5,
        cost_purchasing_power=5.5,
        cost_competitiveness=1.2,   # Slightly reduces civil service attractiveness
        cost_public_service=3.2,
        convexity_factor=2.3,
        fixed_political_cost=3.0,   # High public sector union resistance
    ),
    PolicyMeasure(
        id="M06",
        name="Strict Effective Work Requirement for Minimum Pension & Pension Malus",
        dutch_name="Striktere loopbaanvoorwaarde minimumpensioen & invoering pensioenmalus",
        category="Pensions",
        measure_type="Expenditure Cut",
        entity="Entity I (Social Security)",
        description=(
            "Require at least 30-35 years of effective worked days (limiting assimilated periods like long-term "
            "unemployment) for full minimum pension access, plus an actuarial malus for early retirement before statutory age."
        ),
        structural_yield_eur=1.85,
        max_intensity=1.5,
        max_annual_ramp=0.40,
        maturation_profile=[0.30, 0.60, 0.80, 0.95, 1.00],
        keynesian_multiplier=0.10,  # Partially offset by later retirement (longer working careers)
        cost_equity=6.2,
        cost_purchasing_power=5.0,
        cost_competitiveness=0.5,
        cost_public_service=1.0,
        convexity_factor=2.5,
        fixed_political_cost=2.8,
    ),
    PolicyMeasure(
        id="M07",
        name="Capping High Pensions (Wijninckx-plafond) & Reforming Survivor Pensions",
        dutch_name="Verlaging pensioenplafonds & hervorming overlevingspensioen naar overgangsuitkering",
        category="Pensions",
        measure_type="Expenditure Cut",
        entity="Entity I (Social Security)",
        description=(
            "Freeze the highest pension ceilings in real terms, increase solidarity contributions on top pensions, "
            "and accelerate conversion of lifetime survivor pensions into temporary transition allowances for working-age survivors."
        ),
        structural_yield_eur=0.95,
        max_intensity=1.5,
        max_annual_ramp=0.50,
        maturation_profile=[0.45, 0.70, 0.90, 1.00, 1.00],
        keynesian_multiplier=0.18,
        cost_equity=2.8,
        cost_purchasing_power=4.2,
        cost_competitiveness=1.5,
        cost_public_service=0.8,
        convexity_factor=2.1,
        fixed_political_cost=1.5,
    ),

    # =========================================================================
    # 3. HEALTHCARE, WAGE INDEXATION & SOCIAL PROTECTION
    # =========================================================================
    PolicyMeasure(
        id="M08",
        name="Moderate Real Healthcare Growth Norm (from 2.5% to 1.5% + Pharma/Hospital Efficiency)",
        dutch_name="Matiging reële groeinorm gezondheidszorg (RIZIV 1,5%) & doelmatigheid ziekenhuizen/farma",
        category="Healthcare & Social",
        measure_type="Expenditure Cut",
        entity="Entity I (Social Security)",
        description=(
            "Reduce the real annual growth cap of the RIZIV/INAMI healthcare budget from 2.5% to 1.5% above inflation "
            "via generic medicine quotas, medical imaging audits, and hospital network consolidation."
        ),
        structural_yield_eur=2.40,
        max_intensity=1.6,          # x=1.6 corresponds to near 0.9% real growth norm
        max_annual_ramp=0.45,
        maturation_profile=[0.35, 0.60, 0.80, 0.95, 1.00],
        keynesian_multiplier=0.35,
        cost_equity=5.5,
        cost_purchasing_power=3.8,
        cost_competitiveness=1.0,
        cost_public_service=7.8,    # High sensitivity if pushed too far (waiting times, out-of-pocket costs)
        convexity_factor=3.2,       # Steeply convex: initial efficiency gains are painless, deep cuts hurt patients
        fixed_political_cost=2.2,
    ),
    PolicyMeasure(
        id="M09",
        name="Targeted Indexation Reform ('Centenindex' / Partial Index Jump on High Brackets)",
        dutch_name="Hervorming automatische indexering (Centenindex / aftopping hoge lonen & uitkeringen)",
        category="Healthcare & Social",
        measure_type="Expenditure Cut",
        entity="Joint (Entity I + II)",
        description=(
            "Replace full percentage indexation above median income with a flat 'centenindex' or temporary index jump "
            "on public wages and social benefits, while shielding minimum benefits and boosts Belgian wage competitiveness."
        ),
        structural_yield_eur=2.80,
        max_intensity=1.5,
        max_annual_ramp=0.60,
        maturation_profile=[0.60, 0.85, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.30,  # Dampens domestic consumption, partially offset by better export competitiveness
        cost_equity=5.4,
        cost_purchasing_power=8.5,  # Directly hits household purchasing power
        cost_competitiveness=-1.2,  # Actually improves firm wage competitiveness!
        cost_public_service=2.0,
        convexity_factor=2.9,
        fixed_political_cost=4.5,   # Major political taboo / union strike trigger
    ),
    PolicyMeasure(
        id="M10",
        name="Means-Testing of Social Tariffs & Phasing Out Broad Energy/Service Vouchers",
        dutch_name="Inkomensgericht maken sociale tarieven & hervorming dienstencheques/premies",
        category="Healthcare & Social",
        measure_type="Expenditure Cut",
        entity="Joint (Entity I + II)",
        description=(
            "Link social energy/telecom tariffs strictly to net household income via a central social register "
            "and reduce tax deductibility / public subsidy per service voucher (dienstencheque)."
        ),
        structural_yield_eur=1.15,
        max_intensity=1.5,
        max_annual_ramp=0.50,
        maturation_profile=[0.50, 0.80, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.25,
        cost_equity=4.5,
        cost_purchasing_power=4.8,
        cost_competitiveness=1.2,
        cost_public_service=2.2,
        convexity_factor=2.1,
        fixed_political_cost=1.4,
    ),

    # =========================================================================
    # 4. CAPITAL, WEALTH & CORPORATE TAXATION (Vermogens- & Vennootschapsbelasting)
    # =========================================================================
    PolicyMeasure(
        id="M11",
        name="Capital Gains Tax on Financial Assets ('Solidariteitsbijdrage' 10% with Exemption)",
        dutch_name="Meerwaardebelasting op financiële activa (10% met vrijstelling kleine beleggers)",
        category="Wealth & Corporate Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Introduce a 10% capital gains tax on shares, bonds, and crypto with an annual exemption of €10,000 "
            "for retail investors, historical step-up at introduction, and safeguards for SME family businesses."
        ),
        structural_yield_eur=1.20,
        max_intensity=2.0,          # x=2.0 represents a broader ~15-20% capital gains tax
        max_annual_ramp=0.50,
        maturation_profile=[0.35, 0.70, 0.90, 1.00, 1.00],
        keynesian_multiplier=0.20,
        cost_equity=0.4,            # Strongly progressive (low equity cost)
        cost_purchasing_power=1.8,
        cost_competitiveness=5.8,   # Risk of capital mobility & reduced venture investment if scaled too high
        cost_public_service=0.5,
        convexity_factor=2.8,       # Laffer / behavioral avoidance rises steeply at high rates
        fixed_political_cost=2.5,
    ),
    PolicyMeasure(
        id="M12",
        name="Expansion of Securities Account Tax (Effectentaks) & Abolishing Tax Shelters",
        dutch_name="Verhoging effectentaks ( van 0,15% naar 0,30%) & afbouw fiscale achterpoortjes",
        category="Wealth & Corporate Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Double the annual tax on securities accounts above €1M from 0.15% to 0.30%, strengthen anti-abuse "
            "provisions, and cap passive investment tax shelters."
        ),
        structural_yield_eur=0.85,
        max_intensity=1.8,
        max_annual_ramp=0.60,
        maturation_profile=[0.65, 0.90, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.15,
        cost_equity=0.3,
        cost_purchasing_power=1.2,
        cost_competitiveness=4.9,
        cost_public_service=0.2,
        convexity_factor=2.7,
        fixed_political_cost=1.6,
    ),
    PolicyMeasure(
        id="M13",
        name="Reform of DBI-Aftrek, Management Companies & Copyright Regimes",
        dutch_name="Strengere voorwaarden DBI-aftrek, managementvennootschappen & auteursrechten",
        category="Wealth & Corporate Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Tighten participation exemption conditions (DBI-aftrek minimum threshold of €2.5M / 10% + financial asset test), "
            "curb personal tax optimization via management companies (VVPRbis/liquidation reserve), and restrict copyright regimes."
        ),
        structural_yield_eur=1.65,
        max_intensity=1.5,
        max_annual_ramp=0.50,
        maturation_profile=[0.50, 0.80, 0.95, 1.00, 1.00],
        keynesian_multiplier=0.28,
        cost_equity=0.8,
        cost_purchasing_power=2.6,  # Impacts freelancers/SME owners
        cost_competitiveness=6.2,   # Holding companies and headquarters sensitivity
        cost_public_service=0.4,
        convexity_factor=2.6,
        fixed_political_cost=2.2,
    ),
    PolicyMeasure(
        id="M14",
        name="Cut Wage Subsidies (Vrijstelling Doorstorting BV) & Fossil Corporate Subsidies",
        dutch_name="Hervorming vrijstelling doorstorting bedrijfsvoorheffing (ploegenarbeid) & fossiele subsidies",
        category="Wealth & Corporate Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Audit and tighten the €11B+ system of payroll withholding tax exemptions (ploegenarbeid, nachtarbeid) "
            "and phase out professional diesel and industrial fossil fuel subsidies."
        ),
        structural_yield_eur=1.90,
        max_intensity=1.5,
        max_annual_ramp=0.45,
        maturation_profile=[0.40, 0.70, 0.90, 1.00, 1.00],
        keynesian_multiplier=0.35,  # Directly increases effective labour/energy cost for industry
        cost_equity=1.5,
        cost_purchasing_power=2.0,
        cost_competitiveness=7.2,   # High sensitivity for manufacturing/logistics
        cost_public_service=0.5,
        convexity_factor=2.9,
        fixed_political_cost=2.0,
    ),

    # =========================================================================
    # 5. CONSUMPTION & GREEN TAXATION (Consumptie- & Milieubelastingen)
    # =========================================================================
    PolicyMeasure(
        id="M15",
        name="VAT Harmonization (Merging 6% & 12% Reduced Rates to 9%, Basic Food Exempt)",
        dutch_name="BTW-harmonisatie (samenvoeging 6% en 12% naar 9%, uitzondering basisvoeding)",
        category="Consumption & Eco Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Modernize the Belgian VAT basket as recommended by the High Council of Finance: merge reduced 6% and 12% "
            "rates into a single 9% rate while keeping unprocessed basic food, pharmaceuticals, and public transport at 6%/0%."
        ),
        structural_yield_eur=2.10,
        max_intensity=1.5,
        max_annual_ramp=0.55,
        maturation_profile=[0.55, 0.85, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.40,  # Consumption drag + slight mechanical CPI inflation bump
        cost_equity=5.8,            # Indirect taxes are somewhat regressive
        cost_purchasing_power=6.8,
        cost_competitiveness=2.2,   # Triggers automatic wage indexation if not neutralized in health index
        cost_public_service=0.5,
        convexity_factor=2.5,
        fixed_political_cost=2.4,
    ),
    PolicyMeasure(
        id="M16",
        name="Health & Environmental Excise Duties (Sugar, Tobacco, Alcohol, Aviation & Packaging)",
        dutch_name="Gezondheids- en milieuaccijnzen (suiker, tabak, alcohol, vliegtaks & verpakkingen)",
        category="Consumption & Eco Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Increase excise duties on tobacco, alcohol, ultra-processed sugary drinks, non-recyclable packaging, "
            "and short-haul flights/private jets, generating revenue while reducing long-term healthcare externalities."
        ),
        structural_yield_eur=0.95,
        max_intensity=1.6,
        max_annual_ramp=0.60,
        maturation_profile=[0.60, 0.85, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.22,
        cost_equity=3.8,
        cost_purchasing_power=3.5,
        cost_competitiveness=2.0,   # Cross-border shopping risk (grensaankopen in France/Luxembourg) if too high
        cost_public_service=-0.5,   # Preventative health benefit
        convexity_factor=2.6,
        fixed_political_cost=1.2,
    ),
    PolicyMeasure(
        id="M17",
        name="Accelerated Reform of Company Car & Fuel Card Tax Deductions (Salariswagens)",
        dutch_name="Versnelde hervorming fiscale gunstregimes salariswagens & tank-/laadkaarten",
        category="Consumption & Eco Tax",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Increase the taxable benefit-in-kind (Voordeel Alle Aard) on company cars, tighten CO2 solidarity "
            "contributions, and cap unlimited tax-free fuel/charging cards in favor of a mobility budget."
        ),
        structural_yield_eur=1.35,
        max_intensity=1.5,
        max_annual_ramp=0.45,
        maturation_profile=[0.35, 0.65, 0.85, 1.00, 1.00],
        keynesian_multiplier=0.25,
        cost_equity=1.2,            # Concentrated in upper-middle deciles
        cost_purchasing_power=6.0,  # Perceived as direct net wage loss by ~650,000 employees
        cost_competitiveness=3.8,
        cost_public_service=0.2,
        convexity_factor=2.4,
        fixed_political_cost=2.6,
    ),

    # =========================================================================
    # 6. GOVERNMENT EFFICIENCY & INSTITUTIONAL REFORM (Overheid & Staatsstructuur)
    # =========================================================================
    PolicyMeasure(
        id="M18",
        name="Federal & Regional Civil Service Efficiency (Selective Replacement & AI/Digitalization)",
        dutch_name="Afslanking overheidsapparaat (selectieve vervanging 1 op 3 & digitalisering)",
        category="Government Efficiency",
        measure_type="Expenditure Cut",
        entity="Joint (Entity I + II)",
        description=(
            "Replace only 1 in 3 retiring administrative civil servants (excluding front-line teachers, nurses, police, "
            "and judges), consolidate back-office IT agencies, and cut external consultancy spend by 35%."
        ),
        structural_yield_eur=1.80,
        max_intensity=1.5,
        max_annual_ramp=0.40,
        maturation_profile=[0.30, 0.55, 0.75, 0.90, 1.00],
        keynesian_multiplier=0.30,
        cost_equity=1.4,
        cost_purchasing_power=1.5,
        cost_competitiveness=0.6,
        cost_public_service=4.8,    # Risk to administrative processing speed if pushed beyond x=1.2
        convexity_factor=2.5,
        fixed_political_cost=1.5,
    ),
    PolicyMeasure(
        id="M19",
        name="Abolition of Senate, Lower Party Dotations & Institutional Streamlining",
        dutch_name="Afschaffing Senaat, verlaging partijdotaties & afslanking politieke kabinetten",
        category="Government Efficiency",
        measure_type="Expenditure Cut",
        entity="Joint (Entity I + II)",
        description=(
            "Abolish the Senate, shrink ministerial cabinets by 40%, freeze and reduce political party dotations, "
            "and phase out provincial intermediate administrative structures."
        ),
        structural_yield_eur=0.45,
        max_intensity=1.4,
        max_annual_ramp=0.70,
        maturation_profile=[0.60, 0.90, 1.00, 1.00, 1.00],
        keynesian_multiplier=0.15,
        cost_equity=0.1,
        cost_purchasing_power=0.1,
        cost_competitiveness=0.1,
        cost_public_service=0.6,
        convexity_factor=1.5,
        fixed_political_cost=0.8,   # High public legitimacy ("goed bestuur")
    ),
    PolicyMeasure(
        id="M20",
        name="Zero-Based Subsidy Audit across Federal, Flemish, Walloon & Brussels Levels",
        dutch_name="Grondige subsidiedoorlichting (Zero-Based Budgeting Federaal + Gewesten)",
        category="Government Efficiency",
        measure_type="Expenditure Cut",
        entity="Entity II (Regions/Communities)",
        description=(
            "Systematic zero-based review of the €18B+ regional and federal subsidy landscape (enterprise grants, "
            "overlapping cultural/intermunicipal funds, and non-performing structural subsidies)."
        ),
        structural_yield_eur=2.10,
        max_intensity=1.5,
        max_annual_ramp=0.45,
        maturation_profile=[0.35, 0.65, 0.85, 1.00, 1.00],
        keynesian_multiplier=0.28,
        cost_equity=2.6,
        cost_purchasing_power=2.0,
        cost_competitiveness=2.8,
        cost_public_service=3.6,
        convexity_factor=2.4,
        fixed_political_cost=1.8,
    ),
    PolicyMeasure(
        id="M21",
        name="Combatting Tax & Social Fraud (AI Data-Mining, Cash Limits & Real-Time E-Invoicing)",
        dutch_name="Versterkte strijd tegen fiscale en sociale fraude (e-invoicing & datamining)",
        category="Government Efficiency",
        measure_type="Revenue Increase",
        entity="Entity I (Federal)",
        description=(
            "Mandatory B2B/B2G real-time e-invoicing, cross-linking FOD Financiën and RSZ databases, "
            "and stricter enforcement against undeclared work and carousel fraud (realistic net collectible yield)."
        ),
        structural_yield_eur=1.30,
        max_intensity=1.4,
        max_annual_ramp=0.45,
        maturation_profile=[0.30, 0.60, 0.85, 1.00, 1.00],
        keynesian_multiplier=0.15,
        cost_equity=0.5,
        cost_purchasing_power=1.2,
        cost_competitiveness=1.8,
        cost_public_service=0.3,
        convexity_factor=3.0,       # Diminishing returns: "terugverdieneffecten" become unrealistic if over-relied upon
        fixed_political_cost=1.0,
    ),
]


# Pre-configured Ideological / Policy Scenarios for comparison
PRESET_PROFILES: Dict[str, Dict] = {
    "Balanced Welfare-Optimal (OR Benchmark)": {
        "description": "Equal social welfare weights across equity, purchasing power, competitiveness, and public services.",
        "weights": {
            "equity": 1.0,
            "purchasing_power": 1.0,
            "competitiveness": 1.0,
            "public_service": 1.0,
        },
        "target_deficit_2029_pct": 2.8,
        "min_spending_share_pct": 55.0,
        "locked_out_measures": [],
    },
    "Full Budget Equilibrium (0.0% Deficit Hawk)": {
        "description": "Strict 0.0% structural budget equilibrium by 2029 (~€39B baseline gap closed) with minimum social damage.",
        "weights": {
            "equity": 1.0,
            "purchasing_power": 1.0,
            "competitiveness": 1.0,
            "public_service": 1.0,
        },
        "target_deficit_2029_pct": 0.0,
        "min_spending_share_pct": 50.0,
        "locked_out_measures": [],
    },
    "Arizona / Supernota Coalition Compromise": {
        "description": "Focus on labour activation, pension reform, efficiency, and a moderate solidarity capital gains tax; shields automatic wage indexation.",
        "weights": {
            "equity": 1.1,
            "purchasing_power": 1.4,
            "competitiveness": 1.5,
            "public_service": 1.1,
        },
        "target_deficit_2029_pct": 2.9,
        "min_spending_share_pct": 65.0,
        "locked_out_measures": ["M09"],  # Shield automatic indexation
    },
    "Social-Progressive Protection": {
        "description": "Heavily penalizes poverty/equity harm and healthcare cuts; relies on capital taxation, fraud enforcement, and corporate subsidy cuts.",
        "weights": {
            "equity": 2.8,
            "purchasing_power": 2.0,
            "competitiveness": 0.5,
            "public_service": 2.5,
        },
        "target_deficit_2029_pct": 3.0,
        "min_spending_share_pct": 25.0,
        "locked_out_measures": ["M09", "M08"],
    },
    "Supply-Side & Competitiveness First": {
        "description": "Protects business competitiveness and capital investment; prioritizes activation, pension reform, and state downsizing.",
        "weights": {
            "equity": 0.6,
            "purchasing_power": 1.2,
            "competitiveness": 3.0,
            "public_service": 0.9,
        },
        "target_deficit_2029_pct": 2.5,
        "min_spending_share_pct": 75.0,
        "locked_out_measures": ["M11", "M12"],
    },
}

