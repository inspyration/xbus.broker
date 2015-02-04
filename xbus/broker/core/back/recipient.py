import aiozmq

from xbus.broker.core.features import RecipientFeature


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

    def has_feature(self, feature: RecipientFeature):
        """Tell whether the recipient has declared support for the specified
        feature.

        :param feature: Feature to check for.
        """

        return feature.name in self.features

    def update_features(self):
        """Refresh the list of features the recipient supports.
        :note: The socket must be open.
        """

        self.features = {}
        for feature in RecipientFeature:

            # Send a "has_[feature]" API call to see what the recipient has to
            # announce about its support for the feature.
            feature_data = yield from getattr(
                self.socket.call, 'has_%s' % feature.name
            )()

            # Ensure we have received valid data.
            if not feature_data or not isinstance(feature_data, (list, tuple)):
                continue

            # Check the first part (boolean) to know feature support.
            if not feature_data[0]:
                continue

            # Save the data for features that are supported.
            self.features[feature.name] = feature_data
