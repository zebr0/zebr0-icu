import datetime
import json
import os.path
import subprocess

import sys
import yaml


def execute(command):
    return subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


steps = []
modes = []


def blibli(args):
    def write_output(status):
        with open(args.output, "w") as output:
            json.dump({
                "utc": datetime.datetime.utcnow().isoformat(),
                "status": status,
                "modes": current_modes
            }, output, indent=2)

    if os.path.isdir(args.directory):
        for filename in sorted(os.listdir(args.directory)):
            with open(os.path.join(args.directory, filename)) as file:
                for item in yaml.load(file, Loader=yaml.BaseLoader):  # uses the yaml baseloader to preserve all strings
                    if item.get("then-mode"):
                        modes.append(item)
                    else:
                        steps.append(item)

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
