import argparse
import functools
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
            print_output(rank, "failed again", test, cp.stdout.splitlines())
            raise ChildProcessError()
        print(rank, "fix successful")

    update_status("ok")


def heal(configuration_directory: Path, status_file, event, delay=10):
    if is_ko(status_file):
        print("exiting: ko status found in", status_file)
        return

    if not configuration_directory.is_dir():
        print("exiting:", configuration_directory, "must exist and be a directory")
        return

    print("watching:", configuration_directory)
    watcher = Watcher(configuration_directory)

    try:
        while not event.is_set():
            watcher.refresh_current_checks_if_necessary()
            try_checks(watcher.current_checks, delay, functools.partial(write, status_file, watcher.current_modes))
            event.wait(delay)
        print("exiting: loop-ending signal")
    except ChildProcessError:
        write(status_file, watcher.current_modes, "ko")
        print("exiting: fatal error")


def main(args=None):
    argparser = argparse.ArgumentParser(description="")
    argparser.add_argument("-c", "--configuration-directory", type=Path, default=Path("/etc/heal"), help="")
    argparser.add_argument("-s", "--status-file", type=Path, default=Path("/var/heal/status.json"), help="")
    argparser.add_argument("-d", "--delay", type=float, default=10, help="")
    args = argparser.parse_args(args)

    event = threading.Event()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda signum, frame: event.set())

    heal(args.configuration_directory, args.status_file, event, args.delay)
