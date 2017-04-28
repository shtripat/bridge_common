import shlex
import sys

from ansible_module_runner import AnsibleExecutableGenerationFailed
from ansible_module_runner import AnsibleRunner

from tendrl.commons.event import Event
from tendrl.commons.message import ExceptionMessage, Message

ANSIBLE_MODULE_PATH = "core/commands/command.py"

SAFE_COMMAND_LIST = [
    "lsblk",
    "lscpu",
    "getenforce",
    "gluster",
    "ceph",
    "config_manager",
    "systemctl",
    "hwinfo",
    "ping",
    "lvm",
    "gstatus"
]


class UnsupportedCommandException(Exception):
    def __init__(self, command):
        self.message = "Command: %s not supported by tendrl commons" % (
            command)


class Command(object):
    def __init__(self, command, shell=False):
        if shlex.split(command)[0] not in SAFE_COMMAND_LIST:
            raise UnsupportedCommandException(command.split()[0])
        self.attributes = {"_raw_params": command, '_uses_shell': shell}

    def run(self):
        try:
            runner = AnsibleRunner(
                ANSIBLE_MODULE_PATH,
                **self.attributes
            )
            result, err = runner.run()
            try:
                Event(
                    Message(
                        priority="debug",
                        publisher=NS.publisher_id,
                        payload={"message": "Command Execution: %s" % result}
                    )
                )
            except KeyError:
                sys.stdout.write("Command Execution: %s \n" % result)
        except AnsibleExecutableGenerationFailed as e:
            try:
                Event(
                    ExceptionMessage(
                        priority="error",
                        publisher=NS.publisher_id,
                        payload={"message": "could not run the command %s. " %
                                            self.attributes["_raw_params"],
                                 "exception": e
                                 }
                    )
                )
            except KeyError:
                sys.stderr.write("could not run the command %s. Error: %s" %
                                 (self.attributes["_raw_params"], str(e))
                                 )
            return "", str(e.message), -1
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "").encode("ascii")
        rc = result.get("rc", -1)
        return stdout, stderr, rc
