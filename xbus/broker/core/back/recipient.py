import aiozmq

from xbus.broker.core.features import RECIPIENT_FEATURES


class Recipient(object):
    """Information about an Xbus recipient (a worker or a consumer):
    - its metadata;
    - the features it supports;
    - a socket.
    """

    def connect(self, url):
        """Initialize the recipient information holder. Open a socket to the
        specified URL and use it to fetch metadata and supported features.

        :param url: URL to reach the recipient.
        """

        self.socket = yield from aiozmq.rpc.connect_rpc(connect=url)
        self.metadata = yield from self.socket.call.get_metadata()
        yield from self.update_features()

    def update_features(self):
        """Refresh the list of features the recipient supports.
        :note: The socket must be open.
        """

        self.features = {}
        for feature in RECIPIENT_FEATURES:
            feature_data = yield from getattr(
                self.socket.call, 'has_%s' % feature
            )()
            self.features[feature] = feature_data
