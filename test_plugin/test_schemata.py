from unittest import TestCase

from qgistim.core import schemata
from qgistim.core.schemata import (
    AllOrNone,
    Optional,
    Positive,
    Required,
    ValidationError,
    Xor,
)


class TestDiscardNone(TestCase):
    def test_discard(self):
        actual = schemata.discard_none([1, 2])
        self.assertTrue(actual == [1, 2])

        actual = schemata.discard_none([None, 1, None, 2, None])
        self.assertTrue(actual == [1, 2])


class TestPositive(TestCase):
    def test_positive(self):
        with self.assertRaises(ValidationError):
            Positive().validate(-1)
        Positive().validate(0)
        Positive().validate(1)


class TestOptional(TestCase):
    def test_optional(self):
        Optional(Positive()).validate(None)
        with self.assertRaises(ValidationError):
            Optional(Positive()).validate(-1)
        Optional(Positive()).validate(0)
        Optional(Positive()).validate(1)


class TestRequired(TestCase):
    def test_required(self):
        with self.assertRaises(ValidationError):
            Required(Positive()).validate(None)
        with self.assertRaises(ValidationError):
            Required(Positive()).validate(-1)
        Required(Positive()).validate(0)
        Required(Positive()).validate(1)
