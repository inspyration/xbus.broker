# -*- encoding: utf-8 -*-
__author__ = 'faide'

from txmta.model.quota import quota
from txmta.model.auth import user

from sqlalchemy.sql import select


def get_quotas_info(dbengine):
    """a helper function that returns a list of all active quotas
    """

    def _quotainfos_fetched(quotainfos):
        return quotainfos

    def _quota_infos_available(result):
        d = result.fetchall()
        d.addCallback(_quotainfos_fetched)
        return d

    d = dbengine.execute(
        select(
            [
                quota.c.id,
                quota.c.user_id,
                quota.c.has_size_limit,
                quota.c.usage_left,
                quota.c.has_dt_limit,
                quota.c.limit_dt,
                quota.c.usage_count,
                user.c.user_name,
            ]
        ).select_from(
            quota.join(
                user
            )
        )
    )
    d.addCallback(_quota_infos_available)
    return d
