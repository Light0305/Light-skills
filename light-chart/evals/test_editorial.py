"""Data-preservation checks for the new composition primitives, not aesthetic scores."""
from pathlib import Path
import ast
import hashlib
import json
import runpy
import sys
import unittest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/light-chart"
sys.path.insert(0, str(SKILL/"scripts"))
from editorial import (canvas, axes_mm, estimate_column, scientific_heatmap,
                       interval_trajectory, raw_groups, component_matrix, figure_style)


class EditorialData(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_repository_values_preserved_exactly(self):
        folder = ROOT/"Reference  Repositories/figures4papers-main"
        table = json.loads((SKILL/"assets/examples/immunostruct.json").read_text())
        source = folder/"figure_ImmunoStruct/raw_data.py"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), table["_provenance"]["sha256"])
        arrays = runpy.run_path(str(source))
        for key in table.keys()-{"_provenance"}:
            for field in ["mean", "std"]:
                np.testing.assert_array_equal(table[key][field], arrays[key][field])
        table = json.loads((SKILL/"assets/examples/rnagenscape.json").read_text())
        source = folder/"figure_RNAGenScape/plot_comparison.py"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), table["_provenance"]["sha256"])
        for node in ast.parse(source.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in table and name.startswith("results_"):
                    np.testing.assert_array_equal(table[name], ast.literal_eval(node.value))

    def test_intervals_cannot_be_invented_or_silently_clipped(self):
        ax = plt.subplots()[1]
        with self.assertRaises(ValueError):
            estimate_column(ax, [1, 2], ["A", "B"], lower=[.8, 1.5])
        with self.assertRaises(ValueError):
            estimate_column(ax, [1, 2], ["A", "B"], lower=[.8, 1.5], upper=[1.2, 2.5], limits=(.5, 2.2))
        estimate_column(ax, [1, np.nan, 2], ["A", "Missing", "B"], limits=(0, 3))
        self.assertIn("NA", [x.get_text() for x in ax.texts])

    def test_matrix_order_missingness_and_scale_preserved(self):
        ax = plt.subplots()[1]
        matrix = np.array([[-2., np.nan], [.5, 1.2]])
        image = scientific_heatmap(ax, matrix, ["Second", "First"], ["T2", "T1"], limits=(-3, 3), center=0)
        np.testing.assert_array_equal(image.get_array().filled(np.nan), matrix)
        self.assertEqual([x.get_text() for x in ax.get_yticklabels()], ["Second", "First"])
        self.assertEqual(image.norm(0), .5)
        self.assertEqual(sum(x.get_text() == "NA" for x in ax.texts), 1)
        with self.assertRaises(ValueError):
            scientific_heatmap(ax, matrix, ["Second", "First"], ["T2", "T1"], limits=(-1, 1), center=0)

    def test_raw_points_and_actual_time_coordinates_retained(self):
        ax = plt.subplots()[1]
        raw_groups(ax, [[2, 2, 3, 99], [4, 5, 6]], ["A", "B"], ["gray", "blue"])
        self.assertEqual(sum(len(c.get_offsets()) for c in ax.collections), 7)
        line = interval_trajectory(ax, [10, 0, 4], [5, 1, 3], [4, .5, 2], [6, 1.5, 4], color="blue")
        np.testing.assert_array_equal(line.get_xdata(), [0, 4, 10])
        np.testing.assert_array_equal(line.get_ydata(), [1, 3, 5])
        with self.assertRaises(ValueError):
            component_matrix(ax, [[0, 2], [1, 0]])

    def test_physical_axes_geometry(self):
        fig = canvas((180, 100)); ax = axes_mm(fig, 20, 10, 40, 30)
        np.testing.assert_allclose(ax.get_position().bounds, [20/180, .6, 40/180, .3])
        with self.assertRaises(ValueError):
            axes_mm(fig, 170, 10, 40, 30)

    def test_print_tick_ink_is_independent_of_muted_structural_marks(self):
        from project_style import role, current_project
        from matplotlib.colors import to_rgba
        with figure_style():
            fig, ax = plt.subplots()
            ax.plot([0,1],[0,1]);fig.canvas.draw()
            for tick in [*ax.get_xticklabels(),*ax.get_yticklabels()]:
                self.assertEqual(to_rgba(tick.get_color()),to_rgba(role('ink')))
                self.assertEqual(tick.get_fontsize(),current_project()['typography']['base_pt'])
            self.assertEqual(to_rgba(ax.xaxis.majorTicks[0].tick1line.get_color()),to_rgba(role('muted')))


if __name__ == "__main__":
    unittest.main()
