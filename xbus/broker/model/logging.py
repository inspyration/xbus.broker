# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import datetime
from uuid import uuid4

from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import Boolean

from sqlalchemy.types import Text

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


ENVELOPE_STATES = ['emit', 'canc', 'wait', 'exec', 'done', 'stop', 'fail']

TRACKING_STATES = [
    'unprocessed',
    'processing',
    'on_hold',
    'corrected',
    'won_t_fix',
]

envelope = Table(
    'envelope', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('emitter_id', UUID, ForeignKey('emitter.id', ondelete='RESTRICT'),
           nullable=False),
    Column('state', Enum(*ENVELOPE_STATES, name='envelope_state'),
           nullable=False),
    Column('posted_date', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
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
    Column('state', Enum(*TRACKING_STATES, name='tracking_state'),
           nullable=False, default='unprocessed'),
    Column(
        'responsible_id', UUID,
        ForeignKey('user.user_id', ondelete='RESTRICT'),
    ),
)

# Errors launched when processing an event (as part of an envelope).
event_error = Table(
    'event_error', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('envelope_id', UUID,
           ForeignKey('envelope.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('event_id', UUID, ForeignKey('event.id', ondelete='CASCADE')),
    Column('node_id', UUID, ForeignKey('event_node.id', ondelete='SET NULL')),
    Column('role_id', UUID, ForeignKey('role.id', ondelete='SET NULL')),
    Column('items', Text),
    Column('message', Text),
    Column('error_date', DateTime, nullable=False,
           default=datetime.datetime.utcnow),
    Column('state', Enum(*TRACKING_STATES, name='tracking_state'),
           nullable=False, default='unprocessed'),
    Column(
        'responsible_id', UUID,
        ForeignKey('user.user_id', ondelete='RESTRICT'),
    ),
)

# Track comments and state changes of event errors.
event_error_tracking = Table(
    'event_error_tracking', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column(
        'event_error_id', UUID,
        ForeignKey('event_error.id', ondelete='CASCADE'),
        index=True, nullable=False,
    ),
    Column(
        'user_id', UUID,
        ForeignKey('user.user_id', ondelete='RESTRICT'),
        nullable=False,
    ),
    Column('date', DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column('comment', Text, nullable=False),
    Column('new_state', Enum(*TRACKING_STATES, name='tracking_state')),
)

# Track comments and state changes of events.
event_tracking = Table(
    'event_tracking', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column(
        'event_id', UUID,
        ForeignKey('event.id', ondelete='CASCADE'),
        index=True, nullable=False,
    ),
    Column(
        'user_id', UUID,
        ForeignKey('user.user_id', ondelete='RESTRICT'),
        nullable=False,
    ),
    Column('date', DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column('comment', Text, nullable=False),
    Column('new_state', Enum(*TRACKING_STATES, name='tracking_state')),
)

item = Table(
    'item', metadata,
    Column('event_id', UUID, nullable=False, primary_key=True),
    Column('index', Integer, nullable=False, primary_key=True),
    Column('data', LargeBinary),
)

event_consumer_failure_rel = Table(
    'event_consumer_inactive_rel', metadata,
    Column('event_id', UUID, ForeignKey('event.id', ondelete='CASCADE')),
    Column('node_id', UUID, ForeignKey('event_node.id', ondelete='CASCADE')),
    Column('role_id', UUID, ForeignKey('role.id', ondelete='CASCADE')),
    Column('was_unavailable', Boolean)
)
