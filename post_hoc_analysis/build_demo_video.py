# =============================================================================
# SCRIPT 2: build_demo_video.py
# Composites a hero agent clip + diagnostic report panel into a full demo video.
#
# Layout (1920x1080):
#   ┌────────────────────────────────────────────────────────────────────────┐
#   │  ITERATION 01                                   [STATUS PILL]          │  <- 96px header
#   ├──────────────────────────────┬─────────────────────────────────────────┤
#   │                              │                                         │
#   │    Hero Agent Clip           │    Diagnostic Report                    │
#   │    (seed 0, scaled)          │    (Playwright HTML render)             │
#   │                              │                                         │
#   └──────────────────────────────┴─────────────────────────────────────────┘
#   740px (CLIP_AREA_W)            1180px (REPORT_W)
#
# Usage:
#   python post_hoc_analysis/build_demo_video.py \
#       --campaign_tag "2025-01-15_baseline_10cycles_500kSteps" \
#       --model_name "gpt-4o" \
#       --iterations 1 2 3 4 5 \
#       --num_seeds 3 \
#       --output_name "demo.mp4"
# =============================================================================

import io
import os
import re
import sys
import argparse
from pathlib import Path

import markdown
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

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.workspace_manager import ExperimentWorkspace


# --- Layout Constants ---------------------------------------------------------
CANVAS_W, CANVAS_H = 1920, 1080
HEADER_H    = 96
REPORT_W    = 1180
CLIP_AREA_W = CANVAS_W - REPORT_W
CONTENT_H   = CANVAS_H - HEADER_H
MAX_CLIP_DUR, MIN_CLIP_DUR = 12.0, 3.0
FPS         = 30
INTRO_DUR, OUTRO_DUR = 4.0, 5.0
BG_COLOR    = (10, 10, 18)
HERO_SEED   = 0
STATUS_STYLE = {"CONVERGED": (90, 220, 130), "UNSTABLE": (255, 90, 90)}
BASE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0c0f1c; color:#d2d2dc;
         font-family:-apple-system,'Segoe UI',Roboto,sans-serif; }
"""


# --- Utility: Freeze last frame to fill up to max_dur -------------------------

def freeze_to_duration(clip: VideoFileClip, max_dur: float) -> VideoFileClip:
    """
    If the clip ends before max_dur (agent landed/crashed early), hold the
    last frame for the remainder. If the clip is longer, hard-trim it.
    """
    if clip.duration >= max_dur:
        return clip.subclipped(0, max_dur)

    last_frame  = clip.get_frame(clip.duration - 1 / FPS)
    freeze_dur  = max_dur - clip.duration
    freeze_clip = ImageClip(last_frame, duration=freeze_dur).with_fps(FPS)
    return concatenate_videoclips([clip, freeze_clip])


# --- Utility: Shared HTML → NumPy renderer ------------------------------------

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


# --- Utility: Preprocessing markdown for correct table rendering --------------

def preprocess_markdown(text: str) -> str:
    """Ensure blank line before any markdown table block."""
    lines = text.split('\n')
    result = []
    for i, line in enumerate(lines):
        if (line.startswith('|') and
                i > 0 and result and
                result[-1].strip() and
                not result[-1].strip().startswith('|')):
            result.append('')
        result.append(line)
    return '\n'.join(result)


# --- Utility: Render markdown report to a NumPy image via Playwright ----------

def markdown_to_image(md_path: Path, width: int, height: int) -> np.ndarray:
    md_text = preprocess_markdown(md_path.read_text())
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ font-size:14px; padding:20px; }}
      h1 {{ color:#8cd2ff; font-size:17px; margin:10px 0 6px; }}
      h2 {{ color:#64b9f0; font-size:15px; margin:8px 0 5px; }}
      h3 {{ color:#50a5e1; font-size:14px; margin:6px 0 4px; }}
      p, li {{ line-height:1.45; margin:3px 0; }}
      strong {{ color:#fff; }}
      table {{ border-collapse:collapse; width:100%; font-size:12px; margin:8px 0; table-layout:fixed; }}
      td, th {{ border:1px solid #2a2d4a; padding:5px 8px; }}
      th {{ background:#1a1d32; }}
      td:last-child {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
      hr {{ border:none; border-top:1px solid #2a2d4a; margin:8px 0; }}
      body::after {{ content:''; position:fixed; left:0; right:0; bottom:0; height:80px;
                     background:linear-gradient(transparent,#0c0f1c); }}
    </style></head><body>{body}</body></html>"""
    return render_html_to_image(html, width, height)


# --- Utility: Parse convergence status from a report -------------------------

def parse_status(report_path: Path):
    if not report_path.exists():
        return None
    m = re.search(r"\*\*Status:\*\*.*?\*\*(CONVERGED|UNSTABLE)", report_path.read_text())
    return m.group(1) if m else None


# --- Utility: Render header bar -----------------------------------------------

def make_header(iteration: int, status, width: int = CANVAS_W, height: int = HEADER_H) -> np.ndarray:
    pill = ""
    if status in STATUS_STYLE:
        r, g, b = STATUS_STYLE[status]
        rgb = f"rgb({r},{g},{b})"
        pill = (f'<div class="pill"><span class="dot" style="background:{rgb};color:{rgb}">'
                f'</span><span style="color:{rgb}">{status}</span></div>')
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ background:#10131f; height:{height}px; display:flex; align-items:center;
              justify-content:space-between; padding:0 36px; border-bottom:2px solid #1f2540; }}
      .iter {{ font-size:30px; font-weight:700; letter-spacing:3px; color:#e8e8f0; }}
      .pill {{ display:flex; align-items:center; gap:12px; font-size:23px; font-weight:700;
               letter-spacing:2px; background:#161a2e; padding:9px 22px; border-radius:24px;
               border:1px solid #262c48; }}
      .dot {{ width:15px; height:15px; border-radius:50%; box-shadow:0 0 12px currentColor; }}
    </style></head><body>
      <div class="iter">ITERATION {iteration:02d}</div>{pill}
    </body></html>"""
    return render_html_to_image(html, width, height)


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
      <div class="title">ARD · Algorithmic Reward Design</div>
      <div class="sub">An autonomous multi-agent system where LLMs read RL training telemetry and iteratively redesign the reward function.</div>
      <div class="meta">LUNARLANDER-V3 · SELF-HOSTED LLMs · CLOSED-LOOP</div>
    </body></html>"""
    return render_html_to_image(html, width, height)


def make_outro_card(width: int = CANVAS_W, height: int = CANVAS_H) -> np.ndarray:
    html = f"""<html><head><style>
      {BASE_CSS}
      body {{ height:{height}px; display:flex; flex-direction:column; align-items:center;
              justify-content:center; text-align:center; }}
      .result {{ font-size:46px; font-weight:700; color:#e8e8f0; }}
      .hl {{ color:#5adc82; }}
      .repo {{ font-size:24px; color:#64b9f0; margin-top:50px; letter-spacing:1px; }}
    </style></head><body>
      <div class="result">Crash-dominant &rarr; <span class="hl">73% landing success</span><br>across 5 reward-design iterations</div>
      <div class="repo">github.com/dominik-klingshirn/rl_agent_loop</div>
    </body></html>"""
    return render_html_to_image(html, width, height)


# --- Core: build one iteration's composite clip --------------------------------

def build_iteration_composite(
    iteration: int,
    ws: ExperimentWorkspace,
    num_seeds: int,
) -> CompositeVideoClip:
    videos_dir  = ws.dirs["root"] / "artifacts" / f"iteration{iteration:02d}" / "videos"
    report_path = ws.dirs["telemetry_reports"] / f"iter{iteration:02d}_report.md"

    hero = min(HERO_SEED, num_seeds - 1)
    clip_path = videos_dir / f"iter{iteration:02d}_seed{hero}.mp4"
    if not clip_path.exists():
        raise FileNotFoundError(f"Missing hero clip: {clip_path}")
    clip = VideoFileClip(str(clip_path))
    target_dur = max(min(clip.duration, MAX_CLIP_DUR), MIN_CLIP_DUR)
    clip = freeze_to_duration(clip, target_dur)

    margin = 40
    scale  = min((CLIP_AREA_W - 2*margin) / 600, (CONTENT_H - 2*margin) / 400)
    cw, ch = int(600*scale), int(400*scale)
    clip = clip.resized((cw, ch)).with_position(
        ((CLIP_AREA_W - cw)//2, HEADER_H + (CONTENT_H - ch)//2))

    if report_path.exists():
        report_arr = markdown_to_image(report_path, REPORT_W, CONTENT_H)
    else:
        print(f"  WARNING: report missing at {report_path}")
        report_arr = np.full((CONTENT_H, REPORT_W, 3), BG_COLOR, dtype=np.uint8)
    report_clip = (ImageClip(report_arr, duration=target_dur)
                   .with_position((CLIP_AREA_W, HEADER_H))
                   .with_fps(FPS))

    header_clip = (ImageClip(make_header(iteration, parse_status(report_path)),
                             duration=target_dur)
                   .with_position((0, 0))
                   .with_fps(FPS))
    divider = (ImageClip(np.full((CONTENT_H, 2, 3), (40, 50, 80), dtype=np.uint8),
                         duration=target_dur)
               .with_position((CLIP_AREA_W - 1, HEADER_H))
               .with_fps(FPS))
    bg = ColorClip(size=(CANVAS_W, CANVAS_H), color=BG_COLOR, duration=target_dur)

    return CompositeVideoClip([bg, clip, divider, report_clip, header_clip],
                              size=(CANVAS_W, CANVAS_H))


# --- Build full demo ----------------------------------------------------------

def build_full_demo(
    iterations: list[int],
    ws: ExperimentWorkspace,
    num_seeds: int,
    output_name: str,
):
    segments = [ImageClip(make_intro_card(), duration=INTRO_DUR).with_fps(FPS)]
    for iteration in iterations:
        print(f"\n  Building composite for iteration {iteration:02d}")
        segments.append(build_iteration_composite(iteration, ws, num_seeds))
    segments.append(ImageClip(make_outro_card(), duration=OUTRO_DUR).with_fps(FPS))
    final = concatenate_videoclips(segments, method="compose")

    output_path = ws.dirs["root"] / "artifacts" / f"{output_name}.mp4"
    print(f"\n  Exporting to: {output_path}")
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio=False,          # no audio yet — voiceover added in CapCut
        threads=4,
        preset="slow",        # better compression; use "fast" if you're impatient
        ffmpeg_params=["-crf", "18"],  # visually lossless for a portfolio piece
    )
    print("\nDone.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_tag", type=str, required=True)
    parser.add_argument("--model_name",   type=str, required=True)
    parser.add_argument("--iterations",   type=int, nargs="+", required=True,
                        help="e.g. --iterations 1 2 3 4 5")
    parser.add_argument("--num_seeds",    type=int, default=3)
    parser.add_argument("--output_name",  type=str, default=None,
                        help="Output filename stem (no .mp4). Defaults to "
                             "{campaign_tag}_{model_name} with ':' and '/' replaced by '-'.")
    args = parser.parse_args()

    if args.output_name is None:
        safe_model       = args.model_name.replace(":", "-").replace("/", "-")
        args.output_name = f"{args.campaign_tag}_{safe_model}"

    os.environ["CAMPAIGN_TAG"] = args.campaign_tag
    os.environ["LLM_MODEL"]    = args.model_name

    # Workspace only needs a valid iteration number to resolve paths —
    # use the first iteration since all share the same campaign root
    ws = ExperimentWorkspace(iteration=args.iterations[0])

    print(f"\nBuilding demo video")
    print(f"  Campaign : {args.campaign_tag}")
    print(f"  Model    : {args.model_name}")
    print(f"  Iters    : {args.iterations}")
    print(f"  Seeds    : {args.num_seeds}")

    build_full_demo(args.iterations, ws, args.num_seeds, args.output_name)


if __name__ == "__main__":
    main()
