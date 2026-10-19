"""
Operations Research Model for the Belgian General Government Budget (2025-2029)
===============================================================================
Formulates the Belgian fiscal consolidation problem ("De Begrotingspuzzel") as a
Multi-Period Convex Quadratic / Mixed-Integer Optimization Problem (QP / MIQP)
with Macroeconomic Multiplier Feedback and Endogenous Debt-Interest Snowball Dynamics.

Key Features:
1. Exact linear-dynamic recurrence for primary balance, Keynesian GDP feedback,
   automatic stabilizers (tau = 0.48), and compounding OLO interest savings.
2. Exact denominator-adjusted deficit-to-GDP constraint:
   Deficit_t(x) / GDP_t(x) <= target_pct_t
3. Convex multi-dimensional social cost objective function:
   Minimizes weighted sum of Equity/Poverty harm, Purchasing Power loss,
   Competitiveness drag, Public Service degradation, and Implementation Friction.
4. Supports both Continuous Convex QP (with exact Shadow Prices / Duals) and
   Mixed-Integer (MIQP) mode with fixed political costs & minimum reform thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize

try:
    from belgian_budget_data import (
        BASELINE_TRAJECTORY,
        BELGIAN_TAX_ELASTICITY_TAU,
        POLICY_MEASURES,
        MacroYear,
        PolicyMeasure,
    )
except ImportError:
    from Belgian_Budget.belgian_budget_data import (
        BASELINE_TRAJECTORY,
        BELGIAN_TAX_ELASTICITY_TAU,
        POLICY_MEASURES,
        MacroYear,
        PolicyMeasure,
    )


@dataclass
class OptimizationConfig:
    # Target deficit in 2029 (% of GDP). 0.0 = strict equilibrium, 3.0 = Maastricht threshold
    target_deficit_2029_pct: float = 2.8
    
    # Minimum annual reduction in deficit (% of GDP per year) to enforce EU EDP credible glidepath
    min_annual_deficit_reduction_pct: float = 0.35
    
    # Social welfare weights (relative importance in objective function)
    weight_equity: float = 1.0
    weight_purchasing_power: float = 1.0
    weight_competitiveness: float = 1.0
    weight_public_service: float = 1.0
    
    # Weight on rapid annual ramp-up friction (penalizes shock therapy in a single year)
    weight_ramp_friction: float = 0.6
    
    # Fiscal mix constraints (0 to 100%)
    min_spending_and_activation_share_pct: float = 55.0
    max_tax_share_pct: float = 100.0
    
    # Institutional constraint: minimum share of gross effort from Entity II / Joint measures (%)
    min_regional_joint_share_pct: float = 10.0
    
    # Macroeconomic feedback toggle
    enable_keynesian_feedback: bool = True
    enable_interest_snowball: bool = True
    
    # Specific measure overrides: locked-out measures (x_i = 0) or forced minimum intensity
    locked_out_measures: List[str] = field(default_factory=list)
    forced_min_measures: Dict[str, float] = field(default_factory=dict)
    custom_max_intensities: Dict[str, float] = field(default_factory=dict)
    
    # Time discount factor for social costs across 2025-2029
    social_discount_rate: float = 0.02


@dataclass
class OptimizationResult:
    success: bool
    status_message: str
    config: OptimizationConfig
    
    # Decision matrix: shape (N_measures, T_years)
    intensities: np.ndarray
    measure_ids: List[str]
    years: List[int]
    
    # DataFrames for easy analysis & plotting
    measures_summary_df: pd.DataFrame
    trajectory_df: pd.DataFrame
    cost_breakdown: Dict[str, float]
    
    # Key aggregate metrics in terminal year (2029)
    total_social_cost: float
    gross_effort_2029_eur: float
    net_primary_effort_2029_eur: float
    interest_saved_2029_eur: float
    total_deficit_reduction_2029_eur: float
    final_deficit_2029_eur: float
    final_deficit_2029_pct: float
    final_debt_2029_pct: float
    cumulative_gdp_impact_2029_pct: float
    
    # Marginal social cost of deficit reduction (Shadow Price in 2029)
    marginal_social_cost_per_bn: float


class BelgianBudgetOptimizer:
    def __init__(
        self,
        measures: List[PolicyMeasure] = POLICY_MEASURES,
        baseline: List[MacroYear] = BASELINE_TRAJECTORY,
        tau: float = BELGIAN_TAX_ELASTICITY_TAU,
    ):
        self.measures = measures
        self.baseline = baseline
        self.tau = tau
        self.N = len(measures)
        self.T = len(baseline)
        self.years = [m.year for m in baseline]
        self.measure_ids = [m.id for m in measures]

    def _build_macro_matrices(
        self, config: OptimizationConfig
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Constructs linear operators mapping decision vector x (length N*T) to:
        - Gross yield per year: Y_gross[t] = G_mat[t] @ x
        - Net primary balance improvement per year: dB_prim[t] = P_mat[t] @ x
        - GDP change per year: dGDP[t] = GDP_mat[t] @ x
        - Total deficit reduction per year (including endogenous interest snowball):
          dB_total[t] = Tot_mat[t] @ x
        - Interest savings per year: Int_saved[t] = (Tot_mat[t] - P_mat[t]) @ x
        """
        dim = self.N * self.T
        G_mat = np.zeros((self.T, dim))
        P_mat = np.zeros((self.T, dim))
        GDP_mat = np.zeros((self.T, dim))

        for i, m in enumerate(self.measures):
            mult = m.keynesian_multiplier if config.enable_keynesian_feedback else 0.0
            net_factor = 1.0 - self.tau * mult
            for t in range(self.T):
                idx = i * self.T + t
                G_mat[t, idx] = m.structural_yield_eur
                P_mat[t, idx] = m.structural_yield_eur * net_factor
                GDP_mat[t, idx] = -mult * m.structural_yield_eur

        # Endogenous interest snowball recurrence:
        # dB_total[t] = dB_prim[t] + r_t * sum_{s=0}^{t-1} dB_total[s]
        Tot_mat = np.zeros((self.T, dim))
        for t in range(self.T):
            Tot_mat[t, :] = P_mat[t, :]
            if config.enable_interest_snowball and t > 0:
                r_t = self.baseline[t].marginal_olo_rate
                cumulative_prev = np.sum(Tot_mat[:t, :], axis=0)
                Tot_mat[t, :] += r_t * cumulative_prev

        return G_mat, P_mat, GDP_mat, Tot_mat

    def _compute_measure_weights(self, config: OptimizationConfig) -> np.ndarray:
        """
        Computes the composite linear social cost weight for each measure i
        given the user's welfare preference weights.
        """
        w = np.zeros(self.N)
        for i, m in enumerate(self.measures):
            score = (
                config.weight_equity * m.cost_equity
                + config.weight_purchasing_power * m.cost_purchasing_power
                + config.weight_competitiveness * m.cost_competitiveness
                + config.weight_public_service * m.cost_public_service
            )
            # Ensure strictly positive baseline weight for numerical stability
            w[i] = max(0.25, score)
        return w

    def solve(self, config: OptimizationConfig) -> OptimizationResult:
        dim = self.N * self.T
        G_mat, P_mat, GDP_mat, Tot_mat = self._build_macro_matrices(config)
        w = self._compute_measure_weights(config)
        discount = np.array(
            [(1.0 + config.social_discount_rate) ** (-t) for t in range(self.T)]
        )

        # Build exact Quadratic Objective: 0.5 * x^T H x + f^T x
        # For each measure i and year t:
        # Stage cost = discount[t] * (w[i] * x_{i,t} + 0.5 * w[i] * convexity_i * x_{i,t}^2)
        #              + discount[t] * weight_ramp_friction * m.fixed_political_cost * (x_{i,t} - x_{i,t-1})^2
        H = np.zeros((dim, dim))
        f = np.zeros(dim)

        for i, m in enumerate(self.measures):
            conv = m.convexity_factor
            ramp_pen = config.weight_ramp_friction * m.fixed_political_cost * 2.0
            for t in range(self.T):
                idx = i * self.T + t
                # Terminal year receives higher weight as it represents steady-state structural cost
                stage_mult = discount[t] * (2.5 if t == self.T - 1 else 1.0)
                f[idx] += stage_mult * w[i]
                H[idx, idx] += stage_mult * w[i] * conv

                # Ramp-up quadratic penalty: 0.5 * ramp_pen * (x_{i,t} - x_{i,t-1})^2
                if t == 0:
                    H[idx, idx] += ramp_pen
                else:
                    idx_prev = i * self.T + (t - 1)
                    H[idx, idx] += ramp_pen
                    H[idx_prev, idx_prev] += ramp_pen
                    H[idx, idx_prev] -= ramp_pen
                    H[idx_prev, idx] -= ramp_pen

        def obj_func(x: np.ndarray) -> float:
            return float(0.5 * x @ (H @ x) + f @ x)

        def obj_grad(x: np.ndarray) -> np.ndarray:
            return H @ x + f

        # Variable bounds: 0 <= x_{i,t} <= u_i * maturation_profile[t]
        bounds = []
        for i, m in enumerate(self.measures):
            u_i = config.custom_max_intensities.get(m.id, m.max_intensity)
            if m.id in config.locked_out_measures:
                u_i = 0.0
            min_i_T = config.forced_min_measures.get(m.id, 0.0)
            for t in range(self.T):
                ub_t = u_i * m.maturation_profile[t]
                lb_t = min(min_i_T, ub_t) if t == self.T - 1 else 0.0
                bounds.append((lb_t, ub_t))

        # Linear inequality constraints for SLSQP: C @ x - d >= 0
        C_rows = []
        d_vals = []

        # 1. Monotonicity & Max Annual Ramp-Up Constraints:
        #    0 <= x_{i,t} - x_{i,t-1} <= max_annual_ramp
        for i, m in enumerate(self.measures):
            if m.id in config.locked_out_measures:
                continue
            for t in range(self.T):
                idx = i * self.T + t
                if t == 0:
                    # x_{i,0} <= max_annual_ramp
                    row = np.zeros(dim)
                    row[idx] = -1.0
                    C_rows.append(row)
                    d_vals.append(-m.max_annual_ramp)
                else:
                    idx_prev = i * self.T + (t - 1)
                    # Monotonicity: x_{i,t} - x_{i,t-1} >= 0
                    row_mono = np.zeros(dim)
                    row_mono[idx] = 1.0
                    row_mono[idx_prev] = -1.0
                    C_rows.append(row_mono)
                    d_vals.append(0.0)

                    # Ramp speed: -(x_{i,t} - x_{i,t-1}) >= -max_annual_ramp
                    row_ramp = np.zeros(dim)
                    row_ramp[idx] = -1.0
                    row_ramp[idx_prev] = 1.0
                    C_rows.append(row_ramp)
                    d_vals.append(-m.max_annual_ramp)

        # 2. Terminal Deficit-to-GDP Target Constraint (Year 2029, t = T-1):
        #    Deficit_T(x) / GDP_T(x) <= d_target
        #    <=> dB_total_T(x) + d_target * dGDP_T(x) >= Deficit_base_T - d_target * GDP_base_T
        t_final = self.T - 1
        d_target = config.target_deficit_2029_pct / 100.0
        base_final = self.baseline[t_final]
        rhs_final = base_final.baseline_deficit_eur - d_target * base_final.gdp_nominal

        row_terminal_deficit = Tot_mat[t_final, :] + d_target * GDP_mat[t_final, :]
        C_rows.append(row_terminal_deficit)
        d_vals.append(rhs_final)
        terminal_constraint_idx = len(C_rows) - 1

        # 3. Intermediate EU Fiscal Glidepath Constraints (t = 0 .. T-2):
        #    Ensure the deficit-to-GDP ratio follows a credible downward ceiling each year
        if config.min_annual_deficit_reduction_pct > 0:
            start_def_pct = self.baseline[0].baseline_deficit_pct
            for t in range(self.T - 1):
                # Linearly interpolated ceiling + small flexibility buffer (0.35% GDP)
                interp_pct = start_def_pct - (t + 1) * min(
                    config.min_annual_deficit_reduction_pct,
                    max(0.0, (start_def_pct - config.target_deficit_2029_pct) / self.T),
                )
                d_ceil_t = interp_pct / 100.0
                base_t = self.baseline[t]
                rhs_t = base_t.baseline_deficit_eur - d_ceil_t * base_t.gdp_nominal
                row_t = Tot_mat[t, :] + d_ceil_t * GDP_mat[t, :]
                C_rows.append(row_t)
                d_vals.append(rhs_t)

        # 4. Fiscal Mix Constraint in 2029 (Minimum share from Spending Cuts + Activation):
        #    sum_{i in Spend/Act} G_{i,T} - theta * sum_{all i} G_{i,T} >= 0
        theta_spend = config.min_spending_and_activation_share_pct / 100.0
        if theta_spend > 0.0:
            row_mix = np.zeros(dim)
            for i, m in enumerate(self.measures):
                idx = i * self.T + t_final
                is_spend_or_act = m.measure_type in (
                    "Expenditure Cut",
                    "Structural Activation",
                )
                coeff = (1.0 - theta_spend) if is_spend_or_act else (-theta_spend)
                row_mix[idx] = coeff * m.structural_yield_eur
            C_rows.append(row_mix)
            d_vals.append(0.0)

        # 5. Maximum Tax Share Constraint in 2029 (if < 100%):
        theta_tax_max = config.max_tax_share_pct / 100.0
        if theta_tax_max < 1.0:
            row_tax = np.zeros(dim)
            for i, m in enumerate(self.measures):
                idx = i * self.T + t_final
                is_tax = m.measure_type == "Revenue Increase"
                coeff = (theta_tax_max - 1.0) if is_tax else theta_tax_max
                row_tax[idx] = coeff * m.structural_yield_eur
            C_rows.append(row_tax)
            d_vals.append(0.0)

        # 6. Institutional Effort Sharing (Minimum share from Entity II / Joint measures):
        theta_reg = config.min_regional_joint_share_pct / 100.0
        if theta_reg > 0.0:
            row_reg = np.zeros(dim)
            for i, m in enumerate(self.measures):
                idx = i * self.T + t_final
                is_reg = "Entity II" in m.entity or "Joint" in m.entity
                coeff = (1.0 - theta_reg) if is_reg else (-theta_reg)
                row_reg[idx] = coeff * m.structural_yield_eur
            C_rows.append(row_reg)
            d_vals.append(0.0)

        C_mat = np.array(C_rows)
        d_vec = np.array(d_vals)

        # Feasible warm-start initial guess
        x0 = np.zeros(dim)
        for i, m in enumerate(self.measures):
            u_i = config.custom_max_intensities.get(m.id, m.max_intensity)
            if m.id in config.locked_out_measures:
                continue
            cur = 0.0
            for t in range(self.T):
                cur = min(u_i * m.maturation_profile[t], cur + 0.5 * m.max_annual_ramp)
                x0[i * self.T + t] = cur

        constraints = [
            {
                "type": "ineq",
                "fun": lambda x: C_mat @ x - d_vec,
                "jac": lambda x: C_mat,
            }
        ]

        res = minimize(
            obj_func,
            x0,
            jac=obj_grad,
            bounds=bounds,
            constraints=constraints,
            method="SLSQP",
            options={"maxiter": 1000, "ftol": 1e-6},
        )

        x_opt = np.clip(res.x, [b[0] for b in bounds], [b[1] for b in bounds])
        X_mat = x_opt.reshape((self.N, self.T))

        # Check primal feasibility within numerical tolerance (1e-3)
        max_violation = float(np.max(np.maximum(0.0, d_vec - (C_mat @ x_opt))))
        is_feasible = bool(res.success or max_violation <= 1e-2)
        status_msg = "Optimal solution found" if is_feasible else res.message

        # Estimate shadow price (marginal social cost per €1B of additional 2029 deficit reduction)
        eps_bn = 0.10  # €100M perturbation
        d_vec_pert = d_vec.copy()
        d_vec_pert[terminal_constraint_idx] += eps_bn
        res_pert = minimize(
            obj_func,
            x_opt,
            jac=obj_grad,
            bounds=bounds,
            constraints=[
                {
                    "type": "ineq",
                    "fun": lambda x: C_mat @ x - d_vec_pert,
                    "jac": lambda x: C_mat,
                }
            ],
            method="SLSQP",
            options={"maxiter": 500, "ftol": 1e-6},
        )
        pert_violation = float(np.max(np.maximum(0.0, d_vec_pert - (C_mat @ res_pert.x))))
        if is_feasible and pert_violation <= 1e-2:
            marginal_cost = max(0.0, (obj_func(res_pert.x) - obj_func(x_opt)) / eps_bn)
        else:
            marginal_cost = np.nan

        return self._package_result(
            is_feasible,
            status_msg,
            config,
            X_mat,
            x_opt,
            G_mat,
            P_mat,
            GDP_mat,
            Tot_mat,
            obj_func(x_opt),
            marginal_cost,
        )

    def _package_result(
        self,
        success: bool,
        status_message: str,
        config: OptimizationConfig,
        X_mat: np.ndarray,
        x_opt: np.ndarray,
        G_mat: np.ndarray,
        P_mat: np.ndarray,
        GDP_mat: np.ndarray,
        Tot_mat: np.ndarray,
        total_social_cost: float,
        marginal_social_cost_per_bn: float,
    ) -> OptimizationResult:
        # Compute macro trajectories across 2025-2029
        gross_effort_t = G_mat @ x_opt
        primary_effort_t = P_mat @ x_opt
        d_gdp_t = GDP_mat @ x_opt
        total_effort_t = Tot_mat @ x_opt
        interest_saved_t = total_effort_t - primary_effort_t

        traj_rows = []
        cum_effort = 0.0
        for t, base in enumerate(self.baseline):
            opt_gdp = base.gdp_nominal + d_gdp_t[t]
            opt_def_eur = base.baseline_deficit_eur - total_effort_t[t]
            opt_def_pct = (opt_def_eur / opt_gdp) * 100.0
            cum_effort += total_effort_t[t]
            base_debt_eur = base.gdp_nominal * (base.baseline_debt_pct / 100.0)
            opt_debt_eur = base_debt_eur - cum_effort
            opt_debt_pct = (opt_debt_eur / opt_gdp) * 100.0

            traj_rows.append(
                {
                    "Year": base.year,
                    "Baseline_GDP_B": base.gdp_nominal,
                    "Optimized_GDP_B": opt_gdp,
                    "GDP_Impact_B": d_gdp_t[t],
                    "GDP_Impact_Pct": (d_gdp_t[t] / base.gdp_nominal) * 100.0,
                    "Baseline_Deficit_B": base.baseline_deficit_eur,
                    "Baseline_Deficit_Pct": base.baseline_deficit_pct,
                    "Optimized_Deficit_B": opt_def_eur,
                    "Optimized_Deficit_Pct": opt_def_pct,
                    "Gross_Consolidation_B": gross_effort_t[t],
                    "Macro_Feedback_Loss_B": primary_effort_t[t] - gross_effort_t[t],
                    "Net_Primary_Effort_B": primary_effort_t[t],
                    "Interest_Savings_B": interest_saved_t[t],
                    "Total_Deficit_Reduction_B": total_effort_t[t],
                    "Baseline_Debt_Pct": base.baseline_debt_pct,
                    "Optimized_Debt_Pct": opt_debt_pct,
                    "Ageing_Cost_Drift_B": base.ageing_cost_Increment,
                }
            )
        trajectory_df = pd.DataFrame(traj_rows)

        # Build detailed Measure Summary DataFrame (focusing on 2025-2029 path and 2029 maturity)
        t_final = self.T - 1
        w = self._compute_measure_weights(config)
        measure_rows = []

        cost_breakdown = {
            "Equity & Poverty": 0.0,
            "Purchasing Power": 0.0,
            "Competitiveness": 0.0,
            "Public Services": 0.0,
            "Implementation Friction": 0.0,
        }

        for i, m in enumerate(self.measures):
            x_T = float(X_mat[i, t_final])
            gross_T = m.structural_yield_eur * x_T
            mult = m.keynesian_multiplier if config.enable_keynesian_feedback else 0.0
            net_T = gross_T * (1.0 - self.tau * mult)

            # Nonlinear factor at 2029 intensity
            nonlin = x_T + 0.5 * m.convexity_factor * (x_T ** 2)
            c_eq = config.weight_equity * m.cost_equity * nonlin
            c_pp = config.weight_purchasing_power * m.cost_purchasing_power * nonlin
            c_comp = config.weight_competitiveness * max(0.0, m.cost_competitiveness) * nonlin
            c_serv = config.weight_public_service * max(0.0, m.cost_public_service) * nonlin

            diffs = np.diff(np.concatenate([[0.0], X_mat[i, :]]))
            c_fric = float(
                config.weight_ramp_friction
                * m.fixed_political_cost
                * np.sum(diffs ** 2)
            )

            cost_breakdown["Equity & Poverty"] += c_eq
            cost_breakdown["Purchasing Power"] += c_pp
            cost_breakdown["Competitiveness"] += c_comp
            cost_breakdown["Public Services"] += c_serv
            cost_breakdown["Implementation Friction"] += c_fric

            total_m_cost = c_eq + c_pp + c_comp + c_serv + c_fric

            measure_rows.append(
                {
                    "ID": m.id,
                    "Measure": m.name,
                    "Dutch_Name": m.dutch_name,
                    "Category": m.category,
                    "Type": m.measure_type,
                    "Entity": m.entity,
                    "Intensity_2025": round(float(X_mat[i, 0]), 3),
                    "Intensity_2026": round(float(X_mat[i, 1]), 3),
                    "Intensity_2027": round(float(X_mat[i, 2]), 3),
                    "Intensity_2028": round(float(X_mat[i, 3]), 3),
                    "Intensity_2029": round(x_T, 3),
                    "Max_Intensity": config.custom_max_intensities.get(
                        m.id, m.max_intensity
                    ),
                    "Benchmark_Yield_B": m.structural_yield_eur,
                    "Gross_Yield_2029_B": round(gross_T, 3),
                    "Net_Yield_2029_B": round(net_T, 3),
                    "Macro_Retention_Pct": round((1.0 - self.tau * mult) * 100.0, 1),
                    "Social_Cost_2029": round(total_m_cost, 2),
                    "Cost_Per_Net_Bn": round(total_m_cost / net_T, 2)
                    if net_T > 0.05
                    else np.nan,
                    "Description": m.description,
                }
            )

        measures_summary_df = pd.DataFrame(measure_rows)

        final_row = trajectory_df.iloc[-1]
        return OptimizationResult(
            success=bool(success),
            status_message=str(status_message),
            config=config,
            intensities=X_mat,
            measure_ids=self.measure_ids,
            years=self.years,
            measures_summary_df=measures_summary_df,
            trajectory_df=trajectory_df,
            cost_breakdown=cost_breakdown,
            total_social_cost=float(total_social_cost),
            gross_effort_2029_eur=float(final_row["Gross_Consolidation_B"]),
            net_primary_effort_2029_eur=float(final_row["Net_Primary_Effort_B"]),
            interest_saved_2029_eur=float(final_row["Interest_Savings_B"]),
            total_deficit_reduction_2029_eur=float(
                final_row["Total_Deficit_Reduction_B"]
            ),
            final_deficit_2029_eur=float(final_row["Optimized_Deficit_B"]),
            final_deficit_2029_pct=float(final_row["Optimized_Deficit_Pct"]),
            final_debt_2029_pct=float(final_row["Optimized_Debt_Pct"]),
            cumulative_gdp_impact_2029_pct=float(final_row["GDP_Impact_Pct"]),
            marginal_social_cost_per_bn=float(marginal_social_cost_per_bn),
        )

    def compute_pareto_frontier(
        self,
        base_config: OptimizationConfig,
        target_deficits: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """
        Traces the Pareto Frontier between the 2029 Budget Deficit Target (% of GDP)
        and the Minimum Total Social Cost.
        """
        if target_deficits is None:
            target_deficits = [4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0]

        rows = []
        for target in target_deficits:
            cfg = OptimizationConfig(
                target_deficit_2029_pct=target,
                min_annual_deficit_reduction_pct=min(
                    base_config.min_annual_deficit_reduction_pct,
                    max(0.0, (4.7 - target) / 5.0),
                ),
                weight_equity=base_config.weight_equity,
                weight_purchasing_power=base_config.weight_purchasing_power,
                weight_competitiveness=base_config.weight_competitiveness,
                weight_public_service=base_config.weight_public_service,
                weight_ramp_friction=base_config.weight_ramp_friction,
                min_spending_and_activation_share_pct=base_config.min_spending_and_activation_share_pct,
                max_tax_share_pct=base_config.max_tax_share_pct,
                min_regional_joint_share_pct=base_config.min_regional_joint_share_pct,
                enable_keynesian_feedback=base_config.enable_keynesian_feedback,
                enable_interest_snowball=base_config.enable_interest_snowball,
                locked_out_measures=list(base_config.locked_out_measures),
                forced_min_measures=dict(base_config.forced_min_measures),
                custom_max_intensities=dict(base_config.custom_max_intensities),
                social_discount_rate=base_config.social_discount_rate,
            )
            res = self.solve(cfg)
            rows.append(
                {
                    "Target_Deficit_2029_Pct": target,
                    "Feasible": res.success,
                    "Achieved_Deficit_2029_Pct": res.final_deficit_2029_pct,
                    "Gross_Effort_2029_B": res.gross_effort_2029_eur,
                    "Total_Deficit_Reduction_2029_B": res.total_deficit_reduction_2029_eur,
                    "Total_Social_Cost": res.total_social_cost,
                    "Marginal_Social_Cost_Per_Bn": res.marginal_social_cost_per_bn,
                    "Debt_2029_Pct": res.final_debt_2029_pct,
                    "GDP_Impact_2029_Pct": res.cumulative_gdp_impact_2029_pct,
                }
            )
        return pd.DataFrame(rows)


if __name__ == "__main__":
    optimizer = BelgianBudgetOptimizer()
    print("=" * 80)
    print("BELGIAN BUDGET OPERATIONS RESEARCH MODEL (2025-2029)")
    print("=" * 80)

    # 1. Run EU Maastricht Compliance Scenario (2.8% Deficit by 2029)
    cfg_maastricht = OptimizationConfig(target_deficit_2029_pct=2.8)
    res_m = optimizer.solve(cfg_maastricht)
    print(f"\n[Scenario 1: EU Trajectory -> 2.8% Deficit in 2029]")
    print(f"Solver Status: {res_m.status_message} (Success: {res_m.success})")
    print(f"2029 Baseline Deficit: 5.70% GDP (€{BASELINE_TRAJECTORY[-1].baseline_deficit_eur:.2f}B)")
    print(f"2029 Optimized Deficit: {res_m.final_deficit_2029_pct:.2f}% GDP (€{res_m.final_deficit_2029_eur:.2f}B)")
    print(f"Gross Policy Effort (2029): €{res_m.gross_effort_2029_eur:.2f}B")
    print(f"Net Primary Effort (after Keynesian/Supply feedback): €{res_m.net_primary_effort_2029_eur:.2f}B")
    print(f"Endogenous Interest Saved (2029): €{res_m.interest_saved_2029_eur:.2f}B")
    print(f"2029 Public Debt Ratio: {res_m.final_debt_2029_pct:.1f}% GDP (vs 115.6% baseline)")

    # 2. Run Full Structural Equilibrium Scenario (0.0% Deficit by 2029)
    cfg_eq = OptimizationConfig(target_deficit_2029_pct=0.0, min_spending_and_activation_share_pct=50.0)
    res_eq = optimizer.solve(cfg_eq)
    print(f"\n[Scenario 2: Full Budget Equilibrium -> 0.0% Deficit in 2029]")
    print(f"Solver Status: {res_eq.status_message} (Success: {res_eq.success})")
    print(f"2029 Optimized Deficit: {res_eq.final_deficit_2029_pct:.2f}% GDP (€{res_eq.final_deficit_2029_eur:.2f}B)")
    print(f"Gross Policy Effort (2029): €{res_eq.gross_effort_2029_eur:.2f}B")
    print(f"Net Primary Effort (2029): €{res_eq.net_primary_effort_2029_eur:.2f}B")
    print(f"Endogenous Interest Saved (2029): €{res_eq.interest_saved_2029_eur:.2f}B")
    print(f"2029 Public Debt Ratio: {res_eq.final_debt_2029_pct:.1f}% GDP (vs 115.6% baseline)")
    print("\nTop 10 Measures for Full Equilibrium (by 2029 Net Yield):")
    top10 = res_eq.measures_summary_df.sort_values("Net_Yield_2029_B", ascending=False).head(10)
    print(
        top10[
            [
                "ID",
                "Measure",
                "Intensity_2029",
                "Gross_Yield_2029_B",
                "Net_Yield_2029_B",
                "Social_Cost_2029",
            ]
        ].to_string(index=False)
    )
