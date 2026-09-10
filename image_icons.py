"""
Small vector-icon library for the infographic renderer.
Every icon is drawn with plain matplotlib patches/lines so it renders
identically on any machine (no emoji fonts, no external assets).

draw_icon(ax, cx, cy, kind, color, r) draws icon `kind` centered at
(cx, cy) inside an implicit circle of radius `r`.
"""
from __future__ import annotations
import matplotlib.patches as mpatches
from matplotlib.path import Path


ICON_KINDS = [
    "check", "cross", "warning", "gear", "shield", "rocket", "bulb",
    "chart", "lock", "target", "database", "star", "magnify", "coin",
    "clock", "refresh", "cloud", "scale", "puzzle", "arrow_up",
]


def _line(ax, pts, color, lw=2.4, zorder=5):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round",
             solid_joinstyle="round", zorder=zorder)


def draw_icon(ax, cx, cy, kind, color="#2563eb", r=0.28, lw=2.6, zorder=5):
    """Draw a simple flat-style icon centered at (cx, cy)."""
    kind = (kind or "check").lower()

    if kind == "check":
        _line(ax, [(cx - r * 0.55, cy - r * 0.05),
                    (cx - r * 0.12, cy - r * 0.5),
                    (cx + r * 0.6, cy + r * 0.55)], color, lw, zorder)

    elif kind == "cross":
        _line(ax, [(cx - r * 0.5, cy - r * 0.5), (cx + r * 0.5, cy + r * 0.5)], color, lw, zorder)
        _line(ax, [(cx - r * 0.5, cy + r * 0.5), (cx + r * 0.5, cy - r * 0.5)], color, lw, zorder)

    elif kind == "warning":
        tri = mpatches.RegularPolygon((cx, cy - r * 0.05), numVertices=3, radius=r * 0.95,
                                       orientation=0, facecolor="none", edgecolor=color,
                                       linewidth=lw, zorder=zorder)
        ax.add_patch(tri)
        ax.plot([cx], [cy - r * 0.05], marker="", zorder=zorder)
        _line(ax, [(cx, cy + r * 0.05), (cx, cy - r * 0.35)], color, lw * 0.9, zorder)
        ax.add_patch(mpatches.Circle((cx, cy - r * 0.55), r * 0.06, facecolor=color,
                                      edgecolor="none", zorder=zorder))

    elif kind == "gear":
        ax.add_patch(mpatches.Circle((cx, cy), r * 0.42, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Circle((cx, cy), r * 0.14, facecolor=color,
                                      edgecolor="none", zorder=zorder))
        import math
        for i in range(8):
            ang = math.radians(i * 45)
            x1, y1 = cx + math.cos(ang) * r * 0.5, cy + math.sin(ang) * r * 0.5
            x2, y2 = cx + math.cos(ang) * r * 0.78, cy + math.sin(ang) * r * 0.78
            _line(ax, [(x1, y1), (x2, y2)], color, lw * 0.9, zorder)

    elif kind == "shield":
        verts = [(cx, cy + r * 0.85), (cx + r * 0.7, cy + r * 0.45),
                  (cx + r * 0.7, cy - r * 0.25), (cx, cy - r * 0.9),
                  (cx - r * 0.7, cy - r * 0.25), (cx - r * 0.7, cy + r * 0.45),
                  (cx, cy + r * 0.85)]
        ax.add_patch(mpatches.Polygon(verts, closed=True, facecolor="none",
                                       edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, [(cx - r * 0.28, cy - r * 0.05), (cx - r * 0.05, cy - r * 0.3),
                    (cx + r * 0.35, cy + r * 0.3)], color, lw * 0.85, zorder)

    elif kind == "rocket":
        body = mpatches.FancyBboxPatch((cx - r * 0.22, cy - r * 0.55), r * 0.44, r * 1.05,
                                        boxstyle="round,pad=0,rounding_size=0.12",
                                        facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder)
        ax.add_patch(body)
        tip = mpatches.Polygon([(cx - r * 0.22, cy + r * 0.5), (cx, cy + r * 0.95),
                                 (cx + r * 0.22, cy + r * 0.5)], closed=True,
                                facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder)
        ax.add_patch(tip)
        fin_l = mpatches.Polygon([(cx - r * 0.22, cy - r * 0.3), (cx - r * 0.55, cy - r * 0.7),
                                   (cx - r * 0.22, cy - r * 0.55)], closed=True,
                                  facecolor=color, edgecolor="none", zorder=zorder)
        fin_r = mpatches.Polygon([(cx + r * 0.22, cy - r * 0.3), (cx + r * 0.55, cy - r * 0.7),
                                   (cx + r * 0.22, cy - r * 0.55)], closed=True,
                                  facecolor=color, edgecolor="none", zorder=zorder)
        ax.add_patch(fin_l)
        ax.add_patch(fin_r)

    elif kind == "bulb":
        ax.add_patch(mpatches.Circle((cx, cy + r * 0.15), r * 0.55, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Rectangle((cx - r * 0.22, cy - r * 0.65), r * 0.44, r * 0.28,
                                         facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, [(cx - r * 0.18, cy - r * 0.85), (cx + r * 0.18, cy - r * 0.85)], color, lw * 0.9, zorder)

    elif kind == "chart":
        base_y = cy - r * 0.55
        bars = [(-r * 0.5, r * 0.5), (-r * 0.12, r * 0.9), (r * 0.26, r * 1.3)]
        for bx, bh in bars:
            ax.add_patch(mpatches.Rectangle((cx + bx, base_y), r * 0.34, bh * 0.55,
                                             facecolor=color, edgecolor="none", zorder=zorder))
        _line(ax, [(cx - r * 0.7, base_y), (cx + r * 0.7, base_y)], color, lw * 0.8, zorder)

    elif kind == "lock":
        ax.add_patch(mpatches.FancyBboxPatch((cx - r * 0.45, cy - r * 0.55), r * 0.9, r * 0.75,
                                              boxstyle="round,pad=0,rounding_size=0.08",
                                              facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder))
        arc = mpatches.Arc((cx, cy + r * 0.05), r * 0.65, r * 0.9, theta1=0, theta2=180,
                            edgecolor=color, linewidth=lw, zorder=zorder)
        ax.add_patch(arc)
        ax.add_patch(mpatches.Circle((cx, cy - r * 0.18), r * 0.09, facecolor=color,
                                      edgecolor="none", zorder=zorder))

    elif kind == "target":
        for rr, lwid in [(r * 0.85, lw), (r * 0.5, lw), (r * 0.15, 0)]:
            if rr == r * 0.15:
                ax.add_patch(mpatches.Circle((cx, cy), rr, facecolor=color, edgecolor="none", zorder=zorder))
            else:
                ax.add_patch(mpatches.Circle((cx, cy), rr, facecolor="none", edgecolor=color,
                                              linewidth=lwid, zorder=zorder))

    elif kind == "database":
        w, h = r * 0.9, r * 0.35
        for dy in (r * 0.5, 0, -r * 0.5):
            ax.add_patch(mpatches.Ellipse((cx, cy + dy), w, h, facecolor="none",
                                           edgecolor=color, linewidth=lw * 0.85, zorder=zorder))
        _line(ax, [(cx - w / 2, cy + r * 0.5), (cx - w / 2, cy - r * 0.5)], color, lw * 0.85, zorder)
        _line(ax, [(cx + w / 2, cy + r * 0.5), (cx + w / 2, cy - r * 0.5)], color, lw * 0.85, zorder)

    elif kind == "star":
        star = mpatches.RegularPolygon((cx, cy), numVertices=5, radius=r * 0.85,
                                        orientation=3.14159, facecolor="none",
                                        edgecolor=color, linewidth=lw, zorder=zorder)
        ax.add_patch(star)

    elif kind == "magnify":
        ax.add_patch(mpatches.Circle((cx - r * 0.12, cy + r * 0.12), r * 0.5, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, [(cx + r * 0.24, cy - r * 0.24), (cx + r * 0.62, cy - r * 0.62)], color, lw * 1.1, zorder)

    elif kind == "coin":
        ax.add_patch(mpatches.Circle((cx, cy), r * 0.75, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.text(cx, cy, "$", ha="center", va="center", fontsize=r * 34, color=color,
                fontweight="bold", zorder=zorder + 1)

    elif kind == "clock":
        ax.add_patch(mpatches.Circle((cx, cy), r * 0.8, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        _line(ax, [(cx, cy), (cx, cy + r * 0.45)], color, lw * 0.9, zorder)
        _line(ax, [(cx, cy), (cx + r * 0.35, cy - r * 0.1)], color, lw * 0.9, zorder)

    elif kind == "refresh":
        import math
        arc1 = mpatches.Arc((cx, cy), r * 1.5, r * 1.5, theta1=30, theta2=300,
                             edgecolor=color, linewidth=lw, zorder=zorder)
        ax.add_patch(arc1)
        ang = math.radians(300)
        hx, hy = cx + math.cos(ang) * r * 0.75, cy + math.sin(ang) * r * 0.75
        arrow = mpatches.Polygon([(hx - r * 0.18, hy + r * 0.05), (hx + r * 0.2, hy + r * 0.12),
                                   (hx + r * 0.02, hy - r * 0.22)], closed=True,
                                  facecolor=color, edgecolor="none", zorder=zorder)
        ax.add_patch(arrow)

    elif kind == "cloud":
        ax.add_patch(mpatches.Circle((cx - r * 0.3, cy - r * 0.05), r * 0.38, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Circle((cx + r * 0.15, cy + r * 0.12), r * 0.45, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Circle((cx + r * 0.45, cy - r * 0.1), r * 0.3, facecolor="none",
                                      edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Rectangle((cx - r * 0.55, cy - r * 0.45), r * 1.1, r * 0.4,
                                         facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder))

    elif kind == "scale":
        _line(ax, [(cx, cy - r * 0.6), (cx, cy + r * 0.7)], color, lw, zorder)
        _line(ax, [(cx - r * 0.6, cy + r * 0.4), (cx + r * 0.6, cy + r * 0.4)], color, lw, zorder)
        for sx in (-r * 0.6, r * 0.6):
            arc = mpatches.Arc((cx + sx, cy + r * 0.1), r * 0.5, r * 0.5, theta1=200, theta2=340,
                                edgecolor=color, linewidth=lw * 0.9, zorder=zorder)
            ax.add_patch(arc)

    elif kind == "puzzle":
        ax.add_patch(mpatches.FancyBboxPatch((cx - r * 0.5, cy - r * 0.5), r * 1.0, r * 1.0,
                                              boxstyle="round,pad=0,rounding_size=0.06",
                                              facecolor="none", edgecolor=color, linewidth=lw, zorder=zorder))
        ax.add_patch(mpatches.Circle((cx + r * 0.5, cy), r * 0.16, facecolor="none",
                                      edgecolor=color, linewidth=lw * 0.9, zorder=zorder))

    elif kind == "arrow_up":
        _line(ax, [(cx, cy - r * 0.6), (cx, cy + r * 0.6)], color, lw, zorder)
        arrow = mpatches.Polygon([(cx - r * 0.35, cy + r * 0.1), (cx + r * 0.35, cy + r * 0.1),
                                   (cx, cy + r * 0.7)], closed=True,
                                  facecolor=color, edgecolor="none", zorder=zorder)
        ax.add_patch(arrow)

    else:
        # unknown icon kind -> simple dot, never crash the render
        ax.add_patch(mpatches.Circle((cx, cy), r * 0.4, facecolor=color, edgecolor="none", zorder=zorder))
