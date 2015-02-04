"""Features Xbus recipients (workers / consumers) can support.
"""

from enum import Enum

RecipientFeature = Enum(
    'RecipientFeature',

    'clearing '
    'immediate_reply '
)
