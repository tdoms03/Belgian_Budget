"""
Interactive Streamlit Dashboard for the Belgian Budget Operations Research Model
================================================================================
Run with:
    streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from belgian_budget_data import (
    BASELINE_TRAJECTORY,
    BELGIAN_TAX_ELASTICITY_TAU,
    POLICY_MEASURES,
    PRESET_PROFILES,
)
from budget_or_model import BelgianBudgetOptimizer, OptimizationConfig

st.set_page_config(
    page_title="Belgian Budget OR Optimizer (2025–2029)",
    page_icon="🇧🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for KPI cards and clean layout
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: rgba(240, 242, 246, 0.55);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px 16px;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_optimizer() -> BelgianBudgetOptimizer:
    return BelgianBudgetOptimizer()


optimizer = get_optimizer()

# =============================================================================
# SIDEBAR: SCENARIO PRESETS, WELFARE WEIGHTS & POLITICAL CONSTRAINTS
# =============================================================================
st.sidebar.title("🇧🇪 Begroting OR Solver")
st.sidebar.caption(
    "Multi-Period Convex Quadratic Programming (QP) model of Belgian General Government consolidation (2025–2029)."
)

preset_name = st.sidebar.selectbox(
    "1. Policy / Coalition Preset",
    options=list(PRESET_PROFILES.keys()),
    index=0,
    help="Load pre-configured welfare weights, deficit targets, and political vetoes.",
)
preset = PRESET_PROFILES[preset_name]
st.sidebar.info(preset["description"])

st.sidebar.subheader("2. Fiscal Equilibrium Target")
target_deficit_2029 = st.sidebar.slider(
    "2029 Target Deficit (% of GDP)",
    min_value=0.0,
    max_value=4.5,
    value=float(preset["target_deficit_2029_pct"]),
    step=0.1,
    help="0.0% = Full structural budget equilibrium; 3.0% = EU Maastricht / EDP threshold; 5.7% = Unchanged policy baseline.",
)

min_annual_step = st.sidebar.slider(
    "Min. Annual Glidepath Step (% GDP/yr)",
    min_value=0.0,
    max_value=0.8,
    value=0.35,
    step=0.05,
    help="Prevents backloading all reforms to 2029; enforces steady annual progress under the EU net expenditure path.",
)

st.sidebar.subheader("3. Social Welfare Weights (ω)")
st.sidebar.caption("Higher weight = solver tries harder to avoid harm in this dimension.")

w_equity = st.sidebar.slider(
    "⚖️ Equity & Poverty Protection",
    min_value=0.1,
    max_value=4.0,
    value=float(preset["weights"]["equity"]),
    step=0.1,
)
w_pp = st.sidebar.slider(
    "🛒 Middle-Class Purchasing Power",
    min_value=0.1,
    max_value=4.0,
    value=float(preset["weights"]["purchasing_power"]),
    step=0.1,
)
w_comp = st.sidebar.slider(
    "🏭 Economic Competitiveness & Investment",
    min_value=0.1,
    max_value=4.0,
    value=float(preset["weights"]["competitiveness"]),
    step=0.1,
)
w_serv = st.sidebar.slider(
    "🏥 Public Services & Healthcare Quality",
    min_value=0.1,
    max_value=4.0,
    value=float(preset["weights"]["public_service"]),
    step=0.1,
)
w_ramp = st.sidebar.slider(
    "🚧 Implementation & Union Strike Friction",
    min_value=0.0,
    max_value=2.0,
    value=0.6,
    step=0.1,
)

st.sidebar.subheader("4. Political & Institutional Constraints")
min_spend_share = st.sidebar.slider(
    "Min. Share from Spending Cuts + Activation (%)",
    min_value=0.0,
    max_value=90.0,
    value=float(preset["min_spending_share_pct"]),
    step=5.0,
)
max_tax_share = st.sidebar.slider(
    "Max. Share from Tax Increases (%)",
    min_value=10.0,
    max_value=100.0,
    value=100.0 - float(preset["min_spending_share_pct"]) + 20.0
    if float(preset["min_spending_share_pct"]) > 20.0
    else 100.0,
    step=5.0,
)
min_regional_share = st.sidebar.slider(
    "Min. Effort from Regions/Joint (Entity II %)",
    min_value=0.0,
    max_value=35.0,
    value=12.0,
    step=2.0,
)

measure_options = {f"{m.id}: {m.name}": m.id for m in POLICY_MEASURES}
default_locked_labels = [
    f"{m.id}: {m.name}"
    for m in POLICY_MEASURES
    if m.id in preset["locked_out_measures"]
]
locked_labels = st.sidebar.multiselect(
    "🚫 Political Taboos (Veto Measures)",
    options=list(measure_options.keys()),
    default=default_locked_labels,
    help="Force selected policy measures to zero intensity (x_i = 0).",
)
locked_ids = [measure_options[lbl] for lbl in locked_labels]

st.sidebar.subheader("5. Macroeconomic Feedback")
enable_keynesian = st.sidebar.checkbox(
    "Include Keynesian & Supply Multipliers", value=True
)
enable_snowball = st.sidebar.checkbox(
    "Include Endogenous OLO Interest Savings", value=True
)

# Build config & solve
config = OptimizationConfig(
    target_deficit_2029_pct=target_deficit_2029,
    min_annual_deficit_reduction_pct=min_annual_step,
    weight_equity=w_equity,
    weight_purchasing_power=w_pp,
    weight_competitiveness=w_comp,
    weight_public_service=w_serv,
    weight_ramp_friction=w_ramp,
    min_spending_and_activation_share_pct=min_spend_share,
    max_tax_share_pct=max_tax_share,
    min_regional_joint_share_pct=min_regional_share,
    enable_keynesian_feedback=enable_keynesian,
    enable_interest_snowball=enable_snowball,
    locked_out_measures=locked_ids,
)

result = optimizer.solve(config)

# =============================================================================
# HEADER & EXECUTIVE SUMMARY BANNER
# =============================================================================
st.title("🇧🇪 Belgian Budget Equilibrium Optimizer (2025–2029)")
st.markdown(
    "Operations Research model minimizing convex social, economic, and distributional costs "
    "to bring Belgium's General Government budget (*Entity I + Entity II*) to equilibrium."
)

if not result.success or result.final_deficit_2029_pct > target_deficit_2029 + 0.08:
    st.warning(
        f"⚠️ **Constraint Tension Detected:** With the current political vetoes and mix constraints, "
        f"the lowest achievable 2029 deficit is **{result.final_deficit_2029_pct:.2f}% of GDP** "
        f"(target was {target_deficit_2029:.2f}%). Try relaxing political taboos or fiscal mix bounds."
    )

base_2029 = BASELINE_TRAJECTORY[-1]
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "2029 Deficit (% GDP)",
        f"{result.final_deficit_2029_pct:.2f}%",
        delta=f"{result.final_deficit_2029_pct - base_2029.baseline_deficit_pct:.2f}% vs baseline (5.7%)",
        delta_color="inverse",
    )
with col2:
    st.metric(
        "2029 Deficit (€B)",
        f"€{result.final_deficit_2029_eur:.1f}B",
        delta=f"-€{result.total_deficit_reduction_2029_eur:.1f}B vs €{base_2029.baseline_deficit_eur:.1f}B",
        delta_color="inverse",
    )
with col3:
    st.metric(
        "Gross Policy Effort",
        f"€{result.gross_effort_2029_eur:.1f}B",
        delta=f"Net Primary: €{result.net_primary_effort_2029_eur:.1f}B",
        delta_color="off",
    )
with col4:
    st.metric(
        "OLO Interest Saved (2029)",
        f"€{result.interest_saved_2029_eur:.2f}B",
        delta="Snowball reduction",
        delta_color="normal",
    )
with col5:
    st.metric(
        "2029 Debt-to-GDP",
        f"{result.final_debt_2029_pct:.1f}%",
        delta=f"{result.final_debt_2029_pct - base_2029.baseline_debt_pct:.1f}% vs 115.6% base",
        delta_color="inverse",
    )
with col6:
    st.metric(
        "2029 GDP Impact",
        f"{result.cumulative_gdp_impact_2029_pct:+.2f}%",
        delta=f"Shadow Price: {result.marginal_social_cost_per_bn:.1f} cost/€B",
        delta_color="normal" if result.cumulative_gdp_impact_2029_pct >= 0 else "inverse",
    )

# =============================================================================
# TABS
# =============================================================================
tab_traj, tab_mix, tab_pareto, tab_math = st.tabs(
    [
        "📈 1. Macro & Fiscal Trajectory",
        "🧩 2. Optimal Policy Portfolio (De Begrotingspuzzel)",
        "⚖️ 3. Social Cost & Pareto Frontier",
        "📐 4. Mathematical OR Formulation & Data",
    ]
)

# -----------------------------------------------------------------------------
# TAB 1: MACRO & FISCAL TRAJECTORY
# -----------------------------------------------------------------------------
with tab_traj:
    tdf = result.trajectory_df
    c_left, c_right = st.columns(2)

    with c_left:
        fig_def = go.Figure()
        fig_def.add_trace(
            go.Scatter(
                x=tdf["Year"],
                y=tdf["Baseline_Deficit_Pct"],
                mode="lines+markers",
                name="Unchanged Policy Baseline (Ongewijzigd beleid)",
                line=dict(color="#ef4444", width=3, dash="dash"),
            )
        )
        fig_def.add_trace(
            go.Scatter(
                x=tdf["Year"],
                y=tdf["Optimized_Deficit_Pct"],
                mode="lines+markers+text",
                text=[f"{v:.2f}%" for v in tdf["Optimized_Deficit_Pct"]],
                textposition="top center",
                name="OR Optimized Trajectory",
                line=dict(color="#10b981", width=4),
            )
        )
        fig_def.add_hline(
            y=3.0,
            line_dash="dot",
            line_color="#f59e0b",
            annotation_text="EU Maastricht 3.0% Threshold",
            annotation_position="bottom right",
        )
        fig_def.add_hline(
            y=0.0,
            line_dash="solid",
            line_color="#3b82f6",
            annotation_text="0.0% Full Budget Equilibrium",
            annotation_position="bottom left",
        )
        fig_def.update_layout(
            title="General Government Budget Deficit (% of GDP, 2025–2029)",
            xaxis_title="Year",
            yaxis_title="Deficit (% of GDP)",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig_def, use_container_width=True)

    with c_right:
        fig_debt = go.Figure()
        fig_debt.add_trace(
            go.Scatter(
                x=tdf["Year"],
                y=tdf["Baseline_Debt_Pct"],
                mode="lines+markers",
                name="Baseline Debt Trajectory (% GDP)",
                line=dict(color="#ef4444", width=3, dash="dash"),
            )
        )
        fig_debt.add_trace(
            go.Scatter(
                x=tdf["Year"],
                y=tdf["Optimized_Debt_Pct"],
                mode="lines+markers+text",
                text=[f"{v:.1f}%" for v in tdf["Optimized_Debt_Pct"]],
                textposition="bottom center",
                name="Optimized Debt Trajectory (% GDP)",
                line=dict(color="#3b82f6", width=4),
            )
        )
        fig_debt.update_layout(
            title="Belgian Public Debt-to-GDP Ratio (Snowball Stabilization, 2025–2029)",
            xaxis_title="Year",
            yaxis_title="Public Debt (% of GDP)",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig_debt, use_container_width=True)

    # 2029 Deficit Bridge Waterfall Chart
    st.subheader("🌉 2029 Fiscal Consolidation Bridge (How the Deficit Gap is Closed)")
    mdf = result.measures_summary_df
    spend_gross = mdf[mdf["Type"] == "Expenditure Cut"]["Gross_Yield_2029_B"].sum()
    act_gross = mdf[mdf["Type"] == "Structural Activation"]["Gross_Yield_2029_B"].sum()
    tax_gross = mdf[mdf["Type"] == "Revenue Increase"]["Gross_Yield_2029_B"].sum()
    macro_leakage = (
        result.net_primary_effort_2029_eur - result.gross_effort_2029_eur
    )  # positive if activation dominates, negative if demand drag dominates
    int_saved = result.interest_saved_2029_eur

    fig_water = go.Figure(
        go.Waterfall(
            name="2029 Bridge",
            orientation="v",
            measure=[
                "absolute",
                "relative",
                "relative",
                "relative",
                "relative",
                "relative",
                "total",
            ],
            x=[
                "2029 Baseline Deficit",
                "Expenditure Cuts",
                "Labour Activation",
                "Revenue / Tax Measures",
                "Keynesian/Supply Feedback",
                "OLO Interest Saved",
                "2029 Optimized Deficit",
            ],
            textposition="outside",
            text=[
                f"€{base_2029.baseline_deficit_eur:.1f}B",
                f"-€{spend_gross:.1f}B",
                f"-€{act_gross:.1f}B",
                f"-€{tax_gross:.1f}B",
                f"{-macro_leakage:+.2f}B",
                f"-€{int_saved:.2f}B",
                f"€{result.final_deficit_2029_eur:.1f}B",
            ],
            y=[
                base_2029.baseline_deficit_eur,
                -spend_gross,
                -act_gross,
                -tax_gross,
                -macro_leakage,
                -int_saved,
                result.final_deficit_2029_eur,
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#10b981"}},
            increasing={"marker": {"color": "#f59e0b"}},
            totals={"marker": {"color": "#3b82f6"}},
        )
    )
    fig_water.update_layout(
        title="2029 Budget Deficit Waterfall (€ Billions)",
        yaxis_title="€ Billions",
        height=430,
    )
    st.plotly_chart(fig_water, use_container_width=True)

    st.subheader("📋 Multi-Year Macroeconomic & Fiscal Table (2025–2029)")
    st.dataframe(
        tdf.style.format(
            {
                "Baseline_GDP_B": "€{:.1f}B",
                "Optimized_GDP_B": "€{:.1f}B",
                "GDP_Impact_B": "{:+.2f}B",
                "GDP_Impact_Pct": "{:+.2f}%",
                "Baseline_Deficit_B": "€{:.2f}B",
                "Baseline_Deficit_Pct": "{:.2f}%",
                "Optimized_Deficit_B": "€{:.2f}B",
                "Optimized_Deficit_Pct": "{:.2f}%",
                "Gross_Consolidation_B": "€{:.2f}B",
                "Macro_Feedback_Loss_B": "{:+.2f}B",
                "Net_Primary_Effort_B": "€{:.2f}B",
                "Interest_Savings_B": "€{:.2f}B",
                "Total_Deficit_Reduction_B": "€{:.2f}B",
                "Baseline_Debt_Pct": "{:.1f}%",
                "Optimized_Debt_Pct": "{:.1f}%",
                "Ageing_Cost_Drift_B": "+€{:.1f}B",
            }
        ),
        use_container_width=True,
    )

# -----------------------------------------------------------------------------
# TAB 2: OPTIMAL POLICY PORTFOLIO ("DE BEGROTINGSPUZZEL")
# -----------------------------------------------------------------------------
with tab_mix:
    mdf = result.measures_summary_df.sort_values("Net_Yield_2029_B", ascending=True)

    col_bar, col_pie = st.columns([2, 1])

    with col_bar:
        fig_bars = px.bar(
            mdf,
            x="Net_Yield_2029_B",
            y="Measure",
            color="Category",
            orientation="h",
            hover_data=[
                "Dutch_Name",
                "Intensity_2029",
                "Max_Intensity",
                "Gross_Yield_2029_B",
                "Macro_Retention_Pct",
                "Social_Cost_2029",
            ],
            title="Optimal 2029 Net Budgetary Yield per Policy Measure (€ Billions)",
            labels={
                "Net_Yield_2029_B": "2029 Net Budgetary Yield (€B, after macro feedback)",
                "Measure": "",
            },
            height=680,
        )
        fig_bars.update_layout(yaxis=dict(tickfont=dict(size=11)))
        st.plotly_chart(fig_bars, use_container_width=True)

    with col_pie:
        by_type = (
            result.measures_summary_df.groupby("Type")["Gross_Yield_2029_B"]
            .sum()
            .reset_index()
        )
        fig_type = px.pie(
            by_type,
            values="Gross_Yield_2029_B",
            names="Type",
            hole=0.45,
            title="Consolidation Mix by Instrument Type (Gross €B)",
            color="Type",
            color_discrete_map={
                "Expenditure Cut": "#3b82f6",
                "Structural Activation": "#10b981",
                "Revenue Increase": "#f59e0b",
            },
        )
        st.plotly_chart(fig_type, use_container_width=True)

        by_entity = (
            result.measures_summary_df.groupby("Entity")["Gross_Yield_2029_B"]
            .sum()
            .reset_index()
        )
        fig_ent = px.pie(
            by_entity,
            values="Gross_Yield_2029_B",
            names="Entity",
            hole=0.45,
            title="Effort Sharing by Belgian Government Entity",
        )
        st.plotly_chart(fig_ent, use_container_width=True)

    # Heatmap of implementation intensities across 2025-2029
    st.subheader("🗓️ Multi-Year Reform Sequencing & Phasing Heatmap (Intensity x_i,t)")
    st.caption(
        "Intensity 1.00 = 100% of the benchmark Supernota / High Council of Finance reform scope. "
        "Notice how the OR solver frontloads high-retention, low-friction reforms to capture compounding OLO interest savings."
    )
    heat_df = result.measures_summary_df.set_index("Measure")[
        [
            "Intensity_2025",
            "Intensity_2026",
            "Intensity_2027",
            "Intensity_2028",
            "Intensity_2029",
        ]
    ]
    heat_df.columns = ["2025", "2026", "2027", "2028", "2029"]
    fig_heat = px.imshow(
        heat_df,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="YlGnBu",
        title="Optimal Policy Intensity Schedule (2025–2029)",
        height=620,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("📊 Detailed Policy Portfolio Table")
    st.dataframe(
        result.measures_summary_df.sort_values(
            "Net_Yield_2029_B", ascending=False
        )[
            [
                "ID",
                "Measure",
                "Category",
                "Type",
                "Entity",
                "Intensity_2025",
                "Intensity_2027",
                "Intensity_2029",
                "Max_Intensity",
                "Gross_Yield_2029_B",
                "Net_Yield_2029_B",
                "Macro_Retention_Pct",
                "Social_Cost_2029",
                "Cost_Per_Net_Bn",
            ]
        ],
        use_container_width=True,
    )

# -----------------------------------------------------------------------------
# TAB 3: SOCIAL COST & PARETO FRONTIER
# -----------------------------------------------------------------------------
with tab_pareto:
    st.subheader("📉 Pareto Frontier: Fiscal Equilibrium vs. Social Cost")
    st.markdown(
        "By sweeping the 2029 deficit target from **4.5% of GDP** down to **0.0% (Full Budget Equilibrium)**, "
        "the OR solver traces the **Pareto Efficiency Frontier**. Because marginal social harm is convex, "
        "closing the first €15B via painless efficiencies and broad low-rate measures has a low social cost, "
        "whereas pushing all the way to 0.0% requires increasingly painful trade-offs (steeply rising shadow price $\\lambda$)."
    )

    pareto_df = optimizer.compute_pareto_frontier(config)

    c_p1, c_p2 = st.columns(2)
    with c_p1:
        fig_par = go.Figure()
        fig_par.add_trace(
            go.Scatter(
                x=pareto_df["Achieved_Deficit_2029_Pct"],
                y=pareto_df["Total_Social_Cost"],
                mode="lines+markers+text",
                text=[f"€{g:.1f}B" for g in pareto_df["Gross_Effort_2029_B"]],
                textposition="top center",
                name="Pareto Frontier (Gross Effort €B)",
                line=dict(color="#8b5cf6", width=4),
            )
        )
        fig_par.add_vline(
            x=result.final_deficit_2029_pct,
            line_dash="dash",
            line_color="#10b981",
            annotation_text=f"Selected Target ({result.final_deficit_2029_pct:.1f}%)",
        )
        fig_par.update_layout(
            title="Pareto Frontier: Total Social Cost vs. Achieved 2029 Deficit (% GDP)",
            xaxis_title="2029 Budget Deficit (% of GDP) — Lower means tighter equilibrium",
            yaxis_title="Minimum Cumulative Social Cost Index",
            xaxis=dict(autorange="reversed"),
            height=430,
        )
        st.plotly_chart(fig_par, use_container_width=True)

    with c_p2:
        fig_cost_dim = px.bar(
            x=list(result.cost_breakdown.keys()),
            y=list(result.cost_breakdown.values()),
            color=list(result.cost_breakdown.keys()),
            title="Decomposition of Social Cost by Welfare Dimension (2029)",
            labels={"x": "Welfare Dimension", "y": "Weighted Social Cost Contribution"},
            height=430,
        )
        st.plotly_chart(fig_cost_dim, use_container_width=True)

    st.subheader("🎯 Measure Efficiency Map: Net Budgetary Yield vs. Social Cost per €1B")
    active_m = result.measures_summary_df[
        result.measures_summary_df["Net_Yield_2029_B"] > 0.05
    ].copy()
    fig_scat = px.scatter(
        active_m,
        x="Net_Yield_2029_B",
        y="Cost_Per_Net_Bn",
        size="Gross_Yield_2029_B",
        color="Category",
        hover_name="Measure",
        text="ID",
        title="Active Measures: 2029 Net Fiscal Yield (€B) vs. Average Social Cost per Net €1B",
        labels={
            "Net_Yield_2029_B": "2029 Net Primary Yield (€B)",
            "Cost_Per_Net_Bn": "Social Cost per €1B Net Yield (Lower = More Efficient)",
        },
        height=480,
    )
    fig_scat.update_traces(textposition="top center")
    st.plotly_chart(fig_scat, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: MATHEMATICAL FORMULATION & CATALOG
# -----------------------------------------------------------------------------
with tab_math:
    st.subheader("📐 Mathematical Operations Research Formulation")
    st.markdown(
        r"""
### 1. Decision Variables & Multi-Year Horizon
Let $\mathcal{M} = \{1, \dots, 21\}$ be the set of structural policy measures and $\mathcal{T} = \{2025, 2026, 2027, 2028, 2029\}$ be the 5-year planning horizon.
- **$x_{i,t} \in [0, u_i \gamma_{i,t}]$**: Implementation intensity of measure $i \in \mathcal{M}$ in year $t \in \mathcal{T}$, where $x_{i,t} = 1.0$ corresponds to the benchmark full reform scale (e.g., *Supernota* / High Council of Finance standard) and $\gamma_{i,t} \in (0,1]$ is the administrative maturation ceiling in year $t$.
- **$\Delta x_{i,t} = x_{i,t} - x_{i,t-1}$**: Annual policy ramp-up in year $t$.

---

### 2. Convex Multi-Dimensional Social Cost Objective
Why do single-instrument solutions (e.g., closing €30B solely through VAT hikes or solely through healthcare cuts) fail? Because **marginal social, economic, and Laffer distortions escalate convexly** with the intensity of any single measure. We minimize the discounted quadratic social welfare loss:

$$\min_{\mathbf{x}} \sum_{t \in \mathcal{T}} (1 + \delta)^{-t} \sum_{i \in \mathcal{M}} \left[ \psi_t \, w_i \left( x_{i,t} + \frac{1}{2} \kappa_i x_{i,t}^2 \right) + \eta \, F_i \left( x_{i,t} - x_{i,t-1} \right)^2 \right]$$

where the composite social cost weight $w_i$ reflects policymaker welfare preferences $\boldsymbol{\omega}$:

$$w_i = \omega_{\text{eq}} c^{\text{equity}}_i + \omega_{\text{pp}} c^{\text{purchasing}}_i + \omega_{\text{comp}} c^{\text{comp}}_i + \omega_{\text{serv}} c^{\text{service}}_i$$

and $\kappa_i > 0$ is the measure-specific convexity parameter (capturing Laffer tax avoidance, hospital waiting lists, or deep poverty impact), while $F_i (\Delta x_{i,t})^2$ penalizes abrupt single-year shock therapy.

---

### 3. Macroeconomic Multipliers, Terugverdieneffecten & Snowball Interest Dynamics
For each year $t \in \mathcal{T}$:
1. **Gross Budgetary Effort**:
   $$Y^{\text{gross}}_t(\mathbf{x}) = \sum_{i \in \mathcal{M}} \beta_i x_{i,t}$$
2. **Short/Medium-Run GDP Feedback** (with Keynesian demand drag $\mu_i > 0$ for tax hikes/spending cuts and **expansionary labour-supply boost $\mu_i < 0$** for activation reforms M01–M04):
   $$\Delta \text{GDP}_t(\mathbf{x}) = -\sum_{i \in \mathcal{M}} \mu_i \beta_i x_{i,t}$$
3. **Automatic Stabilizers & Tax Base Feedback** (Belgian semi-elasticity $\tau = 0.48$):
   $$\Delta B^{\text{primary}}_t(\mathbf{x}) = \sum_{i \in \mathcal{M}} \beta_i (1 - \tau \mu_i) x_{i,t}$$
4. **Endogenous OLO Debt-Interest Snowball Savings** (at marginal 10-year OLO bond yield $r_t \approx 3.0\% - 3.4\%$):
   $$\Delta B^{\text{total}}_t(\mathbf{x}) = \Delta B^{\text{primary}}_t(\mathbf{x}) + r_t \sum_{s=2025}^{t-1} \Delta B^{\text{total}}_s(\mathbf{x})$$
   *Note: Because early consolidation reduces debt accumulation in years $s < t$, the solver endogenously discovers the value of frontloading structural reforms to avoid compounding interest charges!*

---

### 4. Exact Denominator-Adjusted Fiscal Equilibrium & Political Constraints
- **Exact Deficit-to-GDP Target Constraint** (accounting for both numerator deficit reduction and denominator GDP feedback):
  $$\frac{\text{Deficit}^{\text{base}}_t - \Delta B^{\text{total}}_t(\mathbf{x})}{\text{GDP}^{\text{base}}_t + \Delta \text{GDP}_t(\mathbf{x})} \le d^{\max}_t \iff \Delta B^{\text{total}}_t(\mathbf{x}) + d^{\max}_t \Delta \text{GDP}_t(\mathbf{x}) \ge \text{Deficit}^{\text{base}}_t - d^{\max}_t \text{GDP}^{\text{base}}_t \quad \forall t \in \mathcal{T}$$
- **Structural Monotonicity & Administrative Ramp-Up Speed**:
  $$0 \le x_{i,t} - x_{i,t-1} \le \rho_i \quad \forall i \in \mathcal{M}, \, t \in \mathcal{T}$$
- **Fiscal Mix & Institutional Effort Sharing (Entity I vs. Entity II)**:
  $$\sum_{i \in \mathcal{M}_{\text{spend} \cup \text{act}}} \beta_i x_{i,T} \ge \theta_{\text{spend}} \sum_{i \in \mathcal{M}} \beta_i x_{i,T}, \qquad \sum_{i \in \mathcal{M}_{\text{Entity II}}} \beta_i x_{i,T} \ge \theta_{\text{reg}} \sum_{i \in \mathcal{M}} \beta_i x_{i,T}$$
        """
    )

    st.subheader("📚 Full Catalog of Calibrated Belgian Policy Measures")
    catalog_rows = [
        {
            "ID": m.id,
            "English Name": m.name,
            "Dutch Name (Supernota / HRF)": m.dutch_name,
            "Category": m.category,
            "Type": m.measure_type,
            "Entity": m.entity,
            "Benchmark Yield (x=1.0, €B)": m.structural_yield_eur,
            "Max Scale (u_i)": m.max_intensity,
            "Keynesian Multiplier (μ_i)": m.keynesian_multiplier,
            "Equity Cost": m.cost_equity,
            "Purchasing Power Cost": m.cost_purchasing_power,
            "Competitiveness Cost": m.cost_competitiveness,
            "Public Service Cost": m.cost_public_service,
            "Convexity (κ_i)": m.convexity_factor,
            "Description": m.description,
        }
        for m in POLICY_MEASURES
    ]
    st.dataframe(pd.DataFrame(catalog_rows), use_container_width=True)

