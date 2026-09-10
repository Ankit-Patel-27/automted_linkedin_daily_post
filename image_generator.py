"""
Image generator for the LinkedIn post pipeline.

Renders a polished, multi-section infographic (bold headline, "the real
problem", a labeled pipeline/flow, a "why this matters" card grid, a "key
mindset" before/after, and an "in simple words" closing banner) directly
with matplotlib - the same visual family as the reference AWS/Databricks
explainer graphics. No external image-generation API calls, so there's
nothing to fail, rate-limit, or mangle diagram text.

Public entry point (unchanged signature so the poster script doesn't need
to change): get_image_for_post(post_data, output_path) -> bool
"""
from __future__ import annotations
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from image_icons import draw_icon

# -- Palette -----------------------------------------------------------
DOMAIN_ACCENTS = {
    "databricks": {"primary": "#FF3621", "secondary": "#1B3139"},
    "aws":        {"primary": "#FF9900", "secondary": "#232F3E"},
    "pyspark":    {"primary": "#E25A1C", "secondary": "#1B3139"},
    "sql":        {"primary": "#336791", "secondary": "#1B3139"},
}
DEFAULT_ACCENT = {"primary": "#4a90e2", "secondary": "#0f2540"}

INK = "#1d3557"
SUBINK = "#4b6584"
BG = "#ffffff"
CARD_BG = "#f7f9fc"
RED, RED_BG = "#e24a4a", "#fdeeee"
GREEN, GREEN_BG = "#1a8f4c", "#e9f9ef"
BLUE, BLUE_BG = "#1d4ed8", "#eef3ff"
PURPLE, PURPLE_BG = "#6d28d9", "#f2ecfd"
NAVY = "#0f2540"


def _wrap(s: str, width: int) -> str:
    return "\n".join(textwrap.wrap(s or "", width=width)) if s else ""


def _section_banner(ax, x, y, w, h, text, bg, fg, icon=None, fontsize=11.5):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015,rounding_size=0.08",
                                          facecolor=bg, edgecolor="none", zorder=3))
    if icon:
        draw_icon(ax, x + h * 0.5, y + h / 2, icon, color=fg, r=h * 0.34)
        ax.text(x + h * 0.9, y + h / 2, text, ha="left", va="center", fontsize=fontsize,
                 fontweight="bold", color=fg, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
                 fontweight="bold", color=fg, zorder=4)


def _default_infographic(post_data: dict) -> dict:
    """Safety net if post_data has no (or a broken) infographic payload."""
    domain = post_data.get("domain", "")
    topic = post_data.get("topic", "Data Engineering")
    return {
        "title": topic.upper()[:70],
        "subtitle": f"A practical look for data engineers working with {domain}",
        "badge": (domain[:4] or "DE").upper(),
        "problem_heading": "THE REAL PROBLEM",
        "problem_points": [
            "Inconsistent or messy inputs", "Manual, error-prone steps",
            "Hard to scale reliably", "Costly to fix downstream",
        ],
        "solution_heading": "HOW DATA ENGINEERS HANDLE THIS",
        "pipeline_heading": f"A REAL {domain.upper()} WORKFLOW" if domain else "A REAL WORKFLOW",
        "pipeline_steps": [
            {"label": "Ingest", "icon": "database"}, {"label": "Process", "icon": "gear"},
            {"label": "Validate", "icon": "check"}, {"label": "Serve", "icon": "chart"},
        ],
        "why_heading": "WHY THIS MATTERS",
        "why_matters": [
            {"title": "Builds Trust", "desc": "Stakeholders trust the data", "icon": "shield"},
            {"title": "Saves Time", "desc": "Less rework, fewer re-runs", "icon": "clock"},
            {"title": "Cost Efficient", "desc": "Less wasted compute & storage", "icon": "coin"},
            {"title": "Scales Well", "desc": "Holds up as data grows", "icon": "chart"},
        ],
        "mindset_heading": "KEY MINDSET OF A DATA ENGINEER",
        "mindset_before": "Anyone can move data around.",
        "mindset_after": "Great engineers build systems that hold up.",
        "simple_words_heading": "IN SIMPLE WORDS",
        "simple_words_chain": [domain or "Raw Data", "Reliable Data"],
        "tagline": "Better data. Better insights. Better impact.",
    }


def render_infographic(post_data: dict, output_path: str = "post_image.png") -> bool:
    try:
        info = dict(post_data.get("infographic") or {})
        defaults = _default_infographic(post_data)
        for k, v in defaults.items():
            info.setdefault(k, v)

        domain_key = (post_data.get("domain") or "").lower()
        accent = DOMAIN_ACCENTS.get(domain_key, DEFAULT_ACCENT)
        primary = accent["primary"]

        W, H = 10.0, 16.3
        fig, ax = plt.subplots(figsize=(W, H))
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.axis("off")
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)

        y = H - 0.55

        # ---- Header --------------------------------------------------
        title = info["title"]
        subtitle = info["subtitle"]
        badge = str(info["badge"]).upper()[:4]

        ax.text(0.55, y, _wrap(title, 24), ha="left", va="top", fontsize=23,
                 fontweight="bold", color=INK, linespacing=1.15, zorder=4)
        ax.add_patch(mpatches.FancyBboxPatch((W - 1.85, H - 0.85), 1.3, 0.55,
                                              boxstyle="round,pad=0.02,rounding_size=0.08",
                                              facecolor=accent["secondary"], edgecolor="none", zorder=4))
        ax.text(W - 1.2, H - 0.575, badge, ha="center", va="center", fontsize=11,
                 fontweight="bold", color="#ffffff", zorder=5)

        title_lines = len(_wrap(title, 24).split("\n"))
        y -= 0.5 * title_lines + 0.35
        if subtitle:
            ax.text(0.55, y, _wrap(subtitle, 60), ha="left", va="top", fontsize=11.5,
                     color=SUBINK, style="italic", zorder=4)
            y -= 0.55
        y -= 0.15
        ax.plot([0.55, W - 0.55], [y, y], color="#e2e8f0", lw=1.4, zorder=2)
        y -= 0.35

        # ---- Problem section -------------------------------------------
        _section_banner(ax, 0.55, y - 0.42, W - 1.1, 0.42, info["problem_heading"],
                         RED_BG, RED, icon="warning")
        y -= 0.68
        for pt in (info["problem_points"] or [])[:4]:
            draw_icon(ax, 0.85, y, "cross", color=RED, r=0.11)
            ax.text(1.15, y, _wrap(str(pt), 44).split("\n")[0], ha="left", va="center",
                     fontsize=10, color=INK, zorder=4)
            y -= 0.33
        y -= 0.12

        # ---- Solution banner ---------------------------------------------
        _section_banner(ax, 0.55, y - 0.42, W - 1.1, 0.42, info["solution_heading"],
                         GREEN_BG, GREEN, icon="check")
        y -= 0.78

        # ---- Pipeline flow --------------------------------------------------
        ax.text(W / 2, y, info["pipeline_heading"], ha="center", va="center", fontsize=11,
                 fontweight="bold", color=accent["secondary"], zorder=4)
        y -= 0.55

        steps = (info["pipeline_steps"] or [])[:5] or defaults["pipeline_steps"]
        n = len(steps)
        margin = 1.0
        span = W - 2 * margin
        step_x = [margin + span * (i / max(n - 1, 1)) for i in range(n)]
        node_r = 0.5
        for i, step in enumerate(steps):
            cx = step_x[i]
            ax.add_patch(mpatches.Circle((cx, y), node_r, facecolor=primary,
                                          edgecolor="none", zorder=4, alpha=0.14))
            ax.add_patch(mpatches.Circle((cx, y), node_r * 0.78, facecolor="#ffffff",
                                          edgecolor=primary, linewidth=2, zorder=5))
            draw_icon(ax, cx, y, step.get("icon", "gear"), color=primary, r=node_r * 0.42, zorder=6)
            ax.text(cx, y - node_r - 0.28, _wrap(str(step.get("label", "")), 12),
                     ha="center", va="top", fontsize=9.3, fontweight="bold", color=INK, zorder=6)
            if i < n - 1:
                ax.annotate("", xy=(step_x[i + 1] - node_r - 0.05, y), xytext=(cx + node_r + 0.05, y),
                             arrowprops=dict(arrowstyle="-|>", color="#c7d2e0", lw=1.8), zorder=3)
        y -= node_r + 0.68

        # ---- Why this matters ----------------------------------------------
        _section_banner(ax, 0.55, y - 0.42, W - 1.1, 0.42, info["why_heading"], BLUE_BG, BLUE)
        y -= 0.75

        why = (info["why_matters"] or [])[:4] or defaults["why_matters"]
        cols = 2
        card_w = (W - 1.1 - 0.3) / cols
        card_h = 1.22
        for i, item in enumerate(why):
            col, row = i % cols, i // cols
            cx0 = 0.55 + col * (card_w + 0.3)
            cy0 = y - row * (card_h + 0.16) - card_h
            ax.add_patch(mpatches.FancyBboxPatch((cx0, cy0), card_w, card_h,
                                                  boxstyle="round,pad=0.02,rounding_size=0.09",
                                                  facecolor=CARD_BG, edgecolor="#e6ebf2", linewidth=1, zorder=3))
            draw_icon(ax, cx0 + 0.42, cy0 + card_h - 0.42, item.get("icon", "star"), color=primary, r=0.24)
            ax.text(cx0 + 0.42, cy0 + card_h - 0.85, _wrap(str(item.get("title", "")), 16),
                     ha="left", va="top", fontsize=9.8, fontweight="bold", color=INK, zorder=4)
            ax.text(cx0 + 0.42, cy0 + card_h - 1.12, _wrap(str(item.get("desc", "")), 20),
                     ha="left", va="top", fontsize=8.3, color=SUBINK, zorder=4)
        rows_used = (len(why) + cols - 1) // cols
        y -= rows_used * (card_h + 0.16) + 0.16

        # ---- Key mindset -----------------------------------------------
        _section_banner(ax, 0.55, y - 0.42, W - 1.1, 0.42, info["mindset_heading"], PURPLE_BG, PURPLE)
        y -= 0.65
        before, after = info["mindset_before"], info["mindset_after"]
        half_w = (W - 1.1 - 0.6) / 2
        ax.add_patch(mpatches.FancyBboxPatch((0.55, y - 0.62), half_w, 0.62,
                                              boxstyle="round,pad=0.02,rounding_size=0.1",
                                              facecolor=RED_BG, edgecolor="none", zorder=3))
        ax.text(0.55 + half_w / 2, y - 0.31, _wrap(str(before), 26), ha="center", va="center",
                 fontsize=8.8, color=RED, fontweight="bold", zorder=4)
        ax.annotate("", xy=(0.55 + half_w + 0.5, y - 0.31), xytext=(0.55 + half_w + 0.1, y - 0.31),
                     arrowprops=dict(arrowstyle="-|>", color=PURPLE, lw=2), zorder=4)
        ax.add_patch(mpatches.FancyBboxPatch((0.55 + half_w + 0.6, y - 0.62), half_w, 0.62,
                                              boxstyle="round,pad=0.02,rounding_size=0.1",
                                              facecolor=GREEN_BG, edgecolor="none", zorder=3))
        ax.text(0.55 + half_w + 0.6 + half_w / 2, y - 0.31, _wrap(str(after), 26), ha="center", va="center",
                 fontsize=8.8, color=GREEN, fontweight="bold", zorder=4)
        y -= 0.85

        # ---- In simple words / footer --------------------------------------
        chain = (info["simple_words_chain"] or [])[:3] or defaults["simple_words_chain"]
        tagline = info["tagline"]

        footer_h = 1.55
        box_top = y
        ax.add_patch(mpatches.FancyBboxPatch((0.55, box_top - footer_h), W - 1.1, footer_h,
                                              boxstyle="round,pad=0.02,rounding_size=0.1",
                                              facecolor=NAVY, edgecolor="none", zorder=3))
        ax.add_patch(mpatches.FancyBboxPatch((0.75, box_top - 0.46), 2.3, 0.34,
                                              boxstyle="round,pad=0.02,rounding_size=0.07",
                                              facecolor=primary, edgecolor="none", zorder=4))
        ax.text(0.75 + 1.15, box_top - 0.29, info["simple_words_heading"], ha="center", va="center",
                 fontsize=8.5, fontweight="bold", color="#ffffff", zorder=5)

        cx = 0.9
        cy_chain = box_top - 0.92
        for i, word in enumerate(chain):
            word = str(word)
            ax.text(cx, cy_chain, word, ha="left", va="center", fontsize=12.5,
                     fontweight="bold", color="#ffffff", zorder=5)
            adv = 0.155 * len(word) + 0.35
            if i < len(chain) - 1:
                ax.annotate("", xy=(cx + adv + 0.3, cy_chain), xytext=(cx + adv, cy_chain),
                             arrowprops=dict(arrowstyle="-|>", color=primary, lw=2), zorder=5)
            cx += adv + 0.5
        ax.text(0.9, box_top - footer_h + 0.3, _wrap(str(tagline), 55), ha="left", va="bottom",
                 fontsize=8.7, color="#c9d6e8", zorder=5)
        y = box_top - footer_h - 0.3

        # ---- Hashtags ----------------------------------------------------
        hashtags = post_data.get("hashtags") or ""
        if hashtags:
            ax.text(W / 2, max(y, 0.35), _wrap(hashtags, 70), ha="center", va="top",
                     fontsize=8, color="#94a3b8", zorder=4)

        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.savefig(output_path, dpi=160, facecolor=BG, edgecolor="none")
        plt.close(fig)
        print(f"✓ Infographic generated: {output_path}")
        return True
    except Exception as e:
        print(f"⚠ Infographic render failed: {e}")
        try:
            plt.close("all")
        except Exception:
            pass
        return False


def get_image_for_post(post_data: dict, output_path: str = "post_image.png") -> bool:
    """Main orchestration entry point used by the poster script."""
    return render_infographic(post_data, output_path=output_path)
