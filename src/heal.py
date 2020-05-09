import datetime
import enum
import http.server
import json
import os.path
import socketserver
import subprocess
import sys
import threading

import yaml


class Status(enum.IntEnum):
    OK = 0
    FIXING = 1
    KO = 2


def execute(command):
    return subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


def read_configuration(directory):
    for filename in os.listdir(directory):
        with open(os.path.join(directory, filename)) as file:
            yield from yaml.load(file, Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings


def get_current_modes(configuration):
    return [item.get("then-mode") for item in configuration
            if item.get("then-mode")  # modes
            and execute(item.get("if"))]


def get_expected_steps(configuration, current_modes):
    return [item for item in configuration
            if not item.get("then-mode")  # steps
            and (not item.get("and-if-mode") or item.get("and-if-mode") in current_modes)]


def converge_threads(expected_steps):
    current_steps = []

    # stop obsolete threads
    for thread in threading.enumerate():
        if isinstance(thread, StepThread):
            if thread.step not in expected_steps:
                thread.stop()
            else:
                current_steps.append(thread.step)

    # start missing steps
    [StepThread(step).start() for step in expected_steps if step not in current_steps]


def compute_thread_status():
    return max((thread.status for thread in threading.enumerate() if isinstance(thread, StepThread)), default=Status.OK).name


class StoppableThread(threading.Thread):
    def stop(self):
        pass


class HTTPServerThread(StoppableThread):
    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "utc": datetime.datetime.utcnow().isoformat(),
                "status": compute_thread_status(),
                "modes": None
            }).encode("utf-8"))

    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        def __init__(self):
            super().__init__(("127.0.0.1", 8000), HTTPServerThread.RequestHandler)

    def __init__(self):
        super().__init__()
        self.server = HTTPServerThread.ThreadingHTTPServer()

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class LoopThread(StoppableThread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            self.loop()
            self._stop_event.wait(10)

    def stop(self):
        self._stop_event.set()

    def loop(self):
        pass


class StepThread(LoopThread):
    def __init__(self, step):
        super().__init__()
        self.step = step
        self.status = Status.OK

    def loop(self):
        if not execute(self.step.get("if-not")):
            self.status = Status.FIXING
            if not execute(self.step.get("then")) or not execute(self.step.get("if-not")):
                self.status = Status.KO
            else:
                self.status = Status.OK
        else:
            self.status = Status.OK


class MasterThread(LoopThread):
    def __init__(self, configuration_directory, status_file):
        super().__init__()
        self.configuration_directory = configuration_directory
        self.status_file = status_file

    def loop(self):
        # todo: look for changes in the configuration directory
        configuration = read_configuration(self.configuration_directory)
        current_modes = get_current_modes(configuration)
        expected_steps = get_expected_steps(configuration, current_modes)
        converge_threads(expected_steps)
