# Water-Pixel Dilution Bias (WPDB)
### A Systematic Measurement Error in Riverine Spatial Feature Engineering

[![IEEE CSDE 2026](https://img.shields.io/badge/IEEE%20CSDE-2026%20Accepted-blue.svg)](https://www.ieee-csde.org/)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-orange.svg)](https://earthengine.google.com/)

This repository provides the official implementation, datasets, pre-computed spatial features, and visualization code for the research paper:

> **Md Abu Sayem Sarker and Syed Nazmus Sakib**,  
> *"Water Pixel Dilution Bias: A Systematic Measurement Error in Riverine Spatial Feature Engineering,"*  
> **11th IEEE Asia-Pacific Conference on Computer Science and Data Engineering (IEEE CSDE 2026)**, Cox's Bazar, Bangladesh, 2026.

---

## 🎖️ Conference Acceptance & Evaluation Notice

> [!IMPORTANT]
> **Notice for SPARRSO Evaluation Committee:**  
> This repository has been prepared and made accessible for the technical evaluation and viva assessment by the **Bangladesh Space Research and Remote Sensing Organization (SPARRSO)**.  
> 
> * **Conference Status:** This research has been formally accepted for presentation and inclusion in the conference proceedings of **IEEE CSDE 2026** (Paper ID: `ieee-csde_3561`), scheduled for **1–3 November 2026**.
> * **Copyright Notice:** In accordance with IEEE policy, the conference manuscript and proceedings are subject to IEEE copyright (© 2026 IEEE). The accompanying source code, spatial pipelines, and reproducible feature engineering algorithms are authored by the researchers and released under the [MIT License](LICENSE) for academic review, recruitment evaluation, and research verification.

<p align="center">
  <img src="confirmation.png" alt="IEEE CSDE 2026 Acceptance Confirmation" width="850"/>
  <br>
  <em>Official IEEE CSDE 2026 Acceptance Notification (Paper ID: ieee-csde_3561)</em>
</p>

---

## 📌 Abstract & Problem Formulation

In riverine environmental modeling and land use attribution studies, researchers standardly construct circular Euclidean buffers around monitoring stations to extract land cover proportions. Conventional GIS raster extraction tools normalize class areas by total polygon pixel counts ($A_{\text{total}}$), implicitly retaining open water surface pixels ($A_{\text{water}}$) in the denominator.

Because open water represents an unbuildable aquatic channel rather than available terrestrial land, its inclusion systematically deflates terrestrial land cover estimates whenever a river channel intersects the extraction geometry. This systematic distortion is formalized as **Water-Pixel Dilution Bias (WPDB)**:

$$\Delta f_{\text{built}} = f_{\text{built, naive}} - f_{\text{built, non-water}}$$

$$\Delta f_{\text{built}} = - f_{\text{water}} \cdot f_{\text{built, non-water}}$$

where:
- $f_{\text{water}} \equiv \frac{A_{\text{water}}}{A_{\text{total}}}$ is the open water surface fraction inside the extraction polygon.
- $f_{\text{built, non-water}} \equiv \frac{A_{\text{built}}}{A_{\text{total}} - A_{\text{water}}}$ is the true terrestrial built-up density.

### Empirical Validation
Across 11 monitoring stations on two major urban river networks in Dhaka, Bangladesh:
- **Buriganga River ($n=7$)**: Mean water fraction $56.30\%$; mean dilution bias $-45.88\text{ pp}$ ($\sigma = 10.32\text{ pp}$).
- **Shitalakhya River ($n=4$)**: Mean water fraction $58.80\%$; mean dilution bias $-48.78\text{ pp}$ ($\sigma = 5.85\text{ pp}$).
- **Multi-River Combined ($n=11$)**: Mean distortion of $-46.93\text{ pp}$ (reaching up to $-56.34\text{ pp}$ at Satmasjid Road).
- **Exact Closed-Form Identity**: Verification against observable raster quantities yields numerical agreement within floating-point precision ($|\epsilon| \le 1.11 \times 10^{-14}$), confirming that WPDB is a deterministic geometric identity rather than an empirical artifact.

---

## 📂 Repository Architecture

```text
wpdb_riverine_spatial_feature_engineering/
├── README.md                           # Documentation, mathematical formulation & setup
├── requirements.txt                    # Python environment dependencies
├── LICENSE                             # MIT License
├── .gitignore                          # Standard build and cache exclusions
├── run_experiments.py                  # Master CLI runner for reproducing paper results
│
├── data/
│   ├── raw/
│   │   ├── shitalakhya_stations.csv    # Monitoring station coordinates (DoE Bangladesh)
│   │   └── shitalakhya_monitoring_report_raw.md # Raw multi-year monitoring reports
│   └── processed/
│       ├── buriganga_water_quality.csv # Clean long-format hydrochemical panel (2021-2023)
│       └── shitalakhya_water_quality.csv # Clean long-format hydrochemical panel (2021-2023)
│
├── pipelines/
│   ├── buriganga/                      # Core Buriganga River Pipeline (n=7 stations)
│   │   ├── 01_preprocess_water_quality.py
│   │   ├── 02_extract_centerline.py
│   │   ├── 03_extract_dynamic_world_cover.py
│   │   ├── 04_bonferroni_hypothesis_test.py
│   │   ├── 05_buffer_sensitivity_comparison.py
│   │   └── run_buriganga.py
│   │
│   └── shitalakhya/                    # Multi-River Validation Pipeline (n=4 stations)
│       ├── 01_preprocess_water_quality.py
│       ├── 02_extract_centerline.py
│       ├── 03_extract_dynamic_world_cover.py
│       ├── 04_quantify_dilution_bias.py
│       └── run_shitalakhya.py
│
├── visualization/                      # Publication Figure Generators (IEEE Standards)
│   ├── plot_multi_river_scatter.py     # Generates Figure 3 (Empirical Scaling vs Identity)
│   ├── plot_gee_buffer_overlay.py      # Generates Figure 4 (Satellite overlay at Hazaribagh)
│   └── plot_study_area_maps.py         # Generates study area overview maps
│
├── outputs/                            # Pre-computed Verified Analytical Outputs
│   ├── buriganga/
│   │   ├── centerline.geojson          # 1D automated river centerline (JRC GSW)
│   │   ├── stations_snapped.csv        # Snapped station coordinates and along-channel meters
│   │   ├── land_cover_distance_resolved.csv # 50 x 100m upstream corridor Dynamic World counts
│   │   ├── land_cover_summary.csv      # Built-up fraction summary (Table 1)
│   │   ├── h1_bonferroni_results.csv   # 10-parameter Bonferroni correlation results
│   │   ├── h1_report.txt               # Statistical evaluation narrative
│   │   ├── h2_classification_comparison.csv # Buffer radius cross-tabulation
│   │   └── h2_per_station.csv          # Categorical labels (Buffer vs. Flow Corridor)
│   └── shitalakhya/
│       ├── centerline_shitalakhya.geojson
│       ├── stations_shitalakhya_snapped.csv
│       ├── land_cover_shitalakhya_resolved.csv
│       ├── shitalakhya_bias_summary.csv# Dilution metrics and identity validation (Table 1)
│       └── shitalakhya_hydrochemical_correlations.csv
│
└── figures/                            # High-resolution vector (PDF) and raster (PNG) figures
    ├── fig1_conceptual_comparison.png  # Figure 1: Euclidean Buffer vs. Non-Water Corridor
    ├── fig1_conceptual_comparison.pdf
    ├── fig2_methodology_diagram.png    # Figure 2: End-to-end Methodological Framework
    ├── fig2_methodology_diagram.pdf
    ├── fig3_multi_river_scatter.png    # Figure 3: Multi-River Empirical Scaling vs Identity
    ├── fig3_multi_river_scatter.pdf
    ├── fig4_gee_satellite_overlay.png  # Figure 4: GEE Satellite Overlay at Hazaribagh & Satmasjid
    └── fig4_gee_satellite_overlay.pdf
```

---

## 🔬 Key Methodological Contributions

1. **Analytical Identity Derivation**: Formal proof demonstrating that denominator dilution bias is strictly governed by open water surface fraction ($f_{\text{water}}$) and terrestrial built density ($f_{\text{built, nw}}$).
2. **Automated Centerline Extraction**: JRC Global Surface Water skeletonization graph analysis (`networkx`, `scikit-image`) extracting 1D continuous flowpaths without manual waypoint intervention.
3. **Flow-Aware Upstream Corridor Integration**: Upstream distance-resolved bins ($50 \times 100\,\text{m}$, total $5\,\text{km}$) buffered to $600\,\text{m}$ width, normalizing land cover proportions strictly against non-water land area.
4. **Buffer Sensitivity Quantification**: Direct evidence that standard $200\,\text{m}$ circular buffers misclassify heavily urbanized industrial reaches (e.g., Hazaribagh at $62.10\%$ water misclassified as mixed land use at $26.5\%$ naive built fraction, whereas true non-water density exceeds $88\%$).

---

## ⚙️ Installation & Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/wpdb_riverine_spatial_feature_engineering.git
cd wpdb_riverine_spatial_feature_engineering
```

### 2. Create and Activate a Virtual Environment
```bash
# Using conda
conda create -n wpdb python=3.10 -y
conda activate wpdb

# Or using venv
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows
```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Google Earth Engine Authentication
To execute live satellite reductions from Sentinel-2 Dynamic World and JRC Surface Water, authenticate your GEE credentials:
```bash
earthengine authenticate
```
*Note: All extracted GeoJSON centerlines and distance-resolved land cover tables are already pre-computed in `outputs/` and cached in `cache/` for immediate offline inspection and reproduction.*

---

## 🚀 Execution & Reproducibility Guide

You can reproduce the empirical tables and publication figures using the master runner `run_experiments.py`:

### Reproduce Publication Figures (Offline / Cached)
```bash
python run_experiments.py --figures
```
This generates:
- `figures/fig3_multi_river_scatter.png` & `.pdf` (300 DPI, TrueType font embedded)
- `figures/fig4_gee_satellite_overlay.png` & `.pdf` (300 DPI, TrueType font embedded)

### Run Individual River Pipelines
```bash
# Buriganga River Pipeline (n=7 stations)
python run_experiments.py --river buriganga

# Shitalakhya River Pipeline (n=4 stations)
python run_experiments.py --river shitalakhya
```

### Execute the Full Suite
```bash
python run_experiments.py --all
```

---

## 📊 Summary of Experimental Results (Table I in Paper)

| Monitoring Station | Water Fraction ($f_{\text{water}}$) | Naive Built ($f_{\text{built, naive}}$) | Non-Water Built ($f_{\text{built, nw}}$) | Observed $\Delta f_{\text{built}}$ | Identity Predicted | Residual ($|\epsilon|$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Buriganga River** | | | | | | |
| Mirpur Bridge | $43.01\%$ | $36.03\%$ | $63.22\%$ | $-27.19\%$ | $-27.19\%$ | $0.00\text{ pp}$ |
| Bosila Bridge | $51.89\%$ | $38.74\%$ | $80.52\%$ | $-41.78\%$ | $-41.78\%$ | $0.00\text{ pp}$ |
| Hazaribagh | $62.10\%$ | $33.66\%$ | $88.80\%$ | $-55.14\%$ | $-55.14\%$ | $0.00\text{ pp}$ |
| Satmasjid Road | $63.93\%$ | $31.78\%$ | $88.12\%$ | $-56.34\%$ | $-56.34\%$ | $0.00\text{ pp}$ |
| Chadnighat | $55.54\%$ | $42.81\%$ | $96.29\%$ | $-53.48\%$ | $-53.48\%$ | $0.00\text{ pp}$ |
| Buriganga 1 (BCFB) | $55.73\%$ | $36.44\%$ | $82.31\%$ | $-45.87\%$ | $-45.87\%$ | $0.00\text{ pp}$ |
| Fatullah | $61.91\%$ | $25.45\%$ | $66.81\%$ | $-41.36\%$ | $-41.36\%$ | $0.00\text{ pp}$ |
| **Buriganga Mean ($\mu$)** | **$56.30\%$** | **$34.99\%$** | **$80.87\%$** | **$-45.88\%$** | **$-45.88\%$** | **$0.00\text{ pp}$** |
| **Shitalakhya River** | | | | | | |
| Port Road | $58.47\%$ | $35.27\%$ | $84.93\%$ | $-49.66\%$ | $-49.66\%$ | $0.00\text{ pp}$ |
| Majira Demra Ghat | $56.54\%$ | $41.17\%$ | $94.72\%$ | $-53.56\%$ | $-53.55\%$ | $0.01\text{ pp}$ |
| Murapara (Rupgonj) | $57.45\%$ | $38.18\%$ | $89.74\%$ | $-51.56\%$ | $-51.56\%$ | $0.00\text{ pp}$ |
| Ghorashal | $62.72\%$ | $23.98\%$ | $64.31\%$ | $-40.33\%$ | $-40.34\%$ | $0.01\text{ pp}$ |
| **Shitalakhya Mean ($\mu$)** | **$58.80\%$** | **$34.65\%$** | **$83.43\%$** | **$-48.78\%$** | **$-48.78\%$** | **$0.00\text{ pp}$** |
| **Multi-River Combined ($\mu$)** | **$57.21\%$** | **$34.87\%$** | **$81.80\%$** | **$-46.93\%$** | **$-46.93\%$** | **$0.00\text{ pp}$** |

---

## 📜 Citation

If you use this codebase, methodology, or datasets in your research, please cite our IEEE conference paper:

```bibtex
@inproceedings{sarker2026wpdb,
  author    = {Sarker, Md Abu Sayem and Sakib, Syed Nazmus},
  title     = {Water Pixel Dilution Bias: A Systematic Measurement Error in Riverine Spatial Feature Engineering},
  booktitle = {Proceedings of the 11th IEEE Asia-Pacific Conference on Computer Science and Data Engineering (IEEE CSDE 2026)},
  year      = {2026},
  pages     = {1--6},
  publisher = {IEEE},
  address   = {Cox's Bazar, Bangladesh},
  doi       = {10.1109/CSDE60450.2026.XXXXXXX}
}
```

---

## 👤 Authors & Contact

- **Md Abu Sayem Sarker**  
  Department of Software Engineering  
  Daffodil International University, Dhaka, Bangladesh  
  Email: `sayem2305341279@diu.edu.bd`

- **Syed Nazmus Sakib**  
  Department of Environmental Science and Disaster Management  
  Daffodil International University, Dhaka, Bangladesh  
  Email: `sakib.esdm@diu.edu.bd`

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
