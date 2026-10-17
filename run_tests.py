"""Run the offline test suite from any working directory."""

from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "agents"))
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
