# -*- encoding: utf-8 -*-
"""model tables and classes definition
"""

import datetime
from uuid import uuid4

from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import (Unicode, Integer, DateTime)

from xbus.broker.model import metadata
from xbus.broker.model.types import UUID


# This is the association table for the many-to-many relationship between
# groups and permissions.
group_permission_table = Table(
    'group_permission', metadata,
    Column(
        'group_id', Integer, ForeignKey(
            'group.group_id', onupdate="CASCADE", ondelete="CASCADE")
    ),
    Column(
        'permission_id', Integer, ForeignKey(
            'permission.permission_id',
            onupdate="CASCADE", ondelete="CASCADE")
    ),
)

# This is the association table for the many-to-many relationship between
# groups and members - this is, the memberships.
user_group_table = Table(
    'user_group', metadata,
    Column(
        'user_id', UUID, ForeignKey(
            'user.user_id', onupdate="CASCADE", ondelete="CASCADE")
    ),
    Column(
        'group_id', Integer, ForeignKey(
            'group.group_id', onupdate="CASCADE", ondelete="CASCADE")
    ),
)


# the group table
group = Table(
    'group', metadata,
    Column("group_id", Integer, autoincrement=True, primary_key=True),
    Column("group_name", Unicode(16), unique=True),
    Column("display_name", Unicode(255)),
    Column("created", DateTime, default=datetime.datetime.now),
)


# the user table
user = Table(
    'user', metadata,
    Column("user_id", UUID, primary_key=True, default=uuid4),
    Column("user_name", Unicode(16), unique=True),
    Column("email_address", Unicode(255), unique=True),
    Column("display_name", Unicode(255)),
    Column('password', Unicode(80)),
    Column("created", DateTime, default=datetime.datetime.now),
)


permission = Table(
    'permission', metadata,
    Column("permission_id", Integer, autoincrement=True, primary_key=True),
    Column("permission_name", Unicode(16), unique=True),
    Column("description", Unicode(255)),
)
