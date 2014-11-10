# -*- encoding: utf-8 -*-
from sqlalchemy.types import TypeDecorator
from sqlalchemy.types import CHAR
from sqlalchemy.types import TEXT
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ARRAY
import uuid


class UUID(TypeDecorator):
    """Platform-independent GUID type.

    This type returns an Unicode string: the GUID
    encoded in hexadecimal with no dashes.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return value.strip('-')


class UUIDArray(TypeDecorator):
    """Platform-independent GUID array type.

    This type returns an array of Unicode strings.
    Each GUID is encoded in hexadecimal with no dashes.

    Uses Postgresql's UUID and ARRAY types, otherwise
    uses TEXT, storing as stringified hex values.
    """
    impl = CHAR

    def __init__(self, *a, remove_null=False, **k):
        self.remove_null = remove_null
        super(UUIDArray, self).__init__(*a, **k)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(PG_UUID()))
        else:
            return dialect.type_descriptor(TEXT)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        else:
            return '{{{}}}'.format(','.join(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if dialect.name == 'postgresql':
                value = ''.join(value)
            res = value.strip('{-}').split(',')
            if len(res) == 1 and res[0] == '':
                return []
            elif self.remove_null:
                return list(filter(lambda x: x != "NULL", res))
            else:
                return res
