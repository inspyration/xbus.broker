# -*- encoding: utf-8 -*-
__author__ = 'faide'

"""Data emission into xbus.
"""

from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import Unicode

from xbus.broker.model import metadata
from xbus.broker.model.input import INPUT_TYPES
from xbus.broker.model.types import UUID


# Emission profiles store ways of sending data into xbus.
emission_profile = Table(
    'emission_profile', metadata,
    Column('id', UUID, default=uuid4, primary_key=True),
    Column(
        'name', Unicode(length=64), index=True, nullable=False, unique=True,
    ),
    Column(
        'input_type', Enum(*INPUT_TYPES.keys(), name='input_type'),
        nullable=False,
    ),
    Column(
        'input_descriptor_id', UUID,
        ForeignKey('input_descriptor.id', ondelete='RESTRICT'),
    ),
    # TODO More generic way of associating input types with emission profiles.
    # TODO Security - read / write / execute rights for different groups.
)


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
