#!/usr/bin/python3 -u

import unittest

import heal

MODE_1 = {"if": "true", "then-mode": "mode_1"}
MODE_2 = {"if": "false", "then-mode": "mode_2"}
STEP_1 = {"if-not": "echo 'default' >> tmp/modes", "then": "false"}
STEP_2 = {"if-not": "echo 'mode_1' >> tmp/modes", "and-if-mode": "mode_1", "then": "false"}
STEP_3 = {"if-not": "echo 'mode_2' >> tmp/modes", "and-if-mode": "mode_2", "then": "false"}
CONFIGURATION = [MODE_1, MODE_2, STEP_1, STEP_2, STEP_3]


class TestCase(unittest.TestCase):
    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))

    def test_read_configuration(self):
        self.assertListEqual(list(heal.read_configuration("../test/modes")), CONFIGURATION)

    def test_get_current_modes(self):
        self.assertListEqual(heal.get_current_modes(CONFIGURATION), ["mode_1"])

    def test_get_expected_steps(self):
        self.assertListEqual(heal.get_expected_steps(CONFIGURATION, ["mode_1"]), [STEP_1, STEP_2])

    def test_get_steps(self):
        self.assertListEqual(
            heal.get_steps([heal.StepThread(STEP_1), heal.StepThread(STEP_2), heal.StepThread(STEP_3)]),
            [STEP_1, STEP_2, STEP_3]
        )

    def test_get_current_steps(self):
        threads = [heal.StepThread(STEP_1), heal.StepThread(STEP_2), heal.StepThread(STEP_3)]

        for thread in threads:
            thread.start()
        self.assertListEqual(heal.get_current_steps(), [STEP_1, STEP_2, STEP_3])

        for thread in threads:
            thread.stop.set()
            thread.join()
        self.assertListEqual(heal.get_current_steps(), [])


unittest.main(verbosity=2)
