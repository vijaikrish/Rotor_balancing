import importlib.util
import tkinter as tk
import numpy as np


def test_workbench_example_solve_and_legends():
    assert importlib.util.find_spec('balancing.workbench') is not None, 'Professional workbench missing'
    from balancing.workbench import Application
    root = tk.Tk()
    root.withdraw()
    try:
        app = Application(root)
        for panel in (app.single, app.multi):
            panel.example()
            result = panel.solve()
            assert result is not None
            assert len(panel.result_table.get_children()) == panel.shape[0]
            assert panel.figure.axes[0].get_legend() is not None
            assert np.isfinite(result.correction_weights).all()
        assert 'NASA' in app.help_text.get('1.0', 'end')
    finally:
        root.destroy()
