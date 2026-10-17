import unittest

from personal_assistant.tools import analyze_text, calculate


class ToolTests(unittest.TestCase):
    def test_percent_and_compound_interest(self):
        self.assertEqual(calculate("25000 * 18 / 100")["result"], 4500)
        self.assertEqual(calculate("50000 * 18 / 100")["result"], 9000)
        self.assertAlmostEqual(calculate("10000 * (1 + 8/100)**2 - 10000")["result"], 1664)

    def test_precedence_and_unary(self):
        self.assertEqual(calculate("-3 + 2 * (8 - 1)")["result"], 11)
        self.assertEqual(calculate("10 // 3 + 10 % 3")["result"], 4)

    def test_invalid_or_unsafe_input(self):
        for expression in ("1/0", "2+", "True", "abs(-4)", "x + 1",
                           "__import__('os').getcwd()", "2 ** 1000000", "1e309",
                           "(-1)**0.5", "", "5" * 501):
            with self.subTest(expression=expression[:40]):
                self.assertEqual(calculate(expression)["status"], "error")

    def test_workshop_text(self):
        result = analyze_text("Google ADK helps developers build AI agents.")
        self.assertEqual((result["character_count"], result["word_count"],
                          result["sentence_count"]), (44, 7, 1))

    def test_text_edge_cases(self):
        for text, words, sentences in (("", 0, 0), ("  \n ", 0, 0), ("...?!", 0, 0),
                                       ("Hi!  Ready? Yes", 3, 3),
                                       ("One\ntwo. Three?!", 3, 2),
                                       ("don't stop", 2, 1)):
            with self.subTest(text=text):
                result = analyze_text(text)
                self.assertEqual(result["character_count"], len(text))
                self.assertEqual(result["word_count"], words)
                self.assertEqual(result["sentence_count"], sentences)


if __name__ == "__main__":
    unittest.main()
