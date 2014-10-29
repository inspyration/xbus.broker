# -*- encoding: utf-8 -*-
"""helper script to create an initial database
"""

from sqlalchemy import create_engine
from xbus.broker.model import metadata
from xbus.broker.model import user
from xbus.broker.model import group
from xbus.broker.model import permission
from xbus.broker.model import user_group_table
from xbus.broker.model import group_permission_table
from xbus.broker.model import gen_password


def setup_usergroupperms(engine):
    """default manager setup...
    """
    passw = gen_password(u'managepass')

    # create user
    engine.execute(
        user.insert().values(
            user_name=u'manager',
            display_name=u'Example manager',
            email_address=u'manager@somedomain.com',
            password=passw,
        )
    )

    # fetch user id
    user_id = engine.execute(
        user.select().where(
            user.c.user_name == u'manager'
        ).limit(1)
    ).fetchone()[user.c.user_id]

    # create manager group
    engine.execute(
        group.insert().values(
            group_name=u'managers',
            display_name=u'Managers Group',
        )
    )

    # fetch group_id
    managers_group_id = engine.execute(
        group.select().where(
            group.c.group_name == u'managers'
        ).limit(1)
    ).fetchone()[group.c.group_id]

    # add user/group relation
    engine.execute(
        user_group_table.insert().values(
            user_id=user_id,
            group_id=managers_group_id
        )
    )

    p = permission.insert()
    p = p.values(
        permission_name=u'manage',
        description=(
            u'This permission give an administrative '
            u'right to the bearer'
        )
    )

    engine.execute(p)

    permission_id = engine.execute(
        permission.select().where(
            permission.c.permission_name == u'manage'
        ).limit(1)
    ).fetchone()[permission.c.permission_id]

    # insert group / permission
    engine.execute(
        group_permission_table.insert().values(
            group_id=managers_group_id,
            permission_id=permission_id,
        )
    )


def setup_app(config):
    """Place any commands to setup txMTA here

    config must be a config object as created by SafeConfigParser
    from the standard python lib and must contain a section
    database with an entry sqlalchemy.dburi"""

    print("Creating tables")

    # get dbengine according to config file
    dbengine = create_engine(
        config.get('database', 'sqlalchemy.dburi'),
        echo=True
    )

    # create all the tables defined in the model
    # the bind parameter is given at runtime for the
    # metadata because this metadata is not bound to an engine
    metadata.create_all(bind=dbengine)

    # any other data to be created in the database should be put here
    # like a default user with admin rights
    setup_usergroupperms(dbengine)
