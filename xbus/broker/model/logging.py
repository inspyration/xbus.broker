# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

from uuid import uuid4

from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import func

from sqlalchemy.types import Text

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


ENVELOPE_STATES = ['emit', 'canc', 'wait', 'exec', 'done', 'stop', 'fail']

envelope = Table(
    'envelope', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('emitter_id', UUID, ForeignKey('emitter.id', ondelete='RESTRICT'),
           nullable=False),
    Column('state', Enum(*ENVELOPE_STATES, name='envelope_state'),
           nullable=False),
    Column('posted_date', DateTime, nullable=False,
           default=func.localtimestamp),
    Column('done_date', DateTime),
)

event = Table(
    'event', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('envelope_id', UUID, ForeignKey('envelope.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('emitter_id', UUID, ForeignKey('emitter.id', ondelete='RESTRICT'),
           nullable=False),
    Column('type_id', UUID, ForeignKey('event_type.id', ondelete='RESTRICT'),
           nullable=False),
    Column('started_date', DateTime),
    Column('done_date', DateTime),
    Column('estimated_items', Integer),
    Column('sent_items', Integer),
)

event_error = Table(
    'event_error', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('envelope_id', UUID,
           ForeignKey('envelope.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('event_id', UUID,
           ForeignKey('event.id', ondelete='CASCADE')),
    Column('service_id', UUID,
           ForeignKey('service.id', ondelete='CASCADE')),
    Column('items', Text),
    Column('message', Text),
    Column('error_date', DateTime, nullable=False, default=func.localtimestamp)
)

item = Table(
    'item', metadata,
    Column('event_id', UUID, nullable=False, primary_key=True),
    Column('index', Integer, nullable=False, primary_key=True),
    Column('data', LargeBinary),
)