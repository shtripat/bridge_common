from tendrl.commons import objects


class ClusterNodeContext(objects.BaseObject):

    def __init__(self, node_id=None, fqdn=None,
                 tags=None, status=None, sync_status=None,
                 last_sync=None, *args, **kwargs):
        super(ClusterNodeContext, self).__init__(*args, **kwargs)
        _node_context = NS.node_context.load()
        self.node_id = node_id or _node_context.node_id
        self.fqdn = fqdn or _node_context.fqdn
        self.tags = tags or _node_context.tags
        self.status = status or _node_context.status
        self.sync_status = sync_status or _node_context.sync_status
        self.last_sync = last_sync or _node_context.last_sync
        self.value = 'clusters/{0}/nodes/{1}/NodeContext'

    def render(self):
        self.value = self.value.format(NS.tendrl_context.integration_id,
                                       self.node_id)
        return super(ClusterNodeContext, self).render()
