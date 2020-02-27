#!/usr/bin/python3 -u

import unittest

import heal


class TestCase(unittest.TestCase):
    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))


unittest.main(verbosity=2)
