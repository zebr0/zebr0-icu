import datetime
import json
import os.path
import subprocess
import threading

import sys
import yaml


def execute(command):
    return subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


def read(directory):
    for filename in os.listdir(directory):
        with open(os.path.join(directory, filename)) as file:
            yield from yaml.load(file, Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings


def get_current_modes(items):
    return [item.get("then-mode") for item in items
            if item.get("then-mode")  # modes
            and execute(item.get("if"))]


def get_current_steps(items, modes):
    return [item for item in items
            if not item.get("then-mode")  # steps
            and (not item.get("and-if-mode") or item.get("and-if-mode") in modes)]


def split(items):
    steps, modes = [], []

    for item in items:
        if item.get("then-mode"):
            modes.append(item)
        else:
            steps.append(item)

    return modes, steps


def blibli(directory, output):
    def write_output(status):
        with open(output, "w") as outputfile:
            json.dump({
                "utc": datetime.datetime.utcnow().isoformat(),
                "status": status,
                "modes": current_modes
            }, outputfile, indent=2)

    modes, steps = split(read(directory))

    current_modes = [mode.get("then-mode") for mode in modes if execute(mode.get("if"))]

    for step in steps:
        if_not = step.get("if-not")
        then = step.get("then")
        mode = step.get("and-if-mode")

        if not mode or mode in current_modes:
            print("test: " + if_not)
            if not execute(if_not):
                write_output("fixing")
                print("test failed! fix: " + then)
                execute(then)

                print("test again: " + if_not)
                if not execute(if_not):
                    write_output("ko")
                    print("fix failed!")
                    exit(1)

            write_output("ok")


class LoopThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop = threading.Event()

    def run(self):
        while not self.stop.is_set():
            self.loop()
            self.stop.wait(10)

    def loop(self):
        pass


class StepThread(LoopThread):
    def __init__(self):
        super().__init__()


class MasterThread(LoopThread):
    def __init__(self, configuration_directory, status_file):
        super().__init__()
        self.configuration_directory = configuration_directory
        self.status_file = status_file

    def loop(self):
        items = read(self.configuration_directory)
        modes = get_current_modes(items)
        steps = get_current_steps(items, modes)
