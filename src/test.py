#!/usr/bin/python3 -u

import unittest

import heal

RAW_ITEMS = [{"if": "true", "then-mode": "mode_1"},
             {"if": "false", "then-mode": "mode_2"},
             {"if-not": "echo 'default' >> tmp/modes", "then": "false"},
             {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"},
             {"if-not": "echo 'mode_2' >> tmp/modes", "and-if-mode": "mode_2", "then": "false"}]


class TestCase(unittest.TestCase):
    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))

    def test_read(self):
        self.assertListEqual(list(heal.read("../test/modes")), RAW_ITEMS)

    def test_get_current_modes(self):
        self.assertListEqual(heal.get_current_modes(RAW_ITEMS), ["mode_1"])

    def test_get_current_steps(self):
        self.assertListEqual(heal.get_current_steps(RAW_ITEMS, ["mode_1"]), [
            {"if-not": "echo 'default' >> tmp/modes", "then": "false"},
            {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"}
        ])


unittest.main(verbosity=2)
