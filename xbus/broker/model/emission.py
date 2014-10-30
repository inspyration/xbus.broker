# -*- encoding: utf-8 -*-
__author__ = 'faide'

from uuid import uuid4

from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import (Unicode, DateTime, Text)

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


emitter_profile = Table(
    'emitter_profile', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('name', Unicode(length=64), index=True, nullable=False, unique=True),
    Column("display_name", Unicode(255)),
    Column('description', Text),
)

emitter_profile_event_type_rel = Table(
    'emitter_profile_event_type_rel', metadata,
    Column('event_id', UUID, ForeignKey('event_type.id', ondelete='CASCADE'),
           primary_key=True),
    Column('profile_id', UUID,
           ForeignKey('emitter_profile.id', ondelete='CASCADE'),
           primary_key=True),
)
