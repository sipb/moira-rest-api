# We'll assume that we need new processes for the ticket credential
# cache environment variable changes (KRB5CCNAME) to actually work,
# just like on Moira

import concurrent.futures
import ldap
import ldap.sasl

LISTS_BASE = 'OU=lists,OU=Moira,DC=WIN,DC=MIT,DC=EDU'
USERS_BASE = 'OU=users,OU=Moira,DC=WIN,DC=MIT,DC=EDU'

class LdapNotFoundException(Exception):
    pass

def get_connection():
    conn = ldap.initialize("ldap://w92dc1.win.mit.edu")
    auth = ldap.sasl.gssapi()
    conn.sasl_interactive_bind_s("", auth)
    return conn

def find_list_distinguished_name(conn, name):
    res = conn.search_s(
        LISTS_BASE,
        ldap.SCOPE_SUBTREE,
        f"(cn={name})",
        ["cn"]
    )
    if not res:
        raise LdapNotFoundException(f'list {name} does not exist')
    return res[0][0]

def _get_names_in_list(list_name):
    conn = get_connection()
    list_dn = find_list_distinguished_name(conn, list_name)
    res = conn.search_s(
        USERS_BASE,
        ldap.SCOPE_ONELEVEL,
        f"(memberOf={list_dn})",
        ["displayName", "cn"]
    )
    res = {
        str(values['cn'][0].decode()): str(values['displayName'][0].decode())
        for dn, values in res
    }
    return res

def _get_user_name(kerb):
    conn = get_connection()
    try:
        res = conn.search_s(
            f'cn={kerb},{USERS_BASE}',
            ldap.SCOPE_BASE,
            attrlist=["displayName"],
        )
        return res[0][1]['displayName'][0].decode()
    except ldap.NO_SUCH_OBJECT:
        raise LdapNotFoundException(f'user {kerb} does not exist')

def get_names_in_list(list_name):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        f = executor.submit(_get_names_in_list, list_name)
        ret = f.result()
    return ret

def get_user_name(kerb):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        f = executor.submit(_get_user_name, kerb)
        ret = f.result()
    return ret
