# 🇧🇪 Belgian Budget Equilibrium Optimizer (2025–2029)

An **Operations Research (Convex Quadratic Programming)** model designed to solve Belgium's General Government fiscal consolidation challenge (*"De Begrotingspuzzel" / Supernota*) over the 2025–2029 horizon while **minimizing multi-dimensional social, economic, and distributional costs**.

---

## 🚀 Quick Start

### 1. Run the Interactive Streamlit Dashboard
```powershell
streamlit run app.py
```
This opens an interactive policy optimizer where you can:
- Adjust the **2029 Deficit Target** from `4.5%` down to `3.0%` (EU Maastricht threshold) or `0.0%` (**Full Budget Equilibrium**, closing the ~€40B projected gap).
- Tweak **Social Welfare Weights ($\omega$)** across Equity/Poverty Protection, Middle-Class Purchasing Power, Economic Competitiveness, Public Service Quality, and Union/Implementation Friction.
- Apply **Political Taboos / Vetoes** (e.g., locking out automatic wage indexation reform `M09`, capital gains tax `M11`, or healthcare growth norm cuts `M08`).
- Inspect the **Pareto Efficiency Frontier**, **Snowball OLO Interest Savings**, and the **5-Year Reform Sequencing Heatmap**.

### 2. Run the Command-Line OR Solver
```powershell
python budget_or_model.py
```

---

## 📁 Project Structure

- [`belgian_budget_data.py`](belgian_budget_data.py): Macroeconomic baseline (2025–2029 projections based on the Federal Planning Bureau & High Council of Finance: GDP, unchanged-policy deficit rising from 4.7% to 5.7% of GDP, ageing cost drift, and OLO interest rates) and **21 calibrated policy measures** across 6 domains (Entity I Federal & Social Security + Entity II Regions & Communities).
- [`budget_or_model.py`](budget_or_model.py): The multi-period Convex Quadratic Programming (`BelgianBudgetOptimizer`) engine with Keynesian/labour-supply multipliers, automatic stabilizer feedback ($\tau = 0.48$), endogenous debt-interest snowball recurrence, exact denominator-adjusted deficit constraints, shadow price ($\lambda$) calculation, and Pareto frontier generator.
- [`app.py`](app.py): Interactive Streamlit decision-support dashboard with Plotly visualizations.

