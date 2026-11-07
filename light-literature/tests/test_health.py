from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from litsearch.health import health_weights, load_health, update_health


class HealthTests(unittest.TestCase):
    def test_health_scores_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs = [
                {"source": "openalex", "status": "ok"},
                {"source": "openalex", "status": "ok"},
                {"source": "doaj", "status": "blocked"},
            ]
            state = update_health(Path(tmp), runs)
            self.assertGreaterEqual(state["openalex"]["score"], 90)
            self.assertLessEqual(state["doaj"]["score"], 50)
            weights = health_weights(state)
            self.assertGreater(weights["openalex"], weights["doaj"])
            self.assertEqual(load_health(Path(tmp))["openalex"]["runs"], 2)


if __name__ == "__main__":
    unittest.main()
