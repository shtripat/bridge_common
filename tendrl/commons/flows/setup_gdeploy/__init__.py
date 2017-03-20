import json
import logging
import uuid

from tendrl.commons import flows
from tendrl.commons.objects.job import Job
from tendrl.commons.utils import ansible_module_runner
from tendrl.commons.utils.ssh import generate_key

LOG = logging.getLogger(__name__)


class SetupGdeploy(flows.BaseFlow):
    def run(self):
        # Install gdeploy on the node
        ansible_module_path = "core/packaging/os/yum.py"
        attributes["name"] = "gdeploy"
        try:
            runner = ansible_module_runner.AnsibleRunner(
                ansible_module_path,
                **attributes
            )
            runner.run()
        except ansible_module_runner.AnsibleExecutableGenerationFailed:
            raise FlowExecutionFailedError(
                "Failed to install gdeploy"
            )

        # Install python-gdeploy on the node
        if NS.config.data['package_source_type'] == 'pip':
            name = "https://github.com/Tendrl/python-gdeploy/archive/master.tar.gz"
            attributes["name"] = name
            attributes["editable"] = "false"
            ansible_module_path = "core/packaging/language/pip.py"
        elif NS.config.data['package_source_type'] == 'rpm':
            name = "tendrl-python-gdeploy"
            ansible_module_path = "core/packaging/os/yum.py"
            attributes["name"] = name
        else:
            raise FlowExecutionFailedError(
                "Failed to install python-gdeploy. Invalid package source type"
            )

        try:
            runner = ansible_module_runner.AnsibleRunner(
                ansible_module_path,
                **attributes
            )
            runner.run()
        except ansible_module_runner.AnsibleExecutableGenerationFailed:
            raise FlowExecutionFailedError(
                "Failed to install python-gdeploy"
            )

        # Generate ssh key for this node
        ssh_key, err = generate_key.GenerateKey().run()
        if err != "":
            raise FlowExecutionFailedError(
                "Failed generating SSH key for the node"
            )

        # Copy the public key to all the other nodes
        node_list = self.parameters['Node[]']
        ssh_job_ids = []
        if len(node_list) > 1:
            for node in node_list:
                if NS.node_context.node_id != node:
                    new_params = self.parameters.copy()
                    new_params['Node[]'] = [node]
                    new_params['ssh_key'] = ssh_key
                    payload = {
                        "integration_id": self.parameters[
                            'TendrlContext.integration_id'
                        ],
                        "node_ids": [node],
                        "run": "tendrl.flows.AuthorizeSshKey",
                        "status": "new",
                        "parameters": new_params,
                        "parent": self.parameters['job_id'],
                        "type": "node"
                    }
                    _job_id = str(uuid.uuid4())
                    Job(
                        job_id=_job_id,
                        status="new",
                        payload=json.dumps(payload)
                    ).save()
                    ssh_job_ids.append(_job_id)
                    LOG.info(
                        "Created SSH setup job %s for node %s" %\
                        (_job_id, node)
                    )

        all_ssh_jobs_done = False
        while not all_ssh_jobs_done:
            all_status = []
            for job_id in ssh_job_ids:
                all_status.append(
                    NS.etcd_orm.client.read(
                        "/queue/%s/status" % job_id
                    ).value
                )
            if all(status == "finished" for status in all_status):
                all_ssh_jobs_done = True        

        return True

    def load_definition(self):
        return {"help": "Setup Gdeploy",
                "uuid": "dc4c8775-1595-43c7-a6c6-517f0081545d"}
