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
    Column('description', Text),
)
