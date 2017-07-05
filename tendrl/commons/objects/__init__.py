import etcd

import abc
import copy
import hashlib
import json
import six
import sys
import types

from tendrl.commons.event import Event
from tendrl.commons.message import ExceptionMessage
from tendrl.commons.message import Message
from tendrl.commons.utils.central_store import utils as cs_utils
from tendrl.commons.utils import etcd_utils
from tendrl.commons.utils import time_utils


@six.add_metaclass(abc.ABCMeta)
class BaseObject(object):
    def __init__(self, *args, **kwargs):
        # Tendrl internal objects should populate their own self._defs
        if not hasattr(self, "internal"):
            self._defs = BaseObject.load_definition(self)
        if hasattr(self, "internal"):
            if not hasattr(self, "_defs"):
                raise Exception("Internal Object must provide its own "
                                "definition via '_defs' attr")

    def load_definition(self):
        try:
            Event(
                Message(
                    priority="debug",
                    publisher=NS.publisher_id,
                    payload={"message": "Load definitions (.yml) for "
                                        "namespace.%s.objects.%s" %
                                        (self._ns.ns_name,
                                         self.__class__.__name__)
                             }
                )
            )
        except KeyError:
            sys.stdout.write("Load definitions (.yml) for namespace.%s.objects"
                             ".%s" % (self._ns.ns_name,
                                      self.__class__.__name__))
        try:
            return self._ns.get_obj_definition(self.__class__.__name__)
        except KeyError as ex:
            msg = "Could not find definitions (.yml) for " \
                  "namespace.%s.objects.%s" %\
                  (self._ns.ns_name, self.__class__.__name__)
            try:
                Event(
                    ExceptionMessage(
                        priority="debug",
                        publisher=NS.publisher_id,
                        payload={"message": "error",
                                 "exception": ex}
                    )
                )
            except KeyError:
                sys.stdout.write(str(ex))
            try:
                Event(
                    Message(
                        priority="debug",
                        publisher=NS.publisher_id,
                        payload={"message": msg}
                    )
                )
            except KeyError:
                sys.stdout.write(msg)
            raise Exception(msg)

    def save(self, update=True, ttl=None):
        self.render()
        key = self.value + "/data"
        try:
            NS._int.wclient.write(key, self.json)
        except (etcd.EtcdConnectionFailed, etcd.EtcdException):
            NS._int.wreconnect()
            NS._int.wclient.write(key, self.json)

    def load(self):
        self.render()
        key = self.value + '/data'
        val_str = NS._int.client.read(key).value
        loc_dict = json.loads(val_str)
        for attr_name, attr_val in vars(self).iteritems():
            if not attr_name.startswith('_') and attr_name != "value":
                _type = self._defs.get("attrs", {}).get(attr_name, {}).get("type")
                if _type in ['json', 'list', 'Json', 'List', 'JSON', 'LIST']:
	            setattr(self, attr_name, json.loads(loc_dict[attr_name]))
                else:
                    setattr(self, attr_name, loc_dict[attr_name])
        return self
        
    def load_all(self):
        value = '/'.join(self.value.split('/')[:-1])
        try:
            etcd_resp = NS._int.client.read(value)
        except (etcd.EtcdConnectionFailed, etcd.EtcdException) as ex:
                    if type(ex) != etcd.EtcdKeyNotFound:
                        NS._int.reconnect()
                        etcd_resp = NS._int.client.read(value)
                    else:
                        return None
        ins = []
        for item in etcd_resp.leaves:
            self.value = item.key
            ins.append(self.load())
        return ins

    def exists(self):
        self.render()
        _exists = False
        try:
            NS._int.client.read("/{0}".format(self.value))
            _exists = True
        except (etcd.EtcdConnectionFailed, etcd.EtcdException) as ex:
            if type(ex) != etcd.EtcdKeyNotFound:
                NS._int.reconnect()
                NS._int.client.read("/{0}".format(self.value))
                _exists = True
        return _exists

    def _map_vars_to_tendrl_fields(self):
        _fields = {}
        for attr, value in vars(self).iteritems():
            _type = self._defs.get("attrs", {}).get(attr,
                                                    {}).get("type")
            if value is None:
                value = ""
            if attr.startswith("_") or attr in ['value', 'list']:
                continue
            _fields[attr] = cs_utils.to_tendrl_field(attr, value, _type)

        return _fields

    def render(self):
        """Renders the instance into a structure for central store based on

        its key (self.value)

        :returns: The structure to use for setting.
        :rtype: list(dict{key=str,value=any})
        """

        rendered = []
        _fields = self._map_vars_to_tendrl_fields()
        if _fields:
            for name, field in _fields.iteritems():
                items = field.render()
                if type(items) != list:
                    items = [items]
                for i in items:
                    i['key'] = '/{0}/{1}'.format(self.value, i['key'])
                    rendered.append(i)
        return rendered

    @property
    def json(self):
        """Dumps the entire object as a json structure.

        """
        data = {}
        _fields = self._map_vars_to_tendrl_fields()
        if _fields:
            for name, field in _fields.iteritems():
                data[field.name] = json.loads(field.json)
                # Flatten if needed
                if field.name in data[field.name].keys():
                    data[field.name] = data[field.name][field.name]

        return json.dumps(data)

    def _hash(self):
        self.hash = None
        self.updated_at = None

        # Above items cant be part of hash
        _obj_str = "".join(sorted(self.json))
        return hashlib.md5(_obj_str).hexdigest()

    def _copy_vars(self):
        # Creates a copy intance of $obj using it public vars
        _public_vars = {}
        for attr, value in vars(self).iteritems():
            if attr.startswith("_") or attr in ['hash', 'updated_at',
                                                'value', 'list']:
                continue
            if type(value) in [dict, list]:
                value = copy.deepcopy(value)
            _public_vars[attr] = value
        return self.__class__(**_public_vars)


@six.add_metaclass(abc.ABCMeta)
class BaseAtom(object):
    def __init__(self, parameters=None):
        self.parameters = parameters or dict()

        # Tendrl internal atoms should populate their own self._defs
        if not hasattr(self, "internal"):
            self._defs = BaseAtom.load_definition(self)
        if hasattr(self, "internal"):
            if not hasattr(self, "_defs"):
                raise Exception("Internal Atom must provide its own "
                                "definition via '_defs' attr")

    def load_definition(self):
        try:
            Event(
                Message(
                    priority="debug",
                    publisher=NS.publisher_id,
                    payload={"message": "Load definitions (.yml) for "
                                        "namespace.%s."
                                        "objects.%s.atoms.%s" %
                                        (self._ns.ns_name, self.obj.__name__,
                                         self.__class__.__name__)
                             }
                )
            )
        except KeyError:
            sys.stdout.write("Load definitions (.yml) for "
                             "namespace.%s.objects.%s."
                             "atoms.%s" % (self._ns.ns_name, self.obj.__name__,
                                           self.__class__.__name__))
        try:
            return self._ns.get_atom_definition(self.obj.__name__,
                                                self.__class__.__name__)
        except KeyError as ex:
            msg = "Could not find definitions (.yml) for" \
                  "namespace.%s.objects.%s.atoms.%s" % (self._ns.ns_src,
                                                        self.obj.__name__,
                                                        self.__class__.__name__
                                                        )
            try:
                Event(
                    ExceptionMessage(
                        priority="debug",
                        publisher=NS.publisher_id,
                        payload={"message": "Error", "exception": ex}
                    )
                )
            except KeyError:
                sys.stderr.write("Error: %s" % ex)
            try:
                Event(
                    Message(
                        priority="debug",
                        publisher=NS.publisher_id,
                        payload={"message": msg}
                    )
                )
            except KeyError:
                sys.stderr.write(msg)
            raise Exception(msg)

    @abc.abstractmethod
    def run(self):
        raise AtomNotImplementedError(
            'define the function run to use this class'
        )


class AtomNotImplementedError(NotImplementedError):
    def __init__(self, err):
        self.message = "run function not implemented. {}".format(err)
        super(AtomNotImplementedError, self).__init__(self.message)


class AtomExecutionFailedError(Exception):
    def __init__(self, err):
        self.message = "Atom Execution failed. Error:" + \
                       " {}".format(err)
        super(AtomExecutionFailedError, self).__init__(self.message)
