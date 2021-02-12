import enum
import json
import subprocess

import const
import util


class Status(int, enum.Enum):
    OK = 0
    FIXING = 1
    KO = 2


class Probe(util.LoopThread):
    def __init__(self, config, delay_default=const.DELAY_DEFAULT):
        super().__init__(config.get("delay", delay_default))

        self.config = config
        self.uid = util.generate_uid(config)
        self.status = Status.OK

    def loop(self):
        if self.status != Status.OK or subprocess.run(self.config.get("if-not"), shell=True).returncode == 0:
            return

        print(self.uid, json.dumps(self.config))
        print(self.uid, "test failed, fixing")
        self.status = Status.FIXING

        sp = subprocess.Popen(self.config.get("then"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=const.ENCODING)
        for line in sp.stdout:
            print(self.uid, line.rstrip())
        if sp.wait() != 0:
            print(self.uid, "error!")

        if subprocess.run(self.config.get("if-not"), shell=True).returncode == 0:
            print(self.uid, "fixed")
            self.status = Status.OK
        else:
            print(self.uid, "test still failed: fatal error!")
            self.status = Status.KO