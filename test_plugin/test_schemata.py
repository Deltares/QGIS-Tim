from unittest import TestCase

from qgistim.core import schemata
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllOptional,
    AllOrNone,
    AllRequired,
    Decreasing,
    FirstOnly,
    Increasing,
    Membership,
    NotBoth,
    OffsetAllRequired,
    Optional,
    Positive,
    Range,
    Required,
    SemiConfined,
    SingleRow,
    StrictlyDecreasing,
    StrictlyIncreasing,
)


class TestDiscardNone(TestCase):
    def test_discard(self):
        actual = schemata.discard_none([1, 2])
        self.assertTrue(actual == [1, 2])

        actual = schemata.discard_none([None, 1, None, 2, None])
        self.assertTrue(actual == [1, 2])


class TestPositive(TestCase):
    def test_positive(self):
        self.assertEqual(Positive().validate(-1), "Non-positive value: -1")
        self.assertIsNone(Positive().validate(0))
        self.assertIsNone(Positive().validate(1))


class TestOptional(TestCase):
    def test_optional(self):
        self.assertIsNone(Optional(Positive()).validate(None))
        self.assertIsNone(Optional(Positive()).validate(0))
        self.assertIsNone(Optional(Positive()).validate(1))
        self.assertEqual(Optional(Positive()).validate(-1), ["Non-positive value: -1"])


class TestRequired(TestCase):
    def test_required(self):
        self.assertEqual(Required(Positive()).validate(None), "a value is required.")
        self.assertEqual(Required(Positive()).validate(-1), ["Non-positive value: -1"])
        self.assertIsNone(Required(Positive()).validate(0))
        self.assertIsNone(Required(Positive()).validate(1))


class TestAllOrNone(TestCase):
    def test_all_or_none(self):
        schema = AllOrNone("a", "b", "c")
        d = {"a": None, "b": None, "c": None}
        self.assertIsNone(schema.validate(d))
        d = {"a": 1, "b": 2, "c": 3}
        self.assertIsNone(schema.validate(d))
        d = {"a": None, "b": 2, "c": 3}
        expected = (
            "Exactly all or none of the following variables must be provided: a, b, c"
        )
        self.assertEqual(schema.validate(d), expected)


class TestNotBoth(TestCase):
    def test_not_both(self):
        schema = NotBoth("a", "b")
        d = {"a": None, "b": None}
        self.assertIsNone(schema.validate(d))
        d = {"a": 1, "b": None}
        self.assertIsNone(schema.validate(d))
        d = {"a": None, "b": 1}
        self.assertIsNone(schema.validate(d))
        d = {"a": 1, "b": 1}
        self.assertEqual(
            schema.validate(d), "Either a or b should be provided, not both."
        )


class TestMembership(TestCase):
    def test_membership(self):
        schema = Membership("model layers")
        other = {"model layers": [1, 2, 3]}
        self.assertIsNone(schema.validate(None, other))
        self.assertIsNone(schema.validate(1, other))
        self.assertEqual(
            schema.validate(0, other), "Value 0 not found in model layers: 1, 2, 3"
        )


class TestAllRequired(TestCase):
    def test_all_required(self):
        schema = AllRequired(Positive())
        self.assertIsNone(schema.validate([1, 2, 3]))
        self.assertEqual(
            schema.validate([None, 2, None]), ["No values provided at row(s): 1, 3"]
        )
        self.assertEqual(schema.validate([1, 2, -1]), ["Non-positive value: -1"])


class TestOffsetAllRequired(TestCase):
    def test_offset_all_required(self):
        schema = OffsetAllRequired(Positive())
        self.assertIsNone(schema.validate([None, 2, 3]))
        self.assertEqual(
            schema.validate([None, 2, None]), ["No values provided at row(s): 3"]
        )
        self.assertEqual(schema.validate([None, 2, -1]), ["Non-positive value: -1"])


class TestAllOptional(TestCase):
    def test_all_optional(self):
        schema = AllOptional(Positive())
        self.assertIsNone(schema.validate([None, None, None]))
        self.assertIsNone(schema.validate([1, 2, 3]))
        self.assertEqual(schema.validate([-1, 2, 3]), ["Non-positive value: -1"])

    def test_all_optional_first_only(self):
        schema = AllOptional(FirstOnly())
        self.assertIsNone(schema.validate([None, None, None]))
        self.assertIsNone(schema.validate([1, None, None]))
        self.assertEqual(
            schema.validate([1, 1, None]), ["Only the first value may be filled in."]
        )

    def test_all_optional_first_only_positive(self):
        schema = AllOptional(FirstOnly(Positive()))
        self.assertIsNone(schema.validate([None, None, None]))
        self.assertIsNone(schema.validate([1, None, None]))
        self.assertEqual(
            schema.validate([1, 1, None]), ["Only the first value may be filled in."]
        )
        self.assertEqual(schema.validate([-1, None, None]), ["Non-positive value: -1"])


class TestRange(TestCase):
    def test_range(self):
        schema = Range()
        self.assertIsNone(schema.validate([0, 1, 2, 3]))
        self.assertEqual(
            schema.validate([1, 2, 3]), "Expected 0, 1, 2; received 1, 2, 3"
        )


class TestIncreasing(TestCase):
    def test_increasing(self):
        schema = Increasing()
        self.assertIsNone(schema.validate([0, 1, 2, 3]))
        self.assertIsNone(schema.validate([0, 1, 1, 2, 3]))
        self.assertEqual(
            schema.validate([1, 0, 2]), "Values are not increasing: 1, 0, 2"
        )


class TestStrictlyIncreasing(TestCase):
    def test_strictly_increasing(self):
        schema = StrictlyIncreasing()
        self.assertIsNone(schema.validate([0, 1, 2, 3]))
        self.assertEqual(
            schema.validate([1, 0, 2]),
            "Values are not strictly increasing (no repeated values): 1, 0, 2",
        )
        self.assertEqual(
            schema.validate([0, 1, 1, 2]),
            "Values are not strictly increasing (no repeated values): 0, 1, 1, 2",
        )


class TestDecreasing(TestCase):
    def test_decreasing(self):
        schema = Decreasing()
        self.assertIsNone(schema.validate([3, 2, 1, 0]))
        self.assertIsNone(schema.validate([3, 2, 2, 1, 1]))
        self.assertEqual(
            schema.validate([1, 0, 2]), "Values are not decreasing: 1, 0, 2"
        )


class TestStrictlyDecreasing(TestCase):
    def test_strictly_decreasing(self):
        schema = StrictlyDecreasing()
        self.assertIsNone(schema.validate([3, 2, 1, 0]))
        self.assertEqual(
            schema.validate([1, 0, 2]),
            "Values are not strictly decreasing (no repeated values): 1, 0, 2",
        )
        self.assertEqual(
            schema.validate([2, 1, 1, 0]),
            "Values are not strictly decreasing (no repeated values): 2, 1, 1, 0",
        )


class TestAllGreateEqual(TestCase):
    def test_all_greater_equal(self):
        schema = AllGreaterEqual("top", "bot")
        d = {"top": [1.0, 0.0], "bot": [0.0, -1.0]}
        self.assertIsNone(schema.validate(d))
        d = {"top": [0.0, -1.0], "bot": [0.0, -1.0]}
        self.assertIsNone(schema.validate(d))
        d = {"bot": [1.0, 0.0], "top": [0.0, -1.0]}
        expected = "top is not greater or equal to bot at row(s): 1, 2"
        self.assertEqual(schema.validate(d), expected)


class TestFirstOnly(TestCase):
    def test_first_only(self):
        schema = FirstOnly()
        self.assertIsNone(schema.validate([None, None]))
        self.assertIsNone(schema.validate([1, None]))
        self.assertEqual(
            schema.validate([1, 1]), "Only the first value may be filled in."
        )


class TestSemiConfined(TestCase):
    def test_semi_confined(self):
        schema = SemiConfined()
        d = {
            "aquifer_top": [0.0, 1.0],
            "aquitard_c": [1.0, None],
            "semiconf_top": [1.0, None],
            "semiconf_head": [1.0, None],
        }
        self.assertIsNone(schema.validate(d))
        d = {
            "aquifer_top": [0.0, 1.0],
            "aquitard_c": [None, None],
            "semiconf_top": [1.0, None],
            "semiconf_head": [1.0, None],
        }
        expected = (
            "To enable a semi-confined top, the first row must be fully "
            "filled in for aquitard_c, semiconf_top, semiconf_head. To disable semi-confined top, none "
            "of the values must be filled in. Found: None, 1.0, 1.0"
        )
        self.assertEqual(schema.validate(d), expected)

        d = {
            "aquifer_top": [0.0, 1.0],
            "aquitard_c": [1.0, None],
            "semiconf_top": [-1.0, None],
            "semiconf_head": [1.0, None],
        }
        self.assertEqual(
            schema.validate(d),
            "semiconf_top must be greater than first aquifer_top.",
        )


class TestSingleRow(TestCase):
    def test_single_row(self):
        schema = SingleRow()
        self.assertIsNone(schema.validate([{"a": 1}]))
        data = [{"a": 1}, {"a": 2}]
        self.assertEqual(schema.validate(data), "Table may contain only one row.")
