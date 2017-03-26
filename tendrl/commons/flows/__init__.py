import abc
import logging

import six

from tendrl.commons.flows.exceptions import FlowExecutionFailedError
from tendrl.commons.objects import AtomExecutionFailedError

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseFlow(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "internal"):
            if hasattr(cls, "load_definition"):
                raise Exception("Non internal Flow cannot use load_definition, must have definition in (.yml)")
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, parameters=None, job_id=None):
        # Tendrl internal flows should populate their own self._defs
        if not hasattr(self, "internal"):
            self._defs = self.load_definition()

        self.parameters = parameters
        self.job_id = job_id
        self.parameters.update({'job_id': self.job_id})
        self.parameters.update({'flow_id': self._defs['uuid']})
        if hasattr(self, "internal"):
            if not hasattr(self, "_defs"):
                raise Exception("Internal Flow must provide its own definition via '_defs' attr")

    def load_definition(self):
        cls_name = self.__class__.__name__
        if hasattr(self, "obj"):
            obj_name = self.obj.__name__
            LOG.debug("Load definitions for namespace.%s.objects.%s.flows.%s",
                      self._ns.ns_src, obj_name, cls_name)
            try:
                return self._ns.get_obj_flow_definition(obj_name,
                                                        cls_name)
            except KeyError as ex:
                msg = "Could not find definitions for " \
                      "namespace.%s.objects.%s.flows.%s" % (self._ns.ns_src,
                                                            obj_name,
                                                            cls_name)
                LOG.error(ex)
                LOG.error(msg)
                raise Exception(msg)
            finally:
                self.to_str = "%s.objects.%s.flows.%s" % (self._ns.ns_name,
                                                          obj_name,
                                                          cls_name)

        else:
            LOG.debug("Load definitions for namespace.%s.flows.%s",
                      self._ns.ns_src, cls_name)
            try:
                return self._ns.get_flow_definition(cls_name)
            except KeyError as ex:
                msg = "Could not find definitions for namespace.%s.flows.%s" %\
                      (self._ns.ns_src, cls_name)
                LOG.error(ex)
                LOG.error(msg)
                raise Exception(msg)
            finally:
                self.to_str = "%s.flows.%s" % (self._ns.ns_name, cls_name)

    @abc.abstractmethod
    def run(self):
        # Execute the pre runs for the flow
        msg = "Processing pre-runs for flow: %s" % self.to_str
        LOG.info(msg)
        # Check for mandatory parameters
        if 'mandatory' in self._defs.get('inputs', {}):
            for item in self._defs['inputs']['mandatory']:
                if item not in self.parameters:
                    raise FlowExecutionFailedError(
                        "Mandatory parameter %s not provided" % item
                    )

        if self._defs.get("pre_run") is not None:
            for atom_fqn in self._defs.get("pre_run"):
                msg = "Start pre-run : %s" % atom_fqn
                LOG.info(msg)

                ret_val = self._execute_atom(atom_fqn)

                if not ret_val:
                    msg = "Failed pre-run: %s for flow: %s" % \
                          (atom_fqn, self._defs['help'])
                    LOG.error(msg)
                    raise AtomExecutionFailedError(
                        "Error executing pre run function: %s for flow: %s" %
                        (atom_fqn, self._defs['help'])
                    )
                else:
                    msg = "Finished pre-run: %s for flow: %s" %\
                          (atom_fqn, self._defs['help'])
                    LOG.info(msg)

        # Execute the atoms for the flow
        msg = "Processing atoms for flow: %s" % self._defs['help']
        LOG.info(msg)

        for atom_fqn in self._defs.get("atoms"):
            msg = "Start atom : %s" % atom_fqn
            LOG.info(msg)

            ret_val = self._execute_atom(atom_fqn)

            if not ret_val:
                msg = "Failed atom: %s on flow: %s" % \
                      (atom_fqn, self._defs['help'])
                LOG.error(msg)
                raise AtomExecutionFailedError(
                    "Error executing atom: %s on flow: %s" %
                    (atom_fqn, self._defs['help'])
                )
            else:
                msg = 'Finished atom %s for flow: %s' %\
                      (atom_fqn, self._defs['help'])
                LOG.info(msg)

        # Execute the post runs for the flow
        msg = "Processing post-runs for flow: %s" % self._defs['help']
        LOG.info(msg)
        if self._defs.get("post_run") is not None:
            for atom_fqn in self._defs.get("post_run"):
                msg = "Start post-run : %s" % atom_fqn
                LOG.info(msg)

                ret_val = self._execute_atom(atom_fqn)

                if not ret_val:
                    msg = "Failed post-run: %s for flow: %s" % \
                          (atom_fqn, self._defs['help'])
                    LOG.error(msg)
                    raise AtomExecutionFailedError(
                        "Error executing post run function: %s" % atom_fqn
                    )
                else:
                    msg = "Finished post-run: %s for flow: %s" %\
                          (atom_fqn, self._defs['help'])
                    LOG.info(msg)

    def _execute_atom(self, atom_fqdn):
        try:
            ns, atom_name = atom_fqdn.split(".atoms.")
            ns, obj_name = ns.split(".objects.")
            ns_str = ns.split(".")[-1]
            
            if "integrations" in ns:
                current_ns =  getattr(NS.integrations, ns_str)
            else:
                current_ns = getattr(NS, ns_str)

            runnable_atom = current_ns.ns.get_atom(obj_name, atom_name)
            try:
                ret_val = runnable_atom(
                    parameters=self.parameters
                ).run()
                return ret_val
            except AtomExecutionFailedError:
                return False

        except (KeyError, AttributeError) as ex:
            LOG.error(ex)

        return False
