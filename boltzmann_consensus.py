#!/usr/bin/env python3
"""
boltzmann_consensus.py built with Claude

Takes the best-fit Boltzmann sigmoidal parameters (Bottom, Top, T50, Slope)
from N *individually fit* datasets (e.g. one nonlinear regression per cell)
and builds a single "consensus" curve:

    1. mean +/- SEM of each of the 4 parameters across the N fits
    2. a Boltzmann curve evaluated at the mean parameters
    3. a propagated error band around that curve -- built from the
       full 4x4 covariance matrix of the N parameter sets (not just the
       diagonal), pushed through the curve equation via the delta method,
       so parameter correlations (e.g. Slope vs T50) are accounted for. produced one graph with SEM and one with 95%CI.

Equation (matches GraphPad Prism's "Boltzmann sigmoidal" built-in model):
    Y = Bottom + (Top - Bottom) / (1 + exp((T50 - X) / Slope))

Usage
-----
    # with the built-in example data (15 cells from this session)
    python boltzmann_consensus.py

    # with your own fits, from a CSV with columns: Bottom,Top,T50,Slope ; capitalization matters here
    # (an optional first column of any name, e.g. "cell", is fine and ignored unless --id-col is given)
    python boltzmann_consensus.py --input my_fits.csv --output consensus_curve.csv

    # control the X grid used for the output curve
    python boltzmann_consensus.py --xmin 0 --xmax 2.2 --xstep 0.01

Output
------
A CSV with columns: X, Y, SEM, CI95_lo, CI95_hi  -- paste directly into a
new Prism XY table (X column + the Y/CI columns as one "Group" of Y values)
to draw the consensus curve and a shaded error band.

Also prints the mean +/- SEM of Bottom, Top, T50, and Slope to the terminal,
and (if matplotlib is available) saves a quick preview PNG.
"""

import argparse
import csv
import sys

import numpy as np
from scipy.stats import t as tdist

# ----------------------------------------------------------------------
# Example data: the 15 individual per-cell Boltzmann fits from this
# session's PressureImagingPaper.prism file. Replace with your own data
# via --input, or edit EXAMPLE_FITS directly.
# ----------------------------------------------------------------------
EXAMPLE_FITS = [
    {'cell': '6.2mmHg',     'Bottom': 0.848057, 'Top': 0.983611, 'T50': 0.335768, 'Slope': -0.041792},
    {'cell': '18.0.5mmHg',  'Bottom': 0.802482, 'Top': 1.032544, 'T50': 0.101146, 'Slope': -0.002282},
    {'cell': '22.1mmHg',    'Bottom': 0.641379, 'Top': 0.863674, 'T50': 0.158391, 'Slope': -0.058226},
    {'cell': '17c.2mmHg',   'Bottom': 0.887292, 'Top': 1.027006, 'T50': 0.472382, 'Slope': -0.222949},
    {'cell': '15.1mmHg',    'Bottom': 0.825811, 'Top': 0.924682, 'T50': 0.305630, 'Slope': -0.024194},
    {'cell': '12.0.5mmHg',  'Bottom': 0.822440, 'Top': 0.915082, 'T50': 0.238349, 'Slope': -0.006149},
    {'cell': '10rep.1mmHg', 'Bottom': 0.825629, 'Top': 1.032064, 'T50': 0.204168, 'Slope': -0.033062},
    {'cell': '28.1mmHg',    'Bottom': 0.802773, 'Top': 1.113223, 'T50': 0.153851, 'Slope': -0.226849},
    {'cell': '24.1mmHg',    'Bottom': 0.925050, 'Top': 1.038653, 'T50': 0.346907, 'Slope': -0.004182},
    {'cell': '2.1mmHg',     'Bottom': 0.926218, 'Top': 0.988477, 'T50': 0.162837, 'Slope': -0.020189},
    {'cell': '25.1mmHg',    'Bottom': 0.881802, 'Top': 0.993324, 'T50': 0.239310, 'Slope': -0.068665},
    {'cell': '8.0.5mmHg',   'Bottom': 0.870991, 'Top': 1.005766, 'T50': 0.261825, 'Slope': -0.129868},
    {'cell': '3.2mmHg',     'Bottom': 0.672456, 'Top': 1.059007, 'T50': 0.039925, 'Slope': -0.025557},
    {'cell': '10.0.5mmHg',  'Bottom': 0.907978, 'Top': 1.034522, 'T50': 0.200481, 'Slope': -0.007865},
    {'cell': '11.1mmHg',    'Bottom': 0.902178, 'Top': 1.108455, 'T50': -0.000276, 'Slope': -0.035662},
]

PARAM_NAMES = ['Bottom', 'Top', 'T50', 'Slope']


def boltzmann(x, Bottom, Top, T50, Slope):
    """Prism's Boltzmann sigmoidal: Y = Bottom + (Top-Bottom)/(1+exp((T50-X)/Slope))"""
    z = np.clip((T50 - x) / Slope, -500, 500)  # clip avoids overflow warnings; result unaffected
    return Bottom + (Top - Bottom) / (1 + np.exp(z))


def boltzmann_grad(x, params):
    """Gradient of Y wrt [Bottom, Top, T50, Slope] at scalar x, for delta-method error propagation."""
    Bottom, Top, T50, Slope = params
    z = np.clip((T50 - x) / Slope, -500, 500)
    e = np.exp(z)
    denom = 1 + e
    dY_dBottom = 1 - 1 / denom
    dY_dTop = 1 / denom
    dY_dT50 = (Top - Bottom) * (-e / denom**2) * (1.0 / Slope)
    dY_dSlope = (Top - Bottom) * (-e / denom**2) * (-(T50 - x) / Slope**2)
    return np.array([dY_dBottom, dY_dTop, dY_dT50, dY_dSlope])


def load_fits_from_csv(path, id_col=None):
    """Read a CSV with (at least) columns Bottom, Top, T50, Slope (case-sensitive)."""
    fits = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in PARAM_NAMES if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"Input CSV is missing required column(s): {missing}. "
                              f"Found columns: {reader.fieldnames}")
        for row in reader:
            entry = {p: float(row[p]) for p in PARAM_NAMES}
            if id_col and id_col in row:
                entry['cell'] = row[id_col]
            fits.append(entry)
    return fits


def summarize_parameters(fits):
    """Return (mean vector, SEM vector, sample covariance of the mean) as numpy arrays, in PARAM_NAMES order."""
    P = np.array([[f[p] for p in PARAM_NAMES] for f in fits])  # shape (n_fits, 4)
    n = P.shape[0]
    if n < 2:
        raise ValueError("Need at least 2 individual fits to compute SEM / covariance.")
    mean = P.mean(axis=0)
    cov_sample = np.cov(P, rowvar=False, ddof=1)      # 4x4 covariance across fits
    sem = np.sqrt(np.diag(cov_sample) / n)
    cov_of_mean = cov_sample / n                       # covariance of the MEAN (for propagation)
    return mean, sem, cov_of_mean, n


def build_consensus_curve(mean_params, cov_of_mean, n_fits, xmin=0.0, xmax=2.2, xstep=0.01):                #change xmin, xmax, xstep according to desired fit during input
    """Evaluate the Boltzmann curve at mean_params, with SEM/CI95 propagated via the delta method."""
    xgrid = np.arange(xmin, xmax + xstep / 2, xstep)
    y = boltzmann(xgrid, *mean_params)
    se = np.empty_like(xgrid)
    for i, xv in enumerate(xgrid):
        g = boltzmann_grad(xv, mean_params)
        se[i] = np.sqrt(g @ cov_of_mean @ g)
    dof = n_fits - 1
    tval95 = tdist.ppf(0.975, dof)
    ci_lo = y - tval95 * se
    ci_hi = y + tval95 * se
    return xgrid, y, se, ci_lo, ci_hi, dof, tval95


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', help='CSV with columns Bottom,Top,T50,Slope (one row per individual fit). '
                                     'If omitted, uses the 15-cell example data built into this script.')
    ap.add_argument('--id-col', default='cell', help='Optional column name to carry through as a label (default: cell)')
    ap.add_argument('--output', default='consensus_curve.csv', help='Output CSV path for the consensus curve')
    ap.add_argument('--xmin', type=float, default=0.0)                                                         
    ap.add_argument('--xmax', type=float, default=2.2)
    ap.add_argument('--xstep', type=float, default=0.01)
    ap.add_argument('--plot', default='SEM_curve.png', help='Optional preview PNG path (set to "" to skip)')    #plots mean +/- SEM
    ap.add_argument('--CIplot', default='CI_curve.png', help='Optional preview PNG path (set to "" to skip)')   #plots mean +/- 95% CI
    args = ap.parse_args()

    fits = load_fits_from_csv(args.input, args.id_col) if args.input else EXAMPLE_FITS
    print(f"Loaded {len(fits)} individual Boltzmann fits"
          f"{' from ' + args.input if args.input else ' (built-in example data)'}.\n")

    mean, sem, cov_of_mean, n = summarize_parameters(fits)
    print("Parameter means +/- SEM (n=%d):" % n)
    for name, m, s in zip(PARAM_NAMES, mean, sem):
        print(f"  {name:8s} = {m:.4f} +/- {s:.4f}")

    corr = cov_of_mean / np.outer(np.sqrt(np.diag(cov_of_mean)), np.sqrt(np.diag(cov_of_mean)))
    print("\nParameter correlation matrix (across individual fits):")
    print("          " + "  ".join(f"{p:>8s}" for p in PARAM_NAMES))
    for i, p in enumerate(PARAM_NAMES):
        print(f"  {p:8s}" + "  ".join(f"{corr[i, j]:8.3f}" for j in range(4)))

    xgrid, y, se, ci_lo, ci_hi, dof, tval95 = build_consensus_curve(
        mean, cov_of_mean, n, args.xmin, args.xmax, args.xstep)

    with open(args.output, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['X', 'Y', 'SEM', 'CI95_lo', 'CI95_hi'])
        for xv, yv, sv, lo, hi in zip(xgrid, y, se, ci_lo, ci_hi):
            w.writerow([f"{xv:.6f}", f"{yv:.6f}", f"{sv:.6f}", f"{lo:.6f}", f"{hi:.6f}"])
    print(f"\nConsensus curve (n={len(xgrid)} points, X {args.xmin}-{args.xmax} step {args.xstep}) "
          f"written to: {args.output}")
    print(f"(95% CI uses t={tval95:.3f} at df={dof})")

    if args.plot:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.fill_between(xgrid, y - se, y + se, color='#c0392b', alpha=0.25, linewidth=0, label='mean ± SEM')
            ax.plot(xgrid, y, color='#c0392b', linewidth=2.2)
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.legend(frameon=False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            plt.savefig(args.plot, dpi=200)
            print(f"Preview plot written to: {args.plot}")
        except ImportError:
            print("(matplotlib not available -- skipped preview plot)")

    if args.CIplot:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.fill_between(xgrid, ci_lo, ci_hi, color='#c0392b', alpha=0.25, linewidth=0, label='mean with 95% CI')
            ax.plot(xgrid, y, color='#c0392b', linewidth=2.2)
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.legend(frameon=False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            plt.savefig(args.CIplot, dpi=200)
            print(f"Preview plot written to: {args.CIplot}")
        except ImportError:
            print("(matplotlib not available -- skipped preview plot)")

if __name__ == '__main__':
    sys.exit(main())