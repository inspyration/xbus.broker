import aiozmq

from xbus.broker.core.features import NODE_FEATURES


class ClientNode(object):
    """Information about an Xbus client node (a worker or a consumer):
    - its metadata;
    - the features it supports;
    - a socket.
    """

    def connect(self, url):
        """Initialize the client node information holder. Open a socket to the
        specified url and use it to fetch metadata and supported features.

        :param url: URL to reach the client node.
        """

        self.socket = yield from aiozmq.rpc.connect_rpc(connect=url)
        self.metadata = yield from self.socket.call.get_metadata()
        yield from self.update_features()

    def update_features(self):
        """Refresh the list of features the client node supports.
        :note: The socket must be open.
        """

        self.features = {}
        for feature in NODE_FEATURES:
            feature_data = yield from getattr(
                self.socket.call, 'has_%s' % feature
            )()
            self.features[feature] = feature_data
