#!/usr/bin/python3 -u

import json
import pathlib
import shutil
import threading
import time
import unittest
import urllib.request

import dateutil.parser

import heal

tmp = pathlib.Path("../test/tmp")

MODE_1 = {"if": "true", "then-mode": "mode_1"}
MODE_2 = {"if": "false", "then-mode": "mode_2"}
STEP_1 = {"if-not": "true", "and-if-mode": "mode_1", "then": "false"}
STEP_2 = {"if-not": "true", "and-if-mode": "mode_2", "then": "false"}
STEP_3 = {"if-not": "true", "then": "false"}
CONFIGURATION = [MODE_1, MODE_2, STEP_1, STEP_2, STEP_3]


def _get_current_threads():
    return sorted((thread for thread in threading.enumerate() if isinstance(thread, heal.StepThread)), key=lambda thread: str(thread.step))


class TestCase(unittest.TestCase):
    def setUp(self):
        if not tmp.is_dir():
            tmp.mkdir()

    def tearDown(self):
        # safety net: stops any remaining LoopThread at the end of each test, so that nothing gets stuck
        for thread in threading.enumerate():
            if isinstance(thread, heal.StoppableThread):
                thread.stop()
                thread.join()

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

    def test_converge_threads(self):
        self.assertFalse(_get_current_threads())

        heal.converge_threads([STEP_1])
        current_threads = _get_current_threads()
        self.assertEqual(len(current_threads), 1)
        thread_1 = current_threads[0]
        self.assertEqual(thread_1.step, STEP_1)

        heal.converge_threads([STEP_1, STEP_2])
        current_threads = _get_current_threads()
        self.assertEqual(len(current_threads), 2)
        self.assertEqual(id(thread_1), id(current_threads[0]))
        thread_2 = current_threads[1]
        self.assertEqual(thread_2.step, STEP_2)

        heal.converge_threads([STEP_2])
        time.sleep(.1)
        current_threads = _get_current_threads()
        self.assertEqual(len(current_threads), 1)
        self.assertEqual(id(thread_2), id(current_threads[0]))

        heal.converge_threads([])
        time.sleep(.1)
        self.assertFalse(_get_current_threads())

    def test_compute_thread_status(self):
        self.assertEqual(heal.compute_thread_status(), "OK")

        heal.StepThread({"if-not": "true", "then": "false"}).start()
        time.sleep(.1)
        self.assertEqual(heal.compute_thread_status(), "OK")

        heal.StepThread({"if-not": "false", "then": "sleep 1"}).start()
        time.sleep(.1)
        self.assertEqual(heal.compute_thread_status(), "FIXING")

        heal.StepThread({"if-not": "false", "then": "false"}).start()
        time.sleep(.1)
        self.assertEqual(heal.compute_thread_status(), "KO")

    def test_httpserverthread(self):
        for _ in range(2):  # twice to check that the socket closes alright
            thread = heal.HTTPServerThread()
            thread.start()
            time.sleep(.1)
            self.assertTrue(thread.is_alive())
            thread.stop()
            thread.join()
            self.assertFalse(thread.is_alive())

    def test_httpserverthread_get(self):
        heal.HTTPServerThread().start()

        with urllib.request.urlopen("http://127.0.0.1:8000") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.info().get_content_type(), "application/json")

            response_json = json.load(response)
            dateutil.parser.parse(response_json.get("utc"))
            self.assertEqual(response_json.get("status"), "OK")
            self.assertEqual(response_json.get("modes"), None)

    def test_stepthread_execute(self):
        for step in [{"if-not": "touch ../test/tmp/if-not", "then": "false"},
                     {"if-not": "false", "then": "touch ../test/tmp/then"}]:
            thread = heal.StepThread(step)
            thread.start()
            time.sleep(.1)
            thread.stop()
            thread.join()

        self.assertTrue(tmp.joinpath("if-not").is_file())
        self.assertTrue(tmp.joinpath("then").is_file())

    # todo: test_stepthread_loop

    def test_stepthread_status_default_then_ok(self):
        thread = heal.StepThread({"if-not": "sleep 1", "then": "false"})
        thread.start()
        time.sleep(.5)
        self.assertEqual(thread.status, heal.Status.OK)
        thread.stop()
        thread.join()
        self.assertEqual(thread.status, heal.Status.OK)

    def test_stepthread_status_fixing_then_ok(self):
        thread = heal.StepThread({"if-not": "test -f ../test/tmp/fixing_ok", "then": "sleep 1 && touch ../test/tmp/fixing_ok"})
        thread.start()
        time.sleep(.5)
        self.assertEqual(thread.status, heal.Status.FIXING)
        thread.stop()
        thread.join()
        self.assertEqual(thread.status, heal.Status.OK)

    def test_stepthread_status_fixing_then_ko(self):
        thread = heal.StepThread({"if-not": "test -f ../test/tmp/fixing_ko", "then": "sleep 1 && touch ../test/tmp/fixing_ko && false"})
        thread.start()
        time.sleep(.5)
        self.assertEqual(thread.status, heal.Status.FIXING)
        thread.stop()
        thread.join()
        self.assertEqual(thread.status, heal.Status.KO)

    def test_stepthread_status_still_ko(self):
        thread = heal.StepThread({"if-not": "false", "then": "sleep 1"})
        thread.start()
        time.sleep(.5)
        self.assertEqual(thread.status, heal.Status.FIXING)
        thread.stop()
        thread.join()
        self.assertEqual(thread.status, heal.Status.KO)

    # todo: test_masterthread
    # todo: full tests


unittest.main(verbosity=2)
