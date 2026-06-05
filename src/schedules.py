# schedules.py
# RL training schedule shapes.
# A KERNEL is a pure function of progress_remaining holding one shape's math; it is the single
# source of truth for that shape and the artifact hashed into the run fingerprint.
# An ADAPTER wraps a kernel into a delivery modality (e.g. SB3's learning_rate callable).
# Adapters are pure pass-throughs and are NOT hashed.
#
# To add a shape: define one kernel, register it in SHAPES. Nothing else changes.

def linear(progress_remaining: float, initial: float, final: float) -> float:
    """Linear interpolation: `initial` at progress_remaining=1, `final` at progress_remaining=0."""
    return final + (initial - final) * progress_remaining


# Shape name -> kernel. The single resolution point, shared across all scheduled parameters.
SHAPES = {
    "linear": linear,
}


def make_lr_schedule(shape_type: str, initial: float, final: float):
    """SB3 learning_rate adapter: wraps a registered kernel into a callable of progress_remaining.
    Pure pass-through — no math here; all shape math lives in the kernel."""
    kernel = SHAPES[shape_type]
    return lambda progress_remaining: kernel(progress_remaining, initial, final)
