"""Caddie Desk branded matplotlib defaults."""
import matplotlib as mpl

INK = "#363334"
PAPER = "#f9f8f3"
INK_MUTE = "#8b8587"
INK_LINE = "#cfc9cb"

def apply():
    mpl.rcParams.update({
        "font.family": "Fraunces, serif",
        "font.size": 11,
        "axes.facecolor": PAPER,
        "figure.facecolor": PAPER,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "xtick.color": INK_MUTE,
        "ytick.color": INK_MUTE,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": INK_LINE,
        "grid.linewidth": 0.5,
    })