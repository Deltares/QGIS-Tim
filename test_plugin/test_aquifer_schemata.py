from unittest import TestCase

from qgistim.core.elements.aquifer import AquiferSchema


class TestAquiferSchema(TestCase):
    def test_validate(self):
        schema = AquiferSchema()
        data = {
            "layer": [0],
            "aquifer_top": [10.0],
            "aquifer_bottom": [0.0],
            "aquitard_c": [None],
            "aquifer_k": [5.0],
            "semiconf_top": [None],
            "semiconf_head": [None],
        }
        self.assertEqual(schema.validate_timml(data), {})

    def test_validate_empty(self):
        schema = AquiferSchema()
        data = {}
        self.assertEqual(schema.validate_timml(data), {"Table:": ["Table is empty."]})

    def test_validate_two_layer(self):
        schema = AquiferSchema()
        data = {
            "layer": [0, 1],
            "aquifer_top": [10.0, -5.0],
            "aquifer_bottom": [0.0, -15.0],
            "aquitard_c": [None, 100.0],
            "aquifer_k": [5.0, 10.0],
            "semiconf_top": [None],
            "semiconf_head": [None],
        }
        self.assertEqual(schema.validate_timml(data), {})

    def test_validate_two_layer_invalid(self):
        schema = AquiferSchema()
        data = {
            "layer": [0, 1],
            "aquifer_top": [10.0, -5.0],
            "aquifer_bottom": [0.0, -15.0],
            "aquitard_c": [None, None],
            "aquifer_k": [5.0, 10.0],
            "semiconf_top": [None],
            "semiconf_head": [None],
        }
        expected = {"aquitard_c": ["No values provided at row(s): 2"]}
        self.assertEqual(schema.validate_timml(data), expected)

    def test_validate_two_layer_consistency(self):
        schema = AquiferSchema()
        data = {
            "layer": [0, 1],
            "aquifer_top": [9.0, -15.0],
            "aquifer_bottom": [10.0, -5.0],
            "aquitard_c": [None, 10.0],
            "aquifer_k": [5.0, 10.0],
            "semiconf_top": [None],
            "semiconf_head": [None],
        }
        expected = {
            "Table:": [
                "aquifer_top is not greater or equal to aquifer_bottom at row(s): 1, 2"
            ]
        }
        self.assertEqual(schema.validate_timml(data), expected)
