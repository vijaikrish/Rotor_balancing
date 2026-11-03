from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_multiplane_gui_exposes_safe_units_and_example():
    source = (ROOT / "balancing/gui_multiplane.py").read_text(encoding="utf-8")
    assert "load_example" in source
    assert "mm/s RMS" in source
    assert "trial mass [g]" in source
    assert "non-finite" in source
