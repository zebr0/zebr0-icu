import argparse
import functools
import pathlib
import signal
import subprocess
import threading
from pathlib import Path

from heal.util import SP_KWARGS, print_output, write, ignore, is_ko
from heal.watch import Watcher


def try_checks(checks, delay=10, update_status=ignore):
    for i, check in enumerate(checks):
        test = check.get("check")
        cp = subprocess.run(test, **SP_KWARGS)
        if cp.returncode == 0:
            continue

        rank = "[" + str(check.get("rank")) + "]"
        print_output(rank, "failed", test, cp.stdout.splitlines())

        update_status("fixing")
        fix = check.get("fix")
        sp = subprocess.Popen(fix, **SP_KWARGS)
        threading.Thread(target=print_output, args=(rank, "fixing", fix, sp.stdout)).start()
        while True:
            try:
                sp.wait(delay)
                break
            except subprocess.TimeoutExpired:
                try_checks(checks[:i], delay)

        cp = subprocess.run(test, **SP_KWARGS)
        if cp.returncode != 0:
            print_output(rank, "failed", test, cp.stdout.splitlines())
            raise ChildProcessError()
        print(rank, "fix successful")

    update_status("ok")


def heal(directory: Path, status_file, event, delay=10):
    if is_ko(status_file):
        print("system already in failed status, exiting")
        return

    if not directory.is_dir():
        print("directory must exist")
        return

    print("watching configuration directory:", directory)
    watcher = Watcher(directory)

    try:
        while True:
            try_checks(watcher.refresh_current_checks_if_necessary(), delay, functools.partial(write, status_file, watcher.current_modes))
            if event.wait(delay):
                break
    except ChildProcessError:
        write(status_file, watcher.current_modes, "ko")
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
