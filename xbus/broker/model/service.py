# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

from uuid import uuid4

from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy import DateTime

from sqlalchemy.types import Text

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID

service = Table(
    'service', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('name', Unicode(length=64), index=True, unique=True),
    Column('consumer', Boolean, server_default='FALSE'),
    Column('description', Text),
)

role = Table(
    'role', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column('login', Unicode(length=64), index=True, nullable=False,
           unique=True),
    Column('service_id', UUID, ForeignKey('service.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('last_logged', DateTime),
)
