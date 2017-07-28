import __builtin__
import etcd
import maps
import mock
from mock import patch
import pytest
import tempfile

from tendrl.commons.flows.import_cluster import ceph_help
from tendrl.commons import TendrlNS
from tendrl.commons.utils import ansible_module_runner


'''Dummy Functions'''


def run(*args):
    raise ansible_module_runner.AnsibleExecutableGenerationFailed


def ansible(*args, **kwargs):
    raise ansible_module_runner.AnsibleModuleNotFound


def open(*args, **kwargs):
    f = tempfile.TemporaryFile()
    return f


'''Unit Test Cases'''


@patch.object(etcd, "Client")
@patch.object(etcd.Client, "read")
def init(patch_read, patch_client):
    patch_read.return_value = etcd.Client()
    patch_client.return_value = etcd.Client()
    setattr(__builtin__, "NS", maps.NamedDict())
    setattr(NS, "_int", maps.NamedDict())
    NS._int.etcd_kwargs = {
        'port': 1,
        'host': 2,
        'allow_reconnect': True}
    NS._int.client = etcd.Client(**NS._int.etcd_kwargs)
    NS._int.wclient = etcd.Client(**NS._int.etcd_kwargs)
    NS.publisher_id = "node_agent"
    NS["config"] = maps.NamedDict()
    NS.config["data"] = maps.NamedDict(logging_socket_path="test/path")
    NS.node_context = maps.NamedDict()
    NS.node_context.node_id = 1
    NS.config.data['package_source_type'] = 'test pip'
    NS.config.data['tags'] = "test"
    NS.config.data['etcd_port'] = 8085
    NS.config.data['etcd_connection'] = "Test Connection"
    tendrlNS = TendrlNS()
    return tendrlNS


@mock.patch('tendrl.commons.event.Event.__init__',
            mock.Mock(return_value=None))
@mock.patch('tendrl.commons.message.Message.__init__',
            mock.Mock(return_value=None))
def test_import_ceph():
    tendrlNS = init()
    NS.compiled_definitions = tendrlNS.current_ns.definitions
    parameters = maps.NamedDict(job_id=1, flow_id=1)
    assert ceph_help.import_ceph(parameters) is False
    NS.config.data['package_source_type'] = 'pip'
    with patch.object(ansible_module_runner.AnsibleRunner, 'run', run):
        ret = ceph_help.import_ceph(parameters)
        assert ret is False
    with patch.object(ansible_module_runner.AnsibleRunner, 'run',
                      return_value=True):
        with patch.object(__builtin__, 'open', open):
            ceph_help.import_ceph(parameters)
    with patch.object(ansible_module_runner, 'AnsibleRunner', ansible):
        with pytest.raises(ansible_module_runner.AnsibleModuleNotFound):
            ceph_help.import_ceph(parameters)
    NS.config.data['package_source_type'] = 'rpm'
    with patch.object(ansible_module_runner.AnsibleRunner, 'run', run):
        ret = ceph_help.import_ceph(parameters)
        assert ret is False
