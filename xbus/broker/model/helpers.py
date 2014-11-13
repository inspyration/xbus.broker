# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import desc
from sqlalchemy import join

from xbus.broker.model.event import event_node
from xbus.broker.model.event import event_node_rel
from xbus.broker.model.types import UUIDArray
from xbus.broker.model import service
from xbus.broker.model import role


@asyncio.coroutine
def get_event_tree(dbengine, event_type_id):
    query = select(
        [
            event_node.c.id,
            event_node.c.service_id,
            event_node.c.is_start,
            func.array_agg(
                event_node_rel.c.child_id,
                type_=UUIDArray(remove_null=True)
            ).label('child_ids'),
        ]
    )
    query = query.where(
        event_node.c.type_id == event_type_id
    )
    query = query.select_from(
        join(
            event_node,
            event_node_rel,
            event_node_rel.c.parent_id == event_node.c.id,
            isouter=True,
        )
    )
    query = query.group_by(event_node.c.id)
    query = query.order_by(desc(event_node.c.is_start))
    cr = yield from dbengine.execute(query)
    res = yield from cr.fetchall()
    return res


@asyncio.coroutine
def get_consumer_roles(dbengine):
    query = select(
        [
            service.c.id,
            func.array_agg(
                role.c.id,
                type_=UUIDArray()
            ).label('role_ids'),
        ]
    )
    query = query.where(service.c.is_consumer)
    query = query.select_from(
        join(service, role, role.c.service_id == service.c.id)
    )
    query = query.group_by(service.c.id)
    cr = yield from dbengine.execute(query)
    res = yield from cr.fetchall()
    return res
