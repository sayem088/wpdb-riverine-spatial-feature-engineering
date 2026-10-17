r"""
Renders Figure 3 for the IEEE CSDE 2026 paper:
Multi-river empirical scaling of Water-Pixel Dilution Bias (WPDB) across 11 monitoring
stations on the Buriganga (n=7) and Shitalakhya (n=4) river networks against the
closed-form analytical identity line: |\Delta f| = f_{water} * \bar{f}_{built, nw}.

Outputs:
  figures/fig3_multi_river_scatter.png (300 DPI)
  figures/fig3_multi_river_scatter.pdf (Vector TrueType embedded)
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# Configure TrueType font embedding for IEEE publication standards
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype']  = 42
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
FIG_DIR    = os.path.join(REPO_ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

PNG_OUT = os.path.join(FIG_DIR, "fig3_multi_river_scatter.png")
PDF_OUT = os.path.join(FIG_DIR, "fig3_multi_river_scatter.pdf")

# Empirical observations from verified extraction data
buriganga_stations = [
    ("Mirpur Bridge",   43.01, 27.19),
    ("Bosila Bridge",   51.89, 41.78),
    ("Hazaribagh",      62.10, 55.14),
    ("Satmasjid Road",  63.93, 56.34),
    ("Chadnighat",      55.54, 53.48),
    ("BCFB",            55.73, 45.87),
    ("Fatullah",        61.91, 41.36),
]

shitalakhya_stations = [
    ("Port Road",          58.47, 49.66),
    ("Majira Demra Ghat",  56.54, 53.56),
    ("Murapara (Rupgonj)", 57.45, 51.56),
    ("Ghorashal",          62.72, 40.33),
]

def main():
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    # Plot Buriganga Network (n=7)
    bx = [s[1] for s in buriganga_stations]
    by = [s[2] for s in buriganga_stations]
    ax.scatter(bx, by, c='#2563EB', marker='o', s=95, zorder=5,
               edgecolors='white', linewidth=0.8, label='Buriganga River ($n=7$)')

    # Plot Shitalakhya Network (n=4)
    sx = [s[1] for s in shitalakhya_stations]
    sy = [s[2] for s in shitalakhya_stations]
    ax.scatter(sx, sy, c='#DC2626', marker='s', s=95, zorder=5,
               edgecolors='white', linewidth=0.8, label='Shitalakhya River ($n=4$)')

    # Station Labels
    for name, x, y in buriganga_stations:
        ax.annotate(name, (x, y), fontsize=7.5, ha='left',
                    xytext=(5, 4), textcoords='offset points', color='#1e40af')

    for name, x, y in shitalakhya_stations:
        ax.annotate(name, (x, y), fontsize=7.5, ha='left',
                    xytext=(5, -8), textcoords='offset points', color='#991b1b')

    # Theoretical Identity Reference Line: |\Delta f| = f_{water} * 0.8180
    x_theory = np.linspace(35, 70, 100)
    y_theory = x_theory * 0.8180
    ax.plot(x_theory, y_theory, 'k--', linewidth=1.2, alpha=0.6,
            label=r'Theoretical Identity: $|\Delta f| = f_{\mathrm{water}} \cdot \bar{f}_{\mathrm{built,nw}}$'
                  '\n' r'($\bar{f}_{\mathrm{built,nw}} = 81.80\%$)')

    # Multi-river mean line
    ax.axhline(y=46.93, color='gray', linestyle=':', linewidth=0.9, alpha=0.7)
    ax.annotate(r'Multi-river mean $|\Delta f| = 46.93\%$',
                xy=(39, 47.3), fontsize=7.5, color='#4b5563', va='bottom')

    # Layout & Styling
    ax.set_xlabel(r'Open Water Surface Fraction $f_{\mathrm{water}}$ (%)', fontsize=11)
    ax.set_ylabel(r'Dilution Bias Magnitude $|\Delta f_{\mathrm{built}}|$ (percentage points)', fontsize=11)
    ax.set_title('Multi-River Empirical Scaling of Water-Pixel Dilution Bias', fontsize=12, fontweight='bold', pad=12)

    ax.set_xlim(38, 68)
    ax.set_ylim(20, 65)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.legend(loc='lower left', fontsize=8.5, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(PNG_OUT, dpi=300, bbox_inches='tight')
    plt.savefig(PDF_OUT, bbox_inches='tight')
    print(f"Figure 3 generated successfully:\n  {PNG_OUT}\n  {PDF_OUT}")

if __name__ == "__main__":
    main()
