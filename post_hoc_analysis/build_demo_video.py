# =============================================================================
# build_demo_video.py
# Composites a hero agent clip + a CURATED telemetry card into a demo video.
#
# The card is built from the structured metric payload (ws.load_metrics), NOT
# by parsing the rendered Diagnostic Report markdown. This is robust to report
# wording changes and mirrors the project's "structured sources over prose"
# principle. The full per-iteration Diagnostic Report lives in the repo
# (CASE_STUDY_FROM_README/) for curious readers — the video stays lightweight.
#
# Layout (1920x1080) — clip-dominant:
#   ┌────────────────────────────────────────────────────────────────────────┐
#   │  ITERATION 05      01 02 03 04 05 · landing 73%        [STATUS PILL]    │  <- 96px header
#   ├──────────────────────────────────────────────┬─────────────────────────┤
#   │                                               │  Universal Robustness   │
#   │            Hero Agent Clip                     │     73.3%               │
#   │            (seed 0, scaled, dominant)          │  landing success        │
#   │                                               │  Reward aligned ...     │
#   │                                               │  [component flag chips] │
#   └──────────────────────────────────────────────┴─────────────────────────┘
#   1160px (clip area)                                760px (CARD_W)
#
# Usage:
#   python post_hoc_analysis/build_demo_video.py \
#       --campaign_tag "2026-06-11_spin_crash_10cycles_1MSteps_remote_baselineV1..." \
#       --model_name "gemma4:26b-mlx" \
#       --iterations 1 2 3 4 5 6 7 8 9 10 \
#       --num_seeds 4 \
#       --output_name "demo"
# =============================================================================

import io
import json
import os
import sys
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from moviepy import (
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ColorClip,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
from src.workspace_manager import ExperimentWorkspace


# --- Layout Constants ---------------------------------------------------------
CANVAS_W, CANVAS_H = 1920, 1080
HEADER_H    = 96
CARD_W      = 760                        # sparse telemetry card; clip gets the rest
CONTENT_H   = CANVAS_H - HEADER_H
FPS         = 30
INTRO_DUR, OUTRO_DUR = 4.0, 5.0
BG_COLOR    = (10, 10, 18)
HERO_SEED   = 0
MAX_COMPONENTS = 10                      # cap chips for legibility; full set is in the repo report
GRID_W      = 960                        # square block; clamped to clip-area width at use
GRID_H      = 960                        # set != GRID_W to experiment with non-square blocks
GRID_GUTTER = 16
SHOW_SEED_LABELS  = True
SHOW_GRID_DIVIDER = True
TAIL_HOLD   = 1.0                        # seconds of final-frame hold added on top of natural length
STATUS_STYLE = {
    "CONVERGED": (90, 220, 130),
    "UNSTABLE": (255, 90, 90),
    "HIGHLY SENSITIVE TO INITIALIZATION": (255, 180, 60),
}
BASE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0c0f1c; color:#d2d2dc;
         font-family:-apple-system,'Segoe UI',Roboto,sans-serif; }
"""
TERM_MODES = [
    {"key": "term_centered",             "label": "landed_centered",             "color": "#2ca02c"},
    {"key": "term_off_centered",         "label": "landed_off_centered",         "color": "#1f77b4"},
    {"key": "term_off_centered_timeout", "label": "landed_off_centered_timeout", "color": "#186499"},
    {"key": "term_slid",                 "label": "landed_but_slid",             "color": "#1A6BA4"},
    {"key": "term_crashed",              "label": "crashed",                     "color": "#d62728"},
    {"key": "term_oob",                  "label": "out_of_bounds",               "color": "#9467bd"},
    {"key": "term_hover",                "label": "hover_timeout",               "color": "#ff7f0e"},
]
TERM_STYLE = {
    "landed_centered":             ("landed_centered",             "#2ca02c"),
    "landed_off_centered":         ("landed_off_centered",         "#1f77b4"),
    "landed_off_centered_timeout": ("landed_off_centered_timeout", "#186499"),
    "landed_but_slid_into_valley": ("landed_but_slid",             "#1A6BA4"),
    "crashed":                     ("crashed",                     "#d62728"),
    "out_of_bounds":               ("out_of_bounds",               "#9467bd"),
    "hover_timeout":               ("hover_timeout",               "#ff7f0e"),
}
_ORDER = list(TERM_STYLE)

# --- Utility: Freeze last frame to fill up to a target duration ---------------

def freeze_to_duration(clip: VideoFileClip, max_dur: float) -> VideoFileClip:
    """Hold the last frame if the clip is shorter than max_dur; hard-trim if longer."""
    if clip.duration >= max_dur:
        return clip.subclipped(0, max_dur)
    last_frame  = clip.get_frame(clip.duration - 1 / FPS)
    freeze_dur  = max_dur - clip.duration
    freeze_clip = ImageClip(last_frame, duration=freeze_dur).with_fps(FPS)
    return concatenate_videoclips([clip, freeze_clip])


# --- Utility: Shared HTML -> NumPy renderer -----------------------------------

def render_html_to_image(html: str, width: int, height: int) -> np.ndarray:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=2)
        page.set_content(html)
        png = page.screenshot(clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()
    img = Image.open(io.BytesIO(png)).convert("RGB").resize((width, height))
    return np.array(img)


# =============================================================================
# Payload readers  (field paths verified against src/analysis.py)
# =============================================================================

def status_from_payload(m: dict):
    """summary_flags -> status string. Mirrors analysis.translate_optimization_health."""
    f = m.get("multi_seed_optimization_health", {}).get("summary_flags", {})
    if f.get("is_initialization_sensitive"):
        return "HIGHLY SENSITIVE TO INITIALIZATION"
    if f.get("is_universally_converged"):
        return "CONVERGED"
    return "UNSTABLE"


def psr_from_payload(m: dict):
    """Deterministic-eval landing success rate (%). analysis.py:452."""
    v = (m.get("multi_seed_evaluation_health", {})
          .get("success_robustness", {})
          .get("population_mean_success_rate"))
    return v * 100 if v is not None else None

def objective_verdict_from_payload(m: dict):
    """Sourced from the stochastic block so the verdict captions the (stochastic)
    component table beneath it — flag and Δ from the same rollouts. The eval-side
    conditional Δ (which inverts on converged runs via hover-timeout reward farming)
    stays in the full diagnostic report, where there's room to explain it."""
    topo  = m.get("multi_seed_stochastic_health", {}).get("global_reward_topology", {})
    delta = topo.get("global_conditional_delta")
    if delta is None:
            dtxt = "\u0394 undefined"
            rates = topo.get("seed_success_rates", [])
            mean_succ = sum(rates) / len(rates) if rates else None
            if mean_succ is not None and mean_succ < 0.005:
                return f"No landings \u00b7 reward unaligned   ({dtxt})", "#ff5a5a"
            if mean_succ is not None and mean_succ > 0.995:
                return f"Universal landing   ({dtxt})", "#5adc82"
            return f"Alignment indeterminate   ({dtxt})", "#8a90a6"
    else:
        if delta < 0: dtxt = "\u0394 < 0"
        elif delta > 0: dtxt = "\u0394 > 0"
        else: dtxt = "\u0394 = 0"

    if topo.get("topology_is_inverted_flag"):
        return f"Reward rewards crashing   ({dtxt})", "#ff5a5a"
    if topo.get("rho_delta_divergence_flag"):
        return f"Aligned, non-linear   ({dtxt})", "#5ab0ff"
    if delta > 0:
        return f"Reward aligned with landing   ({dtxt})", "#5adc82"
    return f"Alignment indeterminate   ({dtxt})", "#8a90a6"

def resolve_component_flag(m: dict):
    """(short_label, css_color) for a component chip.
    Mirrors the 8-level priority ladder in analysis.translate_reward_topology
    (spec: docs/DIAGNOSTIC_TRANSLATION.md flag legend). Numbers omitted for the video."""
    rho = m.get("alignment_rho", 0.0)
    if m.get("is_traitor_component") and rho < -0.2: return "NEGATIVELY ALIGNED", "#ff5a5a"
    if m.get("is_hidden_traitor"):                   return "HIDDEN TRAITOR", "#ff5a5a"
    if m.get("is_hidden_helper"):                    return "NON-LINEAR HELPER", "#5ab0ff"
    if m.get("is_hidden_dependency"):                return "HIDDEN DEPENDENCY", "#b97aff"
    if m.get("is_dead_weight"):                      return "LOW MAGNITUDE", "#e2c14d"
    if m.get("is_high_magnitude_neutral"):           return "UNRESOLVED", "#ffa24d"
    if rho < 0.2:                                    return "Neutral", "#8a90a6"
    return "Optimal", "#5adc82"


# --- Utility: Curated telemetry card (from payload) ---------------------------

def payload_panel_to_image(metrics: dict, width: int, height: int) -> np.ndarray:
    comps     = metrics.get("multi_seed_stochastic_health", {}).get("dynamic_component_analysis", {})
    term_dist = (metrics.get("multi_seed_evaluation_health", {})
                    .get("failure_mode_analysis", {})
                    .get("population_terminal_distribution", {}))
    obj_txt, obj_col = objective_verdict_from_payload(metrics)

    bar_segs, legend_items = [], []
    present = [(k, v) for k, v in term_dist.items() if v and v > 0]
    present.sort(key=lambda kv: (_ORDER.index(kv[0]) if kv[0] in _ORDER else 99))
    for status, v in present:
        label, color = TERM_STYLE.get(status, (status, "#8a90a6"))
        bar_segs.append(f'<div class="bseg" style="width:{v*100:.2f}%;background:{color}"></div>')
        legend_items.append(
            f'<span class="li"><span class="lswatch" style="background:{color}"></span>'
            f'<span class="lt">{label} {v*100:.0f}%</span></span>')
    bar_html    = "".join(bar_segs)
    legend_html = "".join(legend_items)

    rows = []
    for name, m in sorted(comps.items(),
                      key=lambda kv: kv[1].get("relative_magnitude_pct", 0.0),
                      reverse=True)[:MAX_COMPONENTS]:

        label, col = resolve_component_flag(m)
        rho = m.get("alignment_rho", 0.0)
        clean = name.replace("reward_", "", 1)
        rows.append(
            f'<div class="row"><span class="cn">{clean}</span>'
            f'<span class="rho">\u03c1 {rho:+.2f}</span>'
            f'<span class="chip" style="color:{col};border-color:{col}55;background:{col}1a">{label}</span></div>')
    rows_html = "".join(rows)

    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ height:{height}px; padding:46px 44px; display:flex; flex-direction:column; }}
      .kicker {{ font-size:15px; letter-spacing:3px; color:#5a6280; text-transform:uppercase; margin-bottom:14px; }}
      .bar {{ display:flex; width:100%; height:22px; border-radius:4px; overflow:hidden; margin-bottom:12px; }}
      .bseg {{ height:100%; }}
      .legend {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin-bottom:28px; }}
      .li {{ display:flex; align-items:center; gap:6px; }}
      .lswatch {{ width:11px; height:11px; border-radius:2px; flex-shrink:0; }}
      .lt {{ font-size:12px; color:#8a90a6; }}
      .obj {{ font-size:25px; font-weight:700; color:{obj_col}; margin-bottom:30px; }}
      .objlbl {{ font-size:13px; letter-spacing:2px; color:#5a6280; text-transform:uppercase; margin-bottom:10px; }}
      .objformula {{ font-family:Georgia,'Times New Roman',serif; font-size:20px; color:#5a6280; margin-bottom:12px; }}
      .cchdr {{ font-size:13px; letter-spacing:2px; color:#5a6280; text-transform:uppercase; margin-bottom:10px; }}
      .row {{ display:flex; align-items:center; gap:14px; padding:9px 0; border-bottom:1px solid #181b2c; }}
      .cn {{ font-family:ui-monospace,Menlo,monospace; font-size:19px; color:#c4c8d6; flex:0 0 220px; }}
      .rho {{ font-family:ui-monospace,Menlo,monospace; font-size:15px; color:#6b7290; flex:0 0 86px; }}
      .chip {{ font-size:14px; font-weight:700; padding:4px 12px; border-radius:13px; border:1px solid; }}
    </style></head><body>
      <div class="kicker">Behavior Distribution</div>
      <div class="bar">{bar_html}</div>
      <div class="legend">{legend_html}</div>
      <div class="objlbl">Global Objective Alignment \u00b7 Oracle Test</div>
      <div class="objformula">\u0394 = \U0001D53C[<i>R</i> | land] \u2212 \U0001D53C[<i>R</i> | fail]</div>
      <div class="obj">{obj_txt}</div>
      <div class="cchdr">Component Credit Assignment</div>
      {rows_html}
    </body></html>"""
    return render_html_to_image(html, width, height)


# --- Utility: Header bar (iteration, trajectory, running success, status) -----

def make_header(iteration: int, status, iters: list, psr,
                width: int = CANVAS_W, height: int = HEADER_H,
                is_curated: bool = False) -> np.ndarray:
    pill = ""
    if status in STATUS_STYLE:
        r, g, b = STATUS_STYLE[status]
        rgb = f"rgb({r},{g},{b})"
        pill = (f'<div class="pill"><span class="dot" style="background:{rgb};color:{rgb}">'
                f'</span><span style="color:{rgb}">{status}</span></div>')
    traj = " ".join(
        f'<b style="color:#8cd2ff">{i:02d}</b>' if i == iteration else f'{i:02d}'
        for i in iters)
    psr_html = f'<span style="color:#5adc82">{psr:.0f}%</span>' if psr is not None else "\u2014"
    iter_label = f"ITERATION {iteration:02d} \u00b7 CURATED" if is_curated else f"ITERATION {iteration:02d}"
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ background:#10131f; height:{height}px; display:flex; align-items:center;
              justify-content:space-between; padding:0 36px; border-bottom:2px solid #1f2540; }}
      .iter {{ font-size:30px; font-weight:700; letter-spacing:3px; color:#e8e8f0; }}
      .traj {{ font-size:18px; font-weight:500; color:#4a5070; letter-spacing:2px; }}
      .pill {{ display:flex; align-items:center; gap:12px; font-size:23px; font-weight:700;
               letter-spacing:2px; background:#161a2e; padding:9px 22px; border-radius:24px;
               border:1px solid #262c48; }}
      .dot {{ width:15px; height:15px; border-radius:50%; box-shadow:0 0 12px currentColor; }}
    </style></head><body>
      <div class="iter">{iter_label}</div>
      <div class="traj">{traj}&nbsp;&nbsp;\u00b7&nbsp;&nbsp;landing {psr_html}</div>
      {pill}
    </body></html>"""
    return render_html_to_image(html, width, height)

def dump_stills(iteration: int, ws: ExperimentWorkspace, iterations: list,
                curated_reward: str = None):
    """Render only the panel + header PNGs for one iteration, then return.
    Skips all clip loading / moviepy — sub-second feedback loop for layout work."""
    is_curated_frame = (iteration == 0 and curated_reward is not None)
    if is_curated_frame:
        payload_path = (PROJECT_ROOT / "curated_reward_functions"
                        / f"{curated_reward}_iter00_payload.json")
        with open(payload_path) as _f:
            metrics = json.load(_f)
    else:
        metrics = ws.load_metrics(iteration)

    status = status_from_payload(metrics)
    psr    = psr_from_payload(metrics)
    panel  = payload_panel_to_image(metrics, CARD_W, CONTENT_H)
    header = make_header(iteration, status, iterations, psr,
                         is_curated=is_curated_frame)

    out_dir = ws.dirs["root"] / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(out_dir / f"still_panel_iter{iteration:02d}.png")
    Image.fromarray(header).save(out_dir / f"still_header_iter{iteration:02d}.png")
    print(f"  Wrote still_panel_iter{iteration:02d}.png + still_header_iter{iteration:02d}.png")

# --- Utility: Intro / outro cards ---------------------------------------------

def make_intro_card(width: int = CANVAS_W, height: int = CANVAS_H) -> np.ndarray:
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ height:{height}px; display:flex; flex-direction:column; align-items:center;
              justify-content:center; text-align:center; padding:0 80px; }}
      .title {{ font-size:64px; font-weight:800; letter-spacing:2px;
                background:linear-gradient(90deg,#8cd2ff,#64b9f0);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
      .sub {{ font-size:27px; color:#a8b0c8; margin-top:26px; max-width:1100px; line-height:1.5; }}
      .meta {{ font-size:17px; color:#5a6280; margin-top:42px; letter-spacing:3px; }}
    </style></head><body>
      <div class="title">ARD \u00b7 Algorithmic Reward Design</div>
      <div class="sub">An autonomous multi-agent system where LLMs read RL training telemetry and iteratively redesign the reward function.</div>
      <div class="meta">LUNARLANDER-V3 \u00b7 SELF-HOSTED LLMs \u00b7 CLOSED-LOOP</div>
    </body></html>"""
    return render_html_to_image(html, width, height)


def make_outro_card(init_psr,final_psr, n_iters: int,
                    width: int = CANVAS_W, height: int = CANVAS_H) -> np.ndarray:
    final_psr_str = f"{final_psr:.0f}%" if final_psr is not None else "\u2014%"
    init_psr_str = f"{init_psr:.0f}%" if init_psr is not None else "\u2014%"
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ height:{height}px; display:flex; flex-direction:column; align-items:center;
              justify-content:center; text-align:center; }}
      .result {{ font-size:46px; font-weight:700; color:#e8e8f0; line-height:1.4; }}
      .hl {{ color:#5adc82; }}
      .meta {{ font-size:26px; color:#a8b0c8; margin-top:18px; }}
      .repo {{ font-size:24px; color:#64b9f0; margin-top:50px; letter-spacing:1px; }}
    </style></head><body>
      <div class="result">Autonomously repaired a broken reward<br>
        Unstable Behavior, {init_psr_str} landing &rarr; <span class="hl">Improved Stability, {final_psr_str} landing</span>
        <div class="meta">{n_iters} iterations \u00b7 zero human reward edits</div>
      </div>
      <div class="repo">github.com/dominik-klingshirn/rl_agent_loop</div>
    </body></html>"""
    return render_html_to_image(html, width, height)


# --- Utility: Dwell duration policy -------------------------------------------

def dwell_for(natural_len, status, is_first, is_last):
    """Duration policy. natural_len = max clip duration across the iteration's seeds."""
    target = natural_len + TAIL_HOLD
    if is_first or is_last:
        return min(max(target, 7.0), 11.0)
    if status == "UNSTABLE":
        return min(max(target, 6.0), 9.0)   # instability beat lingers
    return min(max(target, 3.5), 9.0)       # middles: full landing, fast crashes still get 3.5s


# --- Utility: Seed badge (PIL only — no Playwright) ---------------------------

def make_seed_badge(seed_id: int, w: int = 120, h: int = 36) -> np.ndarray:
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGB", (w, h), (16, 19, 31))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    d.text((14, 8), f"seed {seed_id}", fill=(160, 168, 196), font=font)
    return np.array(img)


# --- Core: build one iteration's composite clip --------------------------------

def build_iteration_composite(
    iteration: int,
    ws: ExperimentWorkspace,
    num_seeds: int,
    iterations: list,
    is_first: bool,
    is_last: bool,
    seed_badges: dict,
    curated_reward: str = None,
) -> CompositeVideoClip:
    is_curated_frame = (iteration == 0 and curated_reward is not None)

    if is_curated_frame:
        videos_dir   = PROJECT_ROOT / "curated_reward_functions" / "videos"
        payload_path = PROJECT_ROOT / "curated_reward_functions" / f"{curated_reward}_iter00_payload.json"
        with open(payload_path) as _f:
            metrics = json.load(_f)
    else:
        videos_dir = ws.dirs["root"] / "artifacts" / f"iteration{iteration:02d}" / "videos"
        metrics    = ws.load_metrics(iteration)

    status = status_from_payload(metrics)
    psr    = psr_from_payload(metrics)

    def _clip_name(s: int) -> Path:
        if is_curated_frame:
            return videos_dir / f"{curated_reward}_seed{s}.mp4"
        return videos_dir / f"iter{iteration:02d}_seed{s}.mp4"

    # Load all seed clips; tolerate missing seeds
    seed_clips = []
    for s in range(num_seeds):
        clip_path = _clip_name(s)
        if clip_path.exists():
            seed_clips.append((s, VideoFileClip(str(clip_path))))
        else:
            print(f"WARNING: missing clip {clip_path}")
    if not seed_clips:
        raise FileNotFoundError(
            f"No seed clips found for iteration {iteration:02d} in {videos_dir}")

    natural_len = max(c.duration for _, c in seed_clips)
    target_dur  = dwell_for(natural_len, status, is_first, is_last)

    # Geometry from constants
    clip_area_w = CANVAS_W - CARD_W
    gw = min(GRID_W, clip_area_w)
    gh = min(GRID_H, CONTENT_H)
    block_x = (clip_area_w - gw) // 2
    block_y = HEADER_H + (CONTENT_H - gh) // 2
    cell_w = (gw - GRID_GUTTER) // 2
    cell_h = (gh - GRID_GUTTER) // 2

    cells = []
    badge_clips = []
    for s, clip in seed_clips:
        r, c = s // 2, s % 2
        clip = freeze_to_duration(clip, target_dur)
        scale = min(cell_w / clip.w, cell_h / clip.h)
        cw, ch = int(clip.w * scale), int(clip.h * scale)
        ox = block_x + c * (cell_w + GRID_GUTTER)
        oy = block_y + r * (cell_h + GRID_GUTTER)
        cells.append(clip.resized((cw, ch)).with_position(
            (ox + (cell_w - cw) // 2, oy + (cell_h - ch) // 2)))

        if SHOW_SEED_LABELS and s in seed_badges:
            badge_w = 120
            badge_clips.append(
                ImageClip(seed_badges[s], duration=target_dur)
                .with_fps(FPS)
                .with_position((ox + (cell_w - badge_w) // 2, oy + cell_h - 40)))

    grid_dividers = []
    if SHOW_GRID_DIVIDER:
        vbar = np.full((gh, 2, 3), (40, 50, 80), dtype=np.uint8)
        grid_dividers.append(
            ImageClip(vbar, duration=target_dur)
            .with_fps(FPS)
            .with_position((block_x + cell_w + GRID_GUTTER // 2, block_y)))
        hbar = np.full((2, gw, 3), (40, 50, 80), dtype=np.uint8)
        grid_dividers.append(
            ImageClip(hbar, duration=target_dur)
            .with_fps(FPS)
            .with_position((block_x, block_y + cell_h + GRID_GUTTER // 2)))

    panel_clip = (ImageClip(payload_panel_to_image(metrics, CARD_W, CONTENT_H),
                            duration=target_dur)
                  .with_position((clip_area_w, HEADER_H))
                  .with_fps(FPS))
    header_clip = (ImageClip(make_header(iteration, status, iterations, psr,
                                        is_curated=is_curated_frame),
                             duration=target_dur)
                   .with_position((0, 0))
                   .with_fps(FPS))
    card_divider = (ImageClip(np.full((CONTENT_H, 2, 3), (40, 50, 80), dtype=np.uint8),
                              duration=target_dur)
                    .with_position((clip_area_w - 1, HEADER_H))
                    .with_fps(FPS))
    bg = ColorClip(size=(CANVAS_W, CANVAS_H), color=BG_COLOR, duration=target_dur)

    return CompositeVideoClip(
        [bg, *cells, *grid_dividers, *badge_clips, card_divider, panel_clip, header_clip],
        size=(CANVAS_W, CANVAS_H))


# --- Build full demo ----------------------------------------------------------

def build_full_demo(
    iterations: list,
    ws: ExperimentWorkspace,
    num_seeds: int,
    output_name: str,
    curated_reward: str = None,
):
    real_iters = list(iterations)
    loop_iters = ([0] + real_iters) if (curated_reward and 0 not in real_iters) else real_iters

    seed_badges = {s: make_seed_badge(s) for s in range(num_seeds)}
    segments = [ImageClip(make_intro_card(), duration=INTRO_DUR).with_fps(FPS)]
    for i, iteration in enumerate(loop_iters):
        is_first = i == 0
        is_last  = i == len(iterations) - 1
        print(f"\n  Building composite for iteration {iteration:02d}")
        segments.append(
            build_iteration_composite(
                iteration, ws, num_seeds, iterations, is_first, is_last, seed_badges,
                curated_reward=curated_reward))

    # Iteration 0 payload is in a different location
    init_payload_path = PROJECT_ROOT / "curated_reward_functions" / f"{curated_reward}_iter00_payload.json"
    with open(init_payload_path) as _f:
        init_metrics = json.load(_f)

    init_psr = psr_from_payload(init_metrics)
    final_psr = psr_from_payload(ws.load_metrics(real_iters[-1]))
    segments.append(
        ImageClip(
            make_outro_card(init_psr,final_psr,len(real_iters)),
            duration=OUTRO_DUR
            ).with_fps(FPS))

    final = concatenate_videoclips(segments, method="compose")
    output_path = ws.dirs["root"] / "artifacts" / f"{output_name}.mp4"
    print(f"\n  Exporting to: {output_path}")
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio=False,          # no audio yet — voiceover added in post
        threads=4,
        preset="fast",        # better compression; use "fast" while iterating
        ffmpeg_params=["-crf", "18"],
        logger=None,
    )
    print("\nDone.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_tag", type=str, required=True)
    parser.add_argument("--model_name",   type=str, required=True)
    parser.add_argument("--iterations",   type=int, nargs="+", required=True,
                        help="e.g. --iterations 1 2 3 4 5 6 7 8 9 10")
    parser.add_argument("--num_seeds",    type=int, default=4)
    parser.add_argument("--output_name",  type=str, default=None,
                        help="Output filename stem (no .mp4). Defaults to "
                             "{campaign_tag}_{model_name} with ':' and '/' replaced by '-'.")
    parser.add_argument("--curated_reward", type=str, default=None,
                        help="Curated reward name (e.g. spin_crash). When set, iteration 0 "
                             "sources videos and payload from curated_reward_functions/.")
    parser.add_argument("--still", type=int, default=None,
                    help="Render only panel+header PNGs for this iteration, then exit.")
    args = parser.parse_args()

    if args.output_name is None:
        safe_model       = args.model_name.replace(":", "-").replace("/", "-")
        args.output_name = f"{args.campaign_tag}_{safe_model}"

    os.environ["CAMPAIGN_TAG"] = args.campaign_tag
    os.environ["LLM_MODEL"]    = args.model_name

    # Workspace only needs a valid iteration to resolve the campaign root;
    # per-iteration payloads are loaded by number inside the build.
    ws = ExperimentWorkspace(iteration=args.iterations[0])

    print(f"\nBuilding demo video")
    print(f"  Campaign : {args.campaign_tag}")
    print(f"  Model    : {args.model_name}")
    print(f"  Iters    : {args.iterations}")
    print(f"  Seeds    : {args.num_seeds}")

    if args.still is not None:
        dump_stills(args.still, ws, args.iterations, curated_reward=args.curated_reward)
        return
    
    build_full_demo(
        args.iterations,
        ws,
        args.num_seeds,
        args.output_name,
        curated_reward=args.curated_reward
        )


if __name__ == "__main__":
    main()