import unittest

from indian_numbers import format_inr


class FormatInr(unittest.TestCase):
    def test_small_amounts_need_no_grouping(self):
        self.assertEqual(format_inr(0), "₹0.00")
        self.assertEqual(format_inr(99900), "₹999.00")

    def test_thousands(self):
        self.assertEqual(format_inr(123456), "₹1,234.56")

    def test_lakh(self):
        self.assertEqual(format_inr(10000000), "₹1,00,000.00")

    def test_crore(self):
        self.assertEqual(format_inr(1234567890), "₹1,23,45,678.90")

    def test_negative(self):
        self.assertEqual(format_inr(-10000000), "-₹1,00,000.00")

    def test_rejects_floats_and_bools(self):
        for bad in (10.5, True):
            with self.assertRaises(TypeError):
                format_inr(bad)


if __name__ == "__main__":
    unittest.main()
