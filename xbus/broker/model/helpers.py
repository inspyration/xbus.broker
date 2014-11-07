# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import desc
from sqlalchemy.dialects.postgres import ARRAY

from xbus.broker.model.event import event_node
from xbus.broker.model.event import event_node_rel
from xbus.broker.model.types import UUID


@asyncio.coroutine
def get_event_tree(dbengine, event_type_id):
    query = select(
        [
            event_node.c.id,
            event_node.c.service_id,
            event_node.c.start,
            func.array_agg(
                event_node_rel.c.child_id,
                type_=ARRAY(UUID)
            ),
        ]
    )
    query = query.join(
        event_node_rel,
        event_node.c.id == event_node_rel.c.parent_id
    )
    query = query.where(
        event_node.c.type_id == event_type_id
    )
    query = query.group_by(event_node.c.id)
    query = query.order_by(desc(event_node.c.start))
    res = yield from dbengine.execute(query)
    return res
