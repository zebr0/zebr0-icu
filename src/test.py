#!/usr/bin/python3 -u

import unittest

import heal


class TestCase(unittest.TestCase):
    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))

    def test_read(self):
        self.assertListEqual(list(heal.read("../test/modes")),
                             [{"if": "true", "then-mode": "mode_1"},
                              {"if": "false", "then-mode": "mode_2"},
                              {"if-not": "echo 'default' >> tmp/modes", "then": "false"},
                              {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"},
                              {"if-not": "echo 'mode_2' >> tmp/modes", "and-if-mode": "mode_2", "then": "false"}])


unittest.main(verbosity=2)
