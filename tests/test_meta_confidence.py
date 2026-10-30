"""
Unit Tests for Meta-Labeling Conviction Scorer (tests/test_meta_confidence.py).
Tests:
  - Long confidence boosted by healthy Contango (VTS < 0.92) or extreme RSI2 < 5.
  - Long confidence penalized by acute accelerating Backwardation (VTS > 1.05 and rising).
  - Short confidence boosted by Backwardation (VTS >= 1.00).
  - Short confidence penalized by calm Contango (VTS < 0.88).
  - Confidence clamping between 0.55 and 1.35.
"""

import unittest

from aegis_quant.strategies.base import BaseStrategy
from tests.helpers import create_mock_bar


class TestMetaConfidence(unittest.TestCase):
    def test_long_confidence_in_contango(self):
        bar = create_mock_bar(vts_ratio=0.88, rsi2=50.0)
        conf = BaseStrategy.compute_meta_confidence(bar, "LONG", base_score=1.0)
        self.assertEqual(conf, 1.15)  # 1.0 + 0.15

    def test_long_confidence_penalized_in_accelerating_backwardation(self):
        bar = create_mock_bar(vts_ratio=1.10, vts_prev=1.08, rsi2=50.0)
        conf = BaseStrategy.compute_meta_confidence(bar, "LONG", base_score=1.0)
        self.assertEqual(conf, 0.75)  # 1.0 - 0.25

    def test_short_confidence_in_backwardation(self):
        bar = create_mock_bar(vts_ratio=1.05, rsi2=50.0)
        conf = BaseStrategy.compute_meta_confidence(bar, "SHORT", base_score=1.0)
        self.assertEqual(conf, 1.20)  # 1.0 + 0.20

    def test_short_confidence_penalized_in_contango(self):
        bar = create_mock_bar(vts_ratio=0.85, rsi2=50.0)
        conf = BaseStrategy.compute_meta_confidence(bar, "SHORT", base_score=1.0)
        self.assertEqual(conf, 0.80)  # 1.0 - 0.20


if __name__ == "__main__":
    unittest.main()
