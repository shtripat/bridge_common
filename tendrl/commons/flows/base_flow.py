import abc
import logging

import six

from tendrl.commons.atoms.exceptions import AtomExecutionFailedError
from tendrl.commons.flows import utils as flow_utils
from tendrl.commons.utils import import_utils

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseFlow(object):
    def __init__(
            self,
            name,
            atoms,
            help,
            enabled,
            inputs,
            pre_run,
            post_run,
            type,
            uuid,
            parameters,
            job,
            definitions
    ):
        self.name = name
        self.atoms = atoms
        self.help = help
        self.enabled = enabled
        self.inputs = inputs
        self.pre_run = pre_run
        self.post_run = post_run
        self.type = type
        self.uuid = uuid
        self.parameters = parameters
        self.job = job
        self.definitions = definitions
        self.etcd_orm = self.parameters['etcd_orm']
        self.config = self.parameters['config']
        self.manager = self.parameters['manager']
        self.request_id = self.job['request_id']
        self.parameters.update({'request_id': self.request_id})

        # Flows and atoms expected to APPEND their job statuses to appropriate
        # log levels list below, logging everything to "all" is mandatory
        self.log = {"all": [], "info": [], "error": [], "warn": [],
                    "debug": []}

    @abc.abstractmethod
    def run(self):
        # Execute the pre runs for the flow
        # TODO(rohan) make a func outta the below logging common code
        msg = "Processing pre-runs for flow: %s" % self.job['run']
        LOG.info(msg)
        flow_utils.update_job_status(self.request_id, msg, self.log,
                                     'info', self.etcd_orm)

        if self.pre_run is not None:
            for mod in self.pre_run:
                msg = "Start pre-run : %s" % mod
                LOG.info(msg)
                self.log['all'].append(msg)
                self.log['info'].append(msg)

                ret_val = self.execute_atom(mod)

                if not ret_val:
                    msg = "Failed pre-run: %s for flow: %s" % \
                          (mod, self.job['run'])
                    LOG.error(msg)
                    flow_utils.update_job_status(self.request_id, msg,
                                                 self.log,
                                                 'error', self.etcd_orm)

                    raise AtomExecutionFailedError(
                        "Error executing pre run function: %s for flow: %s" %
                        (mod, self.job['run'])
                    )
                else:
                    msg = "Finished pre-run: %s for flow: %s" %\
                          (mod, self.job['run'])
                    LOG.info(msg)
                    self.log['all'].append(msg)
                    self.log['info'].append(msg)

        # Execute the atoms for the flow
        msg = "Processing atoms for flow: %s" % self.job['run']
        LOG.info(msg)
        flow_utils.update_job_status(self.request_id, msg, self.log,
                                     'info', self.etcd_orm)

        for atom in self.atoms:
            msg = "Start atom : %s" % atom
            LOG.info(msg)
            self.log['all'].append(msg)
            self.log['info'].append(msg)

            ret_val = self.execute_atom(atom)

            if not ret_val:
                msg = "Failed atom: %s on flow: %s" % \
                      (atom, self.job['run'])
                LOG.error(msg)
                flow_utils.update_job_status(self.request_id, msg, self.log,
                                             'error', self.etcd_orm)

                raise AtomExecutionFailedError(
                    "Error executing atom: %s on flow: %s" %
                    (atom, self.job['run'])
                )
            else:
                msg = 'Finished atom %s for flow: %s' %\
                      (atom, self.job['run'])
                LOG.info(msg)
                self.log['all'].append(msg)
                self.log['info'].append(msg)

        # Execute the post runs for the flow
        msg = "Processing post-runs for flow: %s" % self.job['run']
        LOG.info(msg)
        flow_utils.update_job_status(self.request_id, msg, self.log,
                                     'info', self.etcd_orm)
        if self.post_run is not None:
            for mod in self.post_run:
                msg = "Start post-run : %s" % mod
                LOG.info(msg)
                self.log['all'].append(msg)
                self.log['info'].append(msg)

                ret_val = self.execute_atom(mod)

                if not ret_val:
                    msg = "Failed post-run: %s for flow: %s" % \
                          (mod, self.job['run'])
                    LOG.error(msg)
                    flow_utils.update_job_status(self.request_id, msg,
                                                 self.log,
                                                 'error', self.etcd_orm)

                    raise AtomExecutionFailedError(
                        "Error executing post run function: %s" % mod
                    )
                else:
                    msg = "Finished post-run: %s for flow: %s" %\
                          (mod, self.job['run'])
                    LOG.info(msg)
                    flow_utils.update_job_status(self.request_id, msg,
                                                 self.log,
                                                 'info', self.etcd_orm)

    def extract_atom_details(self, atom_name):
        namespace = atom_name.split('.objects.')[0]
        object_name = atom_name.split('.objects.')[1].split('.atoms.')[0]
        atoms = self.definitions[namespace]['objects'][object_name]['atoms']
        atom = atoms[atom_name.split('.')[-2]]
        return atom.get('name'), atom.get('enabled'), atom.get('help'), \
            atom.get('inputs'), atom.get('outputs'), atom.get('uuid'), \
            atom.get('run')

    # Executes a givem atom specific by given full module name "mod"
    # It dynamically imports the atom class from module as the_atom
    # and executes the function run() on the instance of same
    def execute_atom(self, mod):
        if "tendrl" in mod and "atoms" in mod:
            atom_name, enabled, help, inputs, outputs, uuid, atom_mod = \
                self.extract_atom_details(mod)
            the_atom = import_utils.load_abs_class(atom_mod)
            try:
                ret_val = the_atom(
                    atom_name,
                    enabled,
                    help,
                    inputs,
                    outputs,
                    uuid,
                    self.parameters
                ).run()
            except AtomExecutionFailedError:
                return False

            return ret_val
        return False
