import json
from pathlib import Path
import numpy as np
from scipy.interpolate import interp1d

ROOT = Path.cwd()
while ROOT.name != "caddiedesk":
    ROOT = ROOT.parent

# Broadie's published anchor points
# Source: Broadie, "Every Shot Counts" (2014), PGA Tour data 2004-2012
broadie_data = {
    "tee": [
        (100, 2.92), (200, 3.12), (240, 3.25), (300, 3.71),
        (400, 3.99), (540, 4.65),
    ],
    "fairway": [
        (20, 2.40), (100, 2.80), (200, 3.19), (240, 3.45),
        (300, 3.78), (400, 4.11), (540, 4.78),
    ],
    "rough": [
        (20, 2.59), (100, 3.02), (200, 3.42), (240, 3.64),
        (300, 3.90), (400, 4.30), (540, 4.97),
    ],
    "sand": [
        (20, 2.53), (100, 3.23), (200, 3.55), (240, 3.84),
        (300, 4.04), (400, 4.69),
    ],
    "recovery": [
        (100, 3.80), (200, 3.87), (240, 3.97), (300, 4.20),
        (400, 4.75), (540, 5.42),
    ],
}

# Putting (in feet)
putting_data = [
    (3, 1.04), (4, 1.13), (5, 1.23), (6, 1.34), (7, 1.42),
    (8, 1.50), (9, 1.56), (10, 1.61), (30, 1.98), (50, 2.14), (90, 2.40),
]


def build_smooth_curve(anchors, min_dist=None, max_dist=None, n_points=80):
    """Interpolate smooth curve through anchor points using cubic spline."""
    xs = np.array([p[0] for p in anchors])
    ys = np.array([p[1] for p in anchors])
    
    if min_dist is None:
        min_dist = xs.min()
    if max_dist is None:
        max_dist = xs.max()
    
    f = interp1d(xs, ys, kind='cubic')
    smooth_x = np.linspace(min_dist, max_dist, n_points)
    smooth_y = f(smooth_x)
    
    return [
        {"distance": round(float(x), 1), "expected_strokes": round(float(y), 3)}
        for x, y in zip(smooth_x, smooth_y)
    ]


# Build all lie curves
data = {
    "tee": build_smooth_curve(broadie_data["tee"]),
    "fairway": build_smooth_curve(broadie_data["fairway"]),
    "rough": build_smooth_curve(broadie_data["rough"]),
    "sand": build_smooth_curve(broadie_data["sand"], max_dist=400),  # sand stops at 400
    "recovery": build_smooth_curve(broadie_data["recovery"]),
    
    # Putting (feet, not yards)
    "putting": build_smooth_curve(putting_data, n_points=40),
    
    # Worked example
    "annotations": [
        {
            "distance": 165,
            "expected_strokes": 3.02,
            "label": "165 yds from fairway",
            "lie": "fairway"
        }
    ],
    
    # Original anchor points for the chart (so they can be shown as dots)
    # Original anchor points for the chart (so they can be shown as dots)
    "anchors": {
        **{
            lie: [{"distance": p[0], "expected_strokes": p[1]} for p in points]
            for lie, points in broadie_data.items()
        },
        "putting": [{"distance": p[0], "expected_strokes": p[1]} for p in putting_data]
    },
    
    "source": "Broadie, Every Shot Counts (2014), PGA Tour data 2004-2012"
}

OUTPUT_PATH = ROOT / "posts" / "data" / "expected-strokes.json"
OUTPUT_PATH.write_text(json.dumps(data, indent=2))

print(f"Saved real Broadie data to {OUTPUT_PATH}")
print(f"\nSample values:")
print(f"  165 yds fairway: ~{[d for d in data['fairway'] if abs(d['distance'] - 165) < 5][0]['expected_strokes']}")
print(f"  500 yds tee: ~{[d for d in data['tee'] if abs(d['distance'] - 500) < 10][0]['expected_strokes']}")
print(f"  10 ft putt: 1.61")