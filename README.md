# SugarIQ-
Predictive Performance Optimization for C-Centrifugal Station_
# Sugar IQ: Predictive Performance Optimization for C-Centrifugal Station
### *Maximizing Sugar Recovery and Minimizing Final Molasses Purity via Statistical Analytics.*
Sugar IQ is a data-driven web application designed for raw sugar processing houses. It transforms routine shift laboratory inputs into predictive maintenance actions and prescriptive floor instructions for C-centrifugal stations. 
The ultimate operational objective of this system is to maintain a strict baseline of **37% Overall Final Molasses Purity (FMP)**.

---

## 🔬 The Core Factory Problem

1. **Crystal Dissolution (Over-Washing):** C-massecuite is highly viscous. Operators manually use hot wash water to improve purging efficiency. However, excessive water drops molasses density (toward 80°Bx) and dissolves fine sugar crystals, washing valuable sucrose out into the waste molasses channel.
2. **Maintenance Blindspots:** Replacing filtering screens on a rigid 6-week calendar schedule is inefficient. A screen tear in Week 2 results in weeks of undetected sugar bleeding. Conversely, replacing a perfectly functional screen at Week 6 wastes maintenance resources.
3. **Station Disruption:** When a primary machine (such as **C-BMA 2**) suffers a prolonged breakdown, standard factory baseline calculations distort, masking actual performance drops on the remaining active machinery.

---

## 🛠️ The Sugar IQ Solution Modules

### Module 1: Predictive Analytics Engine
Utilizes historical time-series data (Weeks 1 to 22) to compute linear regression degradation curves per machine. It forecasts the exact timeframe remaining before a working screen breaches the **2.0-unit maximum purity rise threshold**.

### Module 2: Prescriptive Operator Advisor
Cross-references individual machine purity rises against **Molasses Brix Nirs (Target: 80–85°Bx)** to provide real-time diagnostic logic:
* **High Purity Rise + Low Brix (<82°Bx):** Triggers an immediate operator action to taper manual wash water duration.
* **High Purity Rise + Stable Brix (83–85°Bx):** Structurally confirms a mechanical screen tear. Triggers a foreman order for immediate screen replacement.

### Module 3: Station Resilience & Balance
Dynamically recalibrates the analytical data loops to a 3-machine balance when a machine (like C-BMA 2) is flagged as offline, ensuring overall factory target metrics remain unskewed.
