# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

from uuid import uuid4

from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean

from sqlalchemy.types import Text

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


event_type = Table(
    'event_type', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('name', Unicode(length=64), index=True, unique=True),
    Column('description', Text),
)

event_node = Table(
    'event_node', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('service_id', UUID, ForeignKey('service.id', ondelete='RESTRICT'),
           nullable=False),
    Column('type_id', UUID, ForeignKey('event_type.id', ondelete='RESTRICT'),
           index=True, nullable=False),
    Column('is_start', Boolean, server_default='FALSE'),
)

event_node_rel = Table(
    'event_node_rel', metadata,
    Column('parent_id', UUID, ForeignKey('event_node.id', ondelete='CASCADE'),
           primary_key=True),
    Column('child_id', UUID, ForeignKey('event_node.id', ondelete='CASCADE'),
           primary_key=True),
)
