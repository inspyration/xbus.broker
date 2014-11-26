# -*- encoding: utf-8 -*-

"""Ways of sending data into xbus.
"""

from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy import LargeBinary
from sqlalchemy import Table
from sqlalchemy import Unicode

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


# Input senders.
# key: table-name
INPUT_TYPES = {
    'descriptor': 'input_descriptor',
}


# Input descriptors describe file input.
input_descriptor = Table(
    'input_descriptor', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column(
        'name', Unicode(length=64), index=True, nullable=False, unique=True,
    ),
    Column('descriptor', LargeBinary, nullable=False),
    Column('descriptor_mimetype', Unicode(length=64)),
)


# TODO Other input types.
