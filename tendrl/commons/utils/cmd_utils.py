import logging
import shlex

from ansible_module_runner import AnsibleExecutableGenerationFailed
from ansible_module_runner import AnsibleRunner

ANSIBLE_MODULE_PATH = "core/commands/command.py"
LOG = logging.getLogger(__name__)

SAFE_COMMAND_LIST = [
    "lsblk",
    "lscpu",
    "getenforce",
    "gluster",
    "ceph",
    "config_manager",
    "systemctl",
    "hwinfo",
    "cat",
    "ping"
]


class UnsupportedCommandException(Exception):
    def __init__(self, command):
        self.message = "Command: %s not supported by tendrl commons" % (
            command)


class Command(object):
    def __init__(self, command):
        if shlex.split(command)[0] not in SAFE_COMMAND_LIST:
            raise UnsupportedCommandException(command.split()[0])
        self.attributes = {"_raw_params": command}

    def run(self):
        try:
            runner = AnsibleRunner(
                ANSIBLE_MODULE_PATH,
                **self.attributes
            )
            result, err = runner.run()
            LOG.debug("Command Execution: %s", result)
        except AnsibleExecutableGenerationFailed as e:
            LOG.error("could not run the command %s. Error: %s",
                      self.attributes["_raw_params"], str(e))
            return "", str(e.message), -1
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "").encode("ascii")
        rc = result.get("rc", -1)
        return stdout, stderr, rc
