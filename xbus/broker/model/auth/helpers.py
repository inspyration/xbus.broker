# -*- encoding: utf-8 -*-
__author__ = 'faide'

from hashlib import sha1
import os

from sqlalchemy.sql import select
from sqlalchemy import exists
from sqlalchemy import and_
from sqlalchemy import literal

from xbus.broker.model.types import UUID
from xbus.broker.model import group
from xbus.broker.model import user
from xbus.broker.model import permission
from xbus.broker.model import group_permission_table
from xbus.broker.model import user_group_table


def get_groupnames_for_userid(dbengine, userid):

    def _return_groups(group_rows):
        return [g[0] for g in group_rows]

    def _groups_available(result):
        d = result.fetchall()
        d.addCallback(_return_groups)
        return d

    d = dbengine.execute(
        select(
            [group.c.group_name]
        ).select_from(
            group.join(
                user_group_table,
                user_group_table.c.user_id == userid
            )
        )
    )
    d.addCallback(_groups_available)
    return d


def get_group_id_by_name(dbengine, group_name):
    def _return_group_name(group_res):
        return group_res[0]

    def _groups_available(result):
        d = result.fetchone()
        d.addCallback(_return_group_name)
        return d

    d = dbengine.execute(
        select(
            [group.c.group_id]
        ).where(
            group.c.group_name == group_name
        ).limit(1)
    )
    d.addCallback(_groups_available)
    return d


def remove_user_from_group(dbengine, user_id, group):

    def _done(res):
        return res

    def _groupid_available(group_id, dbengine, user_id):
        d = dbengine.execute(
            user_group_table.delete().where(
                user_group_table.c.user_id == user_id
            ).where(
                user_group_table.c.group_id == group_id
            )
        )
        d.addCallback(_done)
        return d

    d = get_group_id_by_name(dbengine, group)
    d.addCallback(_groupid_available, dbengine, user_id)

    return d


def add_user_in_group(dbengine, user_id, group):
    def _user_added(res):
        return

    def _groupid_available(group_id, dbengine, user_id):

        # insert into where not exists...

        # first create a "select where not exist"
        query = select(
            [
                literal(user_id, type_=UUID),
                literal(group_id)
            ]
        ).where(
            ~exists(
                [user_group_table.c.user_id]
            ).where(
                and_(
                    user_group_table.c.user_id == user_id,
                    user_group_table.c.group_id == group_id
                )
            )
        )

        # then use the select clause inside our insert
        d = dbengine.execute(
            user_group_table.insert().from_select(
                [
                    'user_id',
                    'group_id',
                ],
                query
            )
        )
        d.addCallback(_user_added)
        return d

    d = get_group_id_by_name(dbengine, group)
    d.addCallback(_groupid_available, dbengine, user_id)

    return d


def _user_failed(*args, **kwargs):
    """when no user is found we should return user=None, groups=None
    """
    return None, None


def _return_userinfo(groups, user_row):
    return user_row, groups


def _userinfo_fetched(userinfo, dbengine):
    if not userinfo:
        return _user_failed()

    d = get_groupnames_for_userid(
        dbengine,
        userinfo["user_id"]
    )
    d.addCallback(_return_userinfo, userinfo)
    return d


def _userinfo_available(result, dbengine):
    d = result.fetchone()
    d.addCallback(_userinfo_fetched, dbengine)
    return d


def get_userinfo_byid(dbengine, user_id):
    """helper function that returns a deferred. Once this deferred callback
    fires you will get a n-tuple containing all columns of a user row.
    """
    query = user.select().where(
        user.c.user_id == user_id
    ).limit(1)

    d = dbengine.execute(
        query
    )

    d.addCallback(_userinfo_available, dbengine)
    d.addErrback(_user_failed)
    return d


def get_userinfo_byname(dbengine, username):
    """helper function that returns a deferred. Once this deferred callback
    fires you will get a n-tuple containing all columns of a user row.
    """

    d = dbengine.execute(
        user.select().where(
            user.c.user_name == username
        ).limit(1)
    )

    d.addCallback(_userinfo_available, dbengine)
    return d


def get_userinfos(dbengine):
    """helper function to fetch all users + associated groups
    """

    def _return_userinfos(groups, user_rows):
        # groups is list containing 2-tuples like so:
        # [(True, []), (True, [u'managers',])]
        return zip(user_rows, [g[1] for g in groups])

    def _userinfos_fetched(userinfos, dbengine):
        deferreds = []

        # TODO: compile one sql request instead of many
        for userinfo in userinfos:

            deferreds.append(
                get_groupnames_for_userid(
                    dbengine,
                    userinfo["user_id"]
                )
            )
        d = DeferredList(deferreds)
        d.addCallback(_return_userinfos, userinfos)
        return d

    def _user_infos_available(result, dbengine):
        d = result.fetchall()
        d.addCallback(_userinfos_fetched, dbengine)
        return d

    d = dbengine.execute(
        user.select()
    )
    d.addCallback(_user_infos_available, dbengine)
    return d


def update_user(dbengine, userid, user_dict):
    """a helper function to update a user
    if user_dict contains a password it must be in clear because
    this  helper will take care of encryption
    """
    def _update_done(*args, **kwargs):
        return

    if "password" in user_dict:
        # we have a password in the payload...
        # let's encrypt that properly
        passwd_ = user_dict.pop("password")
        user_dict['password'] = gen_password(passwd_)

    d = dbengine.execute(
        user.update().values(
            **user_dict
        ).where(
            user.c.user_id == userid
        )
    )
    d.addCallback(_update_done)
    return d


def create_user(dbengine, user_dict):
    """a helper function to create a user
    the password must be in clear text inside the user_dict because
    this helper will take care of encryption
    """
    def _create_done(*args, **kwargs):
        return

    d = dbengine.execute(
        user.insert().values(
            **user_dict
        )
    )
    d.addCallback(_create_done)
    return d


def get_principals(dbengine, userid):
    """given a user id (integer) we return a set of principals
    ie: permission names, example: ["manager", "editor", "authenticated"]

    @param dbengine: a configured sqlalchemy engine
    @type dbengine: sqlalchemy.engine

    @param userid: a integer representing the internal ID of a User
    @param userid: int
    """
    def _result_principal(result):
        d = result.fetchall()
        d.addCallback(_principals_values)
        return d

    def _principals_values(principals):
        return set([p[0] for p in principals])

    d = dbengine.execute(
        select(
            [permission.c.permission_name]
        ).select_from(
            user.join(
                user_group_table
            ).join(
                group,
                user.c.user_id == userid
            ).join(
                group_permission_table,
            ).join(
                permission
            )
        )
    )
    d.addCallback(_result_principal)
    return d


def gen_password(password):
    """encrypts password on the fly using the encryption
    algo defined in the configuration
    """
    algorithm = 'salted_sha1'
    return encrypt_password(algorithm, password)


def encrypt_password(algorithm, password):
    """Hash the given password with the specified algorithm. Valid values
    for algorithm are 'salted_sha1'. All other algorithm values will
    be essentially a no-op."""

    if isinstance(password, str):
        # if password is still a string (as opposed to bytes) then
        # we convert it to bytes
        password_8bit = password.encode('UTF-8')
    else:
        password_8bit = password

    if "salted_sha1" == algorithm:
        salt = sha1()
        salt.update(os.urandom(60))
        _hash = sha1()
        # hash.update() accepts only bytes not strings
        _hash.update(password_8bit + salt.hexdigest().encode('utf-8'))
        hashed_password = salt.hexdigest() + _hash.hexdigest()

    else:
        raise ValueError(
            'Only salted_sha1 is implemented, not "{}"'.format(
                algorithm
            )
        )

    # make sure the hashed password is an UTF-8 object at the end of the
    # process because SQLAlchemy _wants_ a unicode object for
    # Unicode columns
    if not isinstance(hashed_password, str):
        hashed_password = hashed_password.decode('UTF-8')

    return hashed_password


def validate_password(password1, password2):
    """Check the password against existing credentials.
    this method _MUST_ return a boolean.

    @param password1: the password that was provided by the user to
    try and authenticate. This is the clear text version that we will
    need to match against the (possibly) encrypted one in the database.
    @type password1: unicode object

    @param password2: the in database password
    @type password2: unicode object
    """
    algorithm = 'salted_sha1'
    if "salted_sha1" == algorithm:
        hashed_pass = sha1()
        hashed_pass.update(password1 + password2[:40])

        return password2[40:] == hashed_pass.hexdigest()

    else:
        ValueError('Only salted_sha1 is implemented, not "%s"' % algorithm)
