#!/usr/bin/python3 -u

import pathlib
import shutil
import threading
import time
import unittest

import heal

tmp = pathlib.Path("../test/tmp")

MODE_1 = {"if": "true", "then-mode": "mode_1"}
MODE_2 = {"if": "false", "then-mode": "mode_2"}
STEP_1 = {"if-not": "true", "and-if-mode": "mode_1", "then": "false"}
STEP_2 = {"if-not": "true", "and-if-mode": "mode_2", "then": "false"}
STEP_3 = {"if-not": "true", "then": "false"}
CONFIGURATION = [MODE_1, MODE_2, STEP_1, STEP_2, STEP_3]


class TestCase(unittest.TestCase):
    def setUp(self):
        if not tmp.is_dir():
            tmp.mkdir()

    def tearDown(self):
        # safety net: stops any remaining LoopThread at the end of each test, so that nothing gets stuck
        [thread.stop.set() for thread in threading.enumerate() if isinstance(thread, heal.LoopThread)]

        if tmp.is_dir():
            shutil.rmtree(tmp)

    def test_execute(self):
        self.assertTrue(heal.execute("/bin/true"))
        self.assertFalse(heal.execute("/bin/false"))

    def test_read_configuration(self):
        self.assertListEqual(list(heal.read_configuration("../test/read_configuration")), [MODE_1, MODE_2])

    def test_get_current_modes(self):
        self.assertListEqual(heal.get_current_modes(CONFIGURATION), ["mode_1"])

    def test_get_expected_steps(self):
        self.assertListEqual(heal.get_expected_steps(CONFIGURATION, ["mode_1"]), [STEP_1, STEP_3])

    def test_get_steps(self):
        self.assertListEqual(
            heal.get_steps([heal.StepThread(STEP_1), heal.StepThread(STEP_2), heal.StepThread(STEP_3)]),
            [STEP_1, STEP_2, STEP_3]
        )

    def test_get_current_threads(self):
        threads = [heal.StepThread(STEP_1), heal.StepThread(STEP_2), heal.StepThread(STEP_3)]

        for thread in threads:
            thread.start()
        self.assertListEqual(heal.get_steps(heal.get_current_threads()), [STEP_1, STEP_2, STEP_3])

        for thread in threads:
            thread.stop.set()
            thread.join()
        self.assertFalse(heal.get_current_threads())

    def test_stop_obsolete_threads(self):
        thread_1 = heal.StepThread(STEP_1)
        thread_1.start()
        thread_2 = heal.StepThread(STEP_2)
        thread_2.start()

        heal.stop_obsolete_threads([thread_1, thread_2], [STEP_1])
        time.sleep(.1)
        self.assertTrue(thread_1.is_alive())
        self.assertFalse(thread_2.is_alive())

        heal.stop_obsolete_threads([thread_1], [])
        time.sleep(.1)
        self.assertFalse(thread_1.is_alive())

    def test_start_missing_steps(self):
        self.assertFalse(heal.get_current_threads())

        heal.start_missing_steps([], [STEP_1])
        current_threads = heal.get_current_threads()
        self.assertEqual(len(current_threads), 1)
        thread_1 = current_threads[0]
        self.assertEqual(thread_1.step, STEP_1)

        heal.start_missing_steps([thread_1], [STEP_1, STEP_2])
        current_threads = sorted(heal.get_current_threads(), key=lambda thread: str(thread.step))
        self.assertEqual(len(current_threads), 2)
        self.assertEqual(id(thread_1), id(current_threads[0]))
        self.assertEqual(current_threads[1].step, STEP_2)

    def test_stepthread_loop(self):
        for step in [{"if-not": "touch ../test/tmp/ok", "then": "false"},
                     {"if-not": "false", "then": "touch ../test/tmp/ko"}]:
            thread = heal.StepThread(step)
            thread.start()
            thread.stop.set()
            thread.join()

        self.assertTrue(tmp.joinpath("ok").is_file())
        self.assertTrue(tmp.joinpath("ko").is_file())


unittest.main(verbosity=2)
