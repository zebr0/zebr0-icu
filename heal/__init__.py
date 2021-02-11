import datetime
import enum
import http.server
import json
import pathlib
import socketserver
import subprocess
import threading

import yaml

import util

DELAY_DEFAULT = 10


class Status(int, enum.Enum):
    OK = 0
    FIXING = 1
    KO = 2


class StepThread(util.LoopThread):
    def __init__(self, step, delay_default=DELAY_DEFAULT):
        super().__init__(step.get("delay", delay_default))
        self.step = step
        self.uid = util.generate_uid(step)
        self.status = Status.OK

    def loop(self):
        if self.status != Status.OK or subprocess.run(self.step.get("if-not"), shell=True).returncode == 0:
            return

        print(self.uid, json.dumps(self.step))
        print(self.uid, "test failed, fixing")
        self.status = Status.FIXING

        sp = subprocess.Popen(self.step.get("then"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=util.ENCODING)
        for line in sp.stdout:
            print(self.uid, line.rstrip())
        if sp.wait() != 0:
            print(self.uid, "error!")

        if subprocess.run(self.step.get("if-not"), shell=True).returncode == 0:
            print(self.uid, "fixed")
            self.status = Status.OK
        else:
            print(self.uid, "test still failed: fatal error!")
            self.status = Status.KO


def read_configuration(directory: pathlib.Path):
    result = []
    for path in directory.iterdir():
        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding=util.ENCODING)
        except (OSError, ValueError) as e:
            print(e)
            continue

        load = yaml.load(text, Loader=yaml.BaseLoader)
        if not isinstance(load, list):
            print(f"error, {path} is not a proper yaml or json list")
            continue

        result.extend(load)  # uses the yaml baseloader to preserve all strings

    return result


def get_current_modes(configuration):
    return [item.get("then-mode") for item in configuration
            if item.get("then-mode")  # modes
            and subprocess.run(item.get("if"), shell=True).returncode == 0]


def get_expected_steps(configuration, current_modes):
    return [item for item in configuration
            if not item.get("then-mode")  # steps
            and (not item.get("and-if-mode") or item.get("and-if-mode") in current_modes)]


def converge_threads(expected_steps, delay_default=DELAY_DEFAULT):
    current_steps = []

    # stop obsolete threads
    for thread in threading.enumerate():
        if isinstance(thread, StepThread):
            if thread.step not in expected_steps:
                thread.stop()
            else:
                current_steps.append(thread.step)

    # start missing steps
    [StepThread(step, delay_default).start() for step in expected_steps if step not in current_steps]


class MasterThread(util.LoopThread):
    def __init__(self, configuration_directory, delay_default=DELAY_DEFAULT):
        super().__init__(30)
        self.configuration_directory = configuration_directory
        self.current_modes = []
        self.delay_default = delay_default

    def loop(self):
        configuration = read_configuration(self.configuration_directory)
        self.current_modes = get_current_modes(configuration)
        expected_steps = get_expected_steps(configuration, self.current_modes)
        converge_threads(expected_steps, self.delay_default)


def shutdown(*_):
    # first ensure that any masterthread is stopped so that it can't create new threads
    for thread in threading.enumerate():
        if isinstance(thread, MasterThread):
            thread.stop()
            thread.join()

    # then stop the remaining threads
    [thread.stop() for thread in threading.enumerate() if isinstance(thread, util.StoppableThread)]


def get_status_from_threads():
    # returns the name of the most critical status amongst the running stepthreads
    return max((thread.status for thread in threading.enumerate() if isinstance(thread, StepThread)), default=Status.OK).name


def get_current_modes_from_threads():
    # there should be only one masterthread amongst the running threads
    return next((thread.current_modes for thread in threading.enumerate() if isinstance(thread, MasterThread)), [])


class HTTPServerThread(util.StoppableThread):
    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "utc": datetime.datetime.utcnow().isoformat(),
                "status": get_status_from_threads(),
                "modes": get_current_modes_from_threads()
            }).encode(util.ENCODING))

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
