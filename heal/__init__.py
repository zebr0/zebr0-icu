import argparse
import functools
import pathlib
import signal
import subprocess
import threading
from pathlib import Path

from heal.util import ENCODING, write_file, do_nothing, is_file_ko
from heal.watch import Watcher


def try_checks(checks, delay=10, update_status=do_nothing):
    for i, check in enumerate(checks):
        test = check.get("check")
        cp = subprocess.run(test, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        if cp.returncode == 0:
            continue

        fix, rank = check.get("fix"), check.get("rank")
        print(f"[{rank}] failed({cp.returncode}): {test}")
        for line in cp.stdout.splitlines():
            print(f"[{rank}] output: {line}")

        print(f"[{rank}] fixing: {fix}")
        update_status("fixing")

        sp = subprocess.Popen(fix, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        threading.Thread(target=lambda: [print(f"[{rank}] output: {line}", end="") for line in sp.stdout]).start()

        while True:
            try:
                if sp.wait(delay) != 0:
                    print(f"[{rank}] warning! fix returned code {sp.returncode}")
                break
            except subprocess.TimeoutExpired:
                try_checks(checks[:i], delay)

        cp = subprocess.run(test, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        if cp.returncode != 0:
            print(f"[{rank}] failed({cp.returncode}): {test}")
            for line in cp.stdout.splitlines():
                print(f"[{rank}] output: {line}")
            raise ChildProcessError()

        print(f"[{rank}] fix successful")

    update_status("ok")


def heal(directory: Path, file, event, delay=10):
    if is_file_ko(file):
        print("system already in failed status, exiting")
        return

    if not directory.is_dir():
        print("directory must exist")
        return

    print("watching configuration directory:", directory)
    watcher = Watcher(directory)

    try:
        while True:
            try_checks(watcher.refresh_current_checks_if_necessary(), delay, functools.partial(write_file, file, watcher.current_modes))
            if event.wait(delay):
                break
    except ChildProcessError:
        write_file(file, watcher.current_modes, "ko")
        print("critical failure, exiting")


def main(args=None):
    argparser = argparse.ArgumentParser(description="")
    argparser.add_argument("-d", "--directory", type=pathlib.Path, default=pathlib.Path("/etc/heald"), help="")
    argparser.add_argument("-f", "--file", type=pathlib.Path, default=pathlib.Path("/var/heald/status.json"), help="")
    argparser.add_argument("-t", "--time", type=float, default=10, help="")
    args = argparser.parse_args(args)

    event = threading.Event()

    # handles signals properly
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda signum, frame: event.set())

    heal(args.directory, args.file, event, args.time)
