import datetime
import enum
import functools
import http.server
import json
import os.path
import socketserver
import subprocess
import threading

import yaml


class StoppableThread(threading.Thread):
    def stop(self):
        pass


class LoopThread(StoppableThread):
    def __init__(self, delay):
        super().__init__()
        self.event_stop = threading.Event()
        self.delay = delay

    def run(self):
        while not self.event_stop.is_set():
            self.loop()
            self.event_stop.wait(self.delay)

    def stop(self):
        self.event_stop.set()

    def loop(self):
        pass


class Status(int, enum.Enum):
    OK = 0
    FIXING = 1
    KO = 2


run = functools.partial(subprocess.run, shell=True)


class StepThread(LoopThread):
    def __init__(self, step):
        super().__init__(step.get("delay", 10))
        self.step = step
        self.status = Status.OK

    def loop(self):
        if run(self.step.get("if-not")).returncode != 0:
            self.status = Status.FIXING
            if run(self.step.get("then")).returncode != 0 or run(self.step.get("if-not")).returncode != 0:
                self.status = Status.KO
            else:
                self.status = Status.OK
        else:
            self.status = Status.OK


def read_configuration(directory):
    result = []
    for filename in os.listdir(directory):
        with open(os.path.join(directory, filename)) as file:
            result.extend(yaml.load(file, Loader=yaml.BaseLoader))  # uses the yaml baseloader to preserve all strings
    return result


def get_current_modes(configuration):
    return [item.get("then-mode") for item in configuration
            if item.get("then-mode")  # modes
            and run(item.get("if")).returncode == 0]


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


class MasterThread(LoopThread):
    def __init__(self, configuration_directory):
        super().__init__(30)
        self.configuration_directory = configuration_directory
        self.current_modes = []

    def loop(self):
        configuration = read_configuration(self.configuration_directory)
        self.current_modes = get_current_modes(configuration)
        expected_steps = get_expected_steps(configuration, self.current_modes)
        converge_threads(expected_steps)


def shutdown(*_):
    # first ensure that any masterthread is stopped so that it can't create new threads
    for thread in threading.enumerate():
        if isinstance(thread, MasterThread):
            thread.stop()
            thread.join()

    # then stop the remaining threads
    [thread.stop() for thread in threading.enumerate() if isinstance(thread, StoppableThread)]


def get_status_from_threads():
    # returns the name of the most critical status amongst the running stepthreads
    return max((thread.status for thread in threading.enumerate() if isinstance(thread, StepThread)), default=Status.OK).name


def get_current_modes_from_threads():
    # there should be only one masterthread amongst the running threads
    return next((thread.current_modes for thread in threading.enumerate() if isinstance(thread, MasterThread)), [])


class HTTPServerThread(StoppableThread):
    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "utc": datetime.datetime.utcnow().isoformat(),
                "status": get_status_from_threads(),
                "modes": get_current_modes_from_threads()
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
