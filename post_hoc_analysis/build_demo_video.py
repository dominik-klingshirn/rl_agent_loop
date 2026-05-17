# =============================================================================
# SCRIPT 2: build_demo_video.py
# Composites per-seed clips + diagnostic report panel into a full demo video.
#
# Layout (1920x1080):
#   ┌─────────────────────────────┬──────────────────┐
#   │  seed 0 | seed 1 | seed 2   │  Diagnostic      │
#   │  (agent clips, side-by-side)│  Report          │
#   │                             │  (rendered .md)  │
#   └─────────────────────────────┴──────────────────┘
#   Iteration label overlaid at top-left.
#
# Usage:
#   python src/build_demo_video.py \
#       --campaign_tag "2025-01-15_baseline_10cycles_500kSteps" \
#       --model_name "gpt-4o" \
#       --iterations 1 2 3 4 5 \
#       --num_seeds 3 \
#       --output_name "demo.mp4"
# =============================================================================

import os
import sys
import argparse
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    clips_array,
    CompositeVideoClip,
    TextClip,
    ColorClip,
)

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.workspace_manager import ExperimentWorkspace


# --- Layout Constants (tweak to taste) ----------------------------------------
CANVAS_W      = 1920
CANVAS_H      = 1080
REPORT_W      = 580     # Width of the diagnostic report panel (right side)
CLIP_AREA_W   = CANVAS_W - REPORT_W   # 1340px for the agent clips
MAX_CLIP_DUR  = 20.0    # Hard cap per episode clip (seconds)
FPS           = 30
TITLE_DUR     = 2.5     # Seconds each iteration title card is shown
BG_COLOR      = (10, 10, 20)


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


# --- Utility: Render markdown report to a PIL image ---------------------------

# Color scheme for the report panel
MD_BG       = (12, 15, 28)
MD_TEXT     = (210, 210, 220)
MD_HEADER1  = (140, 210, 255)   # # headers
MD_HEADER2  = (100, 185, 240)   # ## headers
MD_HEADER3  = (80,  165, 225)   # ### headers
MD_RED      = (255,  90,  90)   # 🔴 traitor components / CRITICAL
MD_YELLOW   = (255, 210,  80)   # 🟡 dead weight
MD_GREEN    = (90,  220, 130)   # 🟢 useful signal
MD_DIM      = (120, 120, 140)   # separator lines / dashes


def _pick_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try common monospace font paths across Linux and macOS."""
    candidates = [
        # Linux (DejaVu)
        f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if bold else ''}.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf" if bold
        else "/System/Library/Fonts/Supplemental/Courier New.ttf",
        # Generic fallback path
        "/usr/share/fonts/truetype/liberation/LiberationMono{}-Regular.ttf".format("-Bold" if bold else ""),
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()  # last resort — no size control


def markdown_to_image(md_path: Path, width: int, height: int) -> np.ndarray:
    """
    Renders a diagnostic report .md file into a numpy RGB image.
    Applies syntax-aware coloring (headers, emoji flags, separators).
    Text that overflows the bottom is clipped — report fits within the panel.
    """
    with open(md_path, "r") as f:
        raw_lines = f.readlines()

    img  = Image.new("RGB", (width, height), color=MD_BG)
    draw = ImageDraw.Draw(img)

    font_normal = _pick_font(11)
    font_bold   = _pick_font(11, bold=True)
    font_h1     = _pick_font(14, bold=True)
    font_h2     = _pick_font(13, bold=True)
    font_h3     = _pick_font(12, bold=True)

    PAD         = 14
    LINE_H      = 16
    WRAP_CHARS  = (width - 2 * PAD) // 7  # approx chars per line at font size 11
    y           = PAD

    for raw in raw_lines:
        line = raw.rstrip("\n")

        # Determine color + font + strip markdown syntax
        if line.startswith("# "):
            color, font, text = MD_HEADER1, font_h1, line[2:]
        elif line.startswith("## "):
            color, font, text = MD_HEADER2, font_h2, line[3:]
        elif line.startswith("### "):
            color, font, text = MD_HEADER3, font_h3, line[4:]
        elif line.startswith("---") or set(line.strip()) <= {"-", "=", "_"}:
            color, font, text = MD_DIM, font_normal, "─" * (WRAP_CHARS - 2)
        elif "🔴" in line or "CRITICAL" in line.upper() or "TRAITOR" in line.upper():
            color, font, text = MD_RED, font_bold, line
        elif "🟡" in line or "DEAD WEIGHT" in line.upper():
            color, font, text = MD_YELLOW, font_normal, line
        elif "🟢" in line or "USEFUL" in line.upper():
            color, font, text = MD_GREEN, font_normal, line
        elif line.startswith("**") and line.endswith("**"):
            color, font, text = MD_HEADER3, font_bold, line.strip("*")
        else:
            color, font, text = MD_TEXT, font_normal, line

        # Word-wrap long lines
        wrapped = textwrap.wrap(text, width=WRAP_CHARS) or [""]
        for subline in wrapped:
            if y + LINE_H > height - PAD:
                break  # clip overflow
            draw.text((PAD, y), subline, font=font, fill=color)
            y += LINE_H
        if y + LINE_H > height - PAD:
            break

    return np.array(img)


# --- Core: build one iteration's composite clip --------------------------------

def build_iteration_composite(
    iteration: int,
    ws: ExperimentWorkspace,
    num_seeds: int,
) -> CompositeVideoClip:
    """
    Loads seed clips, freezes them to a uniform duration (max 20s, but all
    clips within one iteration sync to the longest natural duration among them),
    arranges them side-by-side, and composes with the diagnostic report panel.
    """
    videos_dir  = ws.dirs["videos"]
    reports_dir = ws.dirs["telemetry_reports"]

    # --- Load seed clips ------------------------------------------------------
    clips = []
    for seed_id in range(num_seeds):
        clip_path = videos_dir / f"iter{iteration:02d}_seed{seed_id}.mp4"
        if not clip_path.exists():
            raise FileNotFoundError(
                f"Missing clip: {clip_path}\n"
                f"Run record_clips.py for iteration {iteration} first."
            )
        clips.append(VideoFileClip(str(clip_path)))

    # All clips share the same target duration: longest natural clip, capped at MAX_CLIP_DUR
    natural_durations = [c.duration for c in clips]
    target_dur = min(max(natural_durations), MAX_CLIP_DUR)

    # Freeze short clips so all seeds end at the same time
    clips = [freeze_to_duration(c, target_dur) for c in clips]

    # --- Resize clips to fill the agent panel ---------------------------------
    # Divide the left panel evenly among seeds; preserve ~3:2 aspect ratio
    clip_w = CLIP_AREA_W // num_seeds
    clip_h = int(clip_w * (400 / 600))  # LunarLander native res is 600x400
    clips  = [c.resized((clip_w, clip_h)) for c in clips]

    # Horizontal strip of all seeds
    agent_strip = clips_array([clips])  # shape: [1 row, num_seeds cols]

    # Center the strip vertically in the canvas
    strip_y = (CANVAS_H - clip_h) // 2
    agent_strip = agent_strip.with_position((0, strip_y))

    # --- Diagnostic report panel (right side) --------------------------------
    report_path = reports_dir / f"iter{iteration:02d}_report.md"
    if report_path.exists():
        report_arr = markdown_to_image(report_path, width=REPORT_W, height=CANVAS_H)
    else:
        # Blank placeholder if report is missing
        print(f"  WARNING: Report not found at {report_path}. Using blank panel.")
        report_arr = np.full((CANVAS_H, REPORT_W, 3), fill_value=MD_BG, dtype=np.uint8)

    report_clip = (
        ImageClip(report_arr, duration=target_dur)
        .with_position((CLIP_AREA_W, 0))
    )

    # --- Thin vertical divider between agent panel and report -----------------
    divider_arr = np.full((CANVAS_H, 2, 3), fill_value=(40, 50, 80), dtype=np.uint8)
    divider     = ImageClip(divider_arr, duration=target_dur).with_position((CLIP_AREA_W - 1, 0))

    # --- Iteration label (top-left corner) ------------------------------------
    label = (
        TextClip(
            text=f"Iteration {iteration:02d}",
            font_size=32,
            color="white",
            font="DejaVu-Sans-Mono-Bold",
            stroke_color="black",
            stroke_width=1,
        )
        .with_duration(target_dur)
        .with_position((20, 18))
    )

    # --- Background fill (handles letterbox areas above/below clip strip) ----
    bg = ColorClip(size=(CANVAS_W, CANVAS_H), color=BG_COLOR, duration=target_dur)

    return CompositeVideoClip(
        [bg, agent_strip, divider, report_clip, label],
        size=(CANVAS_W, CANVAS_H),
    )


# --- Build full demo ----------------------------------------------------------

def build_full_demo(
    iterations: list[int],
    ws: ExperimentWorkspace,
    num_seeds: int,
    output_name: str,
):
    """
    Chains iteration composites (with a brief title card between each) and
    exports the final demo video to artifacts/videos/{output_name}.
    """
    segments = []

    for i, iteration in enumerate(iterations):
        print(f"\n  Building composite for iteration {iteration:02d}")

        # Short title card between iterations (except before the first)
        if i > 0:
            card_txt = (
                TextClip(
                    text=f"Iteration {iteration:02d}",
                    font_size=52,
                    color="white",
                    font="DejaVu-Sans-Mono-Bold",
                    bg_color="black",
                )
                .with_duration(TITLE_DUR)
                .with_position("center")
            )
            card = CompositeVideoClip(
                [ColorClip(size=(CANVAS_W, CANVAS_H), color=(0, 0, 0), duration=TITLE_DUR), card_txt],
                size=(CANVAS_W, CANVAS_H),
            )
            segments.append(card)

        composite = build_iteration_composite(iteration, ws, num_seeds)
        segments.append(composite)

    final = concatenate_videoclips(segments, method="compose")

    output_path = ws.dirs["videos"] / output_name
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
    parser.add_argument("--output_name",  type=str, default="demo.mp4")
    args = parser.parse_args()

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