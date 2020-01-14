import unittest
from limaju import deliberate, plot_merit_profile, load_mentions_from_string


class TestLimaju(unittest.TestCase):

    test_mentions_array = [
        u'EXCELLENT',
        u'VERY GOOD',
        u'GOOD',
        u'SOMEWHAT GOOD',
        u'PASSABLE',
        u'POOR',
        u'REJECT',
    ]

    test_mentions = """
        EXCELLENT
        VERY GOOD
        GOOD
        SOMEWHAT GOOD
        PASSABLE
        POOR
        REJECT
    """

    def test_run_with_array(self):
        deliberation, tally = deliberate([
            ['A', 'B', 'C'],
            ['POOR', 'GOOD', 'REJECT'],
            ['EXCELLENT', 'GOOD', 'EXCELLENT'],
        ], self.test_mentions_array)

        self.assertEqual(deliberation, ['B', 'A', 'C'])

    def test_dumb_deliberation_with_one_candidate(self):
        deliberation, tally = deliberate(u"""
A
PASSABLE
EXCELLENT
        """, self.test_mentions)

        self.assertEqual(deliberation, ['A'])

    def test_deliberation_with_one_judge(self):
        deliberation, tally = deliberate(u"""
A, B, C, D
REJECT, PASSABLE, POOR, GOOD
        """, self.test_mentions)

        self.assertEqual(deliberation, ['D', 'B', 'C', 'A'])

    def test_deliberation_with_two_judges(self):
        deliberation, tally = deliberate(u"""
A, B, C
POOR, GOOD, REJECT
EXCELLENT, GOOD, EXCELLENT
        """, self.test_mentions)

        self.assertEqual(deliberation, ['B', 'A', 'C'])

    def test_deliberation_with_same_median_mention(self):
        deliberation, tally = deliberate(u"""
A, B, C, D
POOR, GOOD, REJECT, PASSABLE
EXCELLENT, EXCELLENT, EXCELLENT, EXCELLENT
EXCELLENT, EXCELLENT, EXCELLENT, EXCELLENT
        """, self.test_mentions)

        self.assertEqual(deliberation, ['B', 'D', 'A', 'C'])


    def test_plotting_deliberation(self):
        mentions = load_mentions_from_string(self.test_mentions)
        judgments = ''
        with open("examples/judgments_01.csv") as sample:
            judgments = "".join(sample.readlines())
        deliberation, tally = deliberate(judgments, self.test_mentions)

        plot_merit_profile(tally, deliberation, mentions, filename="test_plot.png")
        # self.assertEqual(deliberation, ['B', 'D', 'A', 'C'])


    # def test_raise(self):
    #     with self.assertRaises(TypeError):
    #         s.split(2)


if __name__ == '__main__':
    unittest.main()
