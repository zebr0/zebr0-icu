import hashlib
import json
import threading

ENCODING = "utf-8"


class StoppableThread(threading.Thread):
    def stop(self):
        pass


class LoopThread(StoppableThread):
    def __init__(self, delay):
        super().__init__()

        self.delay = delay
        self.event_stop = threading.Event()

    def run(self):
        while not self.event_stop.is_set():
            self.loop()
            self.event_stop.wait(self.delay)

    def stop(self):
        self.event_stop.set()

    def loop(self):
        pass


def generate_uid(obj):
    return "#" + hashlib.md5(json.dumps(obj).encode(ENCODING)).hexdigest()[:8]
