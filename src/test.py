#!/usr/bin/python3 -u

import unittest

import heal

CONFIGURATION = [{"if": "true", "then-mode": "mode_1"},
                 {"if": "false", "then-mode": "mode_2"},
                 {"if-not": "echo 'default' >> tmp/modes", "then": "false"},
                 {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"},
                 {"if-not": "echo 'mode_2' >> tmp/modes", "and-if-mode": "mode_2", "then": "false"}]


class TestCase(unittest.TestCase):
    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))

    def test_read_configuration(self):
        self.assertListEqual(list(heal.read_configuration("../test/modes")), CONFIGURATION)

    def test_get_current_modes(self):
        self.assertListEqual(heal.get_current_modes(CONFIGURATION), ["mode_1"])

    def test_get_expected_steps(self):
        self.assertListEqual(heal.get_expected_steps(CONFIGURATION, ["mode_1"]),
                             [{"if-not": "echo 'default' >> tmp/modes", "then": "false"},
                              {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"}])


unittest.main(verbosity=2)
