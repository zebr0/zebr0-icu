#!/usr/bin/python3 -u

import argparse
import datetime
import json
import os.path
import subprocess

import sys
import yaml


def write_output(status):
    with open(args.output, "w") as output:
        json.dump({
            "utc": datetime.datetime.utcnow().isoformat(),
            "status": status,
            "modes": current_modes
        }, output, indent=2)


def execute(command):
    return subprocess.Popen(command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


argparser = argparse.ArgumentParser(description="Minimalist self-healing.")
argparser.add_argument("-d", "--directory", default="/etc/heal.conf.d", help="path to the yaml or json configuration directory (default: /etc/heal.conf.d)")
argparser.add_argument("-o", "--output", default="/var/tmp/status.json", help="path to the output status file (default: /var/tmp/status.json)")
args = argparser.parse_args()

steps = []
modes = []

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
