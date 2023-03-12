import subprocess
from flask import Flask, request, Response
from decorators import webathena, plaintext, moira_query
import moira
from util import *

app = Flask(__name__)

# I wanted to separate this into multiple files, but it seems non-trivial: 
# https://www.reddit.com/r/flask/comments/m3kp1i/splitting_flask_app_into_multiple_files/
# https://flask.palletsprojects.com/en/2.2.x/patterns/appfactories/
# So I think one file will suffice

@app.get('/')
@plaintext
def home():
    return 'Welcome to the Moira API! This is work-in-progress.\nFor documentation see: https://github.com/gabrc52/webmoira2/tree/main/backend'

@app.get('/klist')
@webathena
@plaintext
def test(kerb):
    result = subprocess.run('klist', stdout=subprocess.PIPE)
    return result.stdout.decode()

@app.errorhandler(404)
def not_found(error):
    return {
        'name': 'METHOD_NOT_FOUND',
        'description': f'{error}',
    }

@app.errorhandler(405)
def method_not_allowed(error):
    return {
        'name': 'METHOD_NOT_ALLOWED',
        'description': "The HTTP method you're trying to use is not allowed or has not been implemented for this URL",
    }

@app.get('/whoami')
@webathena
@plaintext
def whoami(kerb):
    return kerb


@app.get('/users/<string:user>/')
@webathena
@moira_query
def get_user(user, kerb):
    if user == 'me':
        user = kerb
    res = moira.query('get_user_by_login', user)
    assert len(res) == 1
    res = res[0]

    if res['middle']:
        full_name = f"{res['first']} {res['middle']} {res['last']}"
    else:
        full_name = f"{res['first']} {res['last']}"

    return {
        'full_name': full_name,
        'names': {
            'first': res['first'],
            'middle': res['middle'],
            'last': res['last'],
        },
        'kerb': kerb,
        'mit_id': res['clearid'],
        'class_year': res['class'],
    }


@app.get('/users/<string:user>/belongings')
@webathena
@moira_query
def get_user_belongings(user, kerb):
    if user == 'me':
        user = kerb
    recurse = parse_bool(request.args.get('recurse', True))
    return get_ace_use(conditional_recursive_type('USER', recurse), user)


@app.get('/users/<string:user>/lists')
@webathena
@moira_query
def get_user_lists(user, kerb):
    if user == 'me':
        user = kerb
    include_properties = request.args.get('include_properties', False)
    recurse = request.args.get('recurse', True)
    res = moira.query('get_lists_of_member', conditional_recursive_type('USER', recurse), user)
    if include_properties:
        return [parse_list_dict(entry) for entry in res]
    else:
        return [entry['list_name'] for entry in res]


@app.get('/users/<string:user>/tapaccess')
@webathena
@moira_query
def user_tap_access(user, kerb):
    if user == 'me':
        user = kerb
    res = moira.query('get_pacs_lists_of_member', 'RUSER', user)
    return [entry['list_name'] for entry in res]


@app.get('/lists/')
@webathena
@moira_query
def get_all_lists(kerb):
    if not parse_bool(request.args.get('confirm', False)):
        return {
            'description': 'You must set confirm to true to run this query.',
        }, 400
    active = request.args.get('active', 'true')
    public = request.args.get('public', 'true')
    hidden = request.args.get('hidden', 'false')
    maillist = request.args.get('is_mailing_list', 'true')
    group = request.args.get('is_afs_group', 'dontcare')
    res = moira.query('qualified_get_lists', active.upper(), public.upper(), hidden.upper(), maillist.upper(), group.upper())
    return [entry['list'] for entry in res]


@app.post('/lists/<string:list_name>/')
@webathena
@moira_query
def make_list(list_name, kerb):
    # TODO: figure this out
    # First, check if list exists though
    return {'description': 'Not implemented'}, 401


@app.get('/lists/<string:list_name>/')
@webathena
@moira_query
def get_list(list_name, kerb):
    res = moira.query('get_list_info', list_name)[0]
    return {
        'name': res['name'],
        'description': res['description'],
        'active': parse_bool(res['active']),
        'public': parse_bool(res['publicflg']),
        'hidden': parse_bool(res['hidden']),
        'is_mailing_list': parse_bool(res['maillist']),
        'is_afs_group': parse_bool(res['grouplist']),
        'is_nfs_group': parse_bool(res['nfsgroup']),
        'is_physical_access': parse_bool(res['pacslist']),
        'is_mailman_list': parse_bool(res['mailman']),
        'owner': {
            'type': res['ace_type'].lower(),
            'name': res['ace_name'],
        },
        'membership_administrator': None if res['memace_type'] == 'NONE' else {
            'type': res['memace_type'].lower(),
            'name': res['memace_name'],
        },
        'last_modified': {
            'time': res['modtime'],
            'user': res['modby'],
            'tool': res['modwith'],
        },
    }


@app.patch('/lists/<string:list_name>/')
@webathena
@moira_query
@plaintext
def update_list(list_name, kerb):
    current_attributes = moira.query('get_list_info', list_name)[0]

    """
    Gets the given attribute
    * If given by the API caller, use that value
    * Otherwise, use the current property of the list
    * If moira_name is none, it is assumed to be the same as api_name
    """
    def get_attribute(api_name, moira_name=None):
        if moira_name is None:
            moira_name = api_name
        if api_name in request.json:
            return request.json[api_name]
        else:
            return current_attributes[moira_name]
    
    # return dict( # for debugging
    moira.query(
        'update_list', 
        name=list_name,
        newname=get_attribute('name', 'name'),
        active=parse_bool_for_moira(get_attribute('active')),
        publicflg=parse_bool_for_moira(get_attribute('public', 'publicflg')),
        hidden=parse_bool_for_moira(get_attribute('hidden')),
        maillist=parse_bool_for_moira(get_attribute('is_mailing_list', 'maillist')),
        grouplist=parse_bool_for_moira(get_attribute('is_afs_group', 'grouplist')),
        gid=current_attributes['gid'],
        nfsgroup=parse_bool_for_moira(get_attribute('is_nfs_group', 'nfsgroup')),
        mailman=parse_bool_for_moira(get_attribute('mailman')),
        mailman_server=get_attribute('mailman_server'),
        
        # These should be changeable via
        # other API calls, but not this one
        ace_type=current_attributes['ace_type'],
        ace_name=current_attributes['ace_name'],
        memace_type=current_attributes['memace_type'],
        memace_name=current_attributes['memace_name'],

        description=get_attribute('description'),
        pacslist=get_attribute('is_physical_access', 'pacslist'),
    )
    return 'success'


@app.delete('/lists/<string:list_name>/')
@webathena
@moira_query
@plaintext
def delete_list(list_name, kerb):
    moira.query('delete_list', list_name)
    return 'success'


@app.get('/lists/<string:list_name>/members/')
@webathena
@moira_query
def get_list_members(list_name, kerb):
    recurse = parse_bool(request.args.get('recurse', False))
    query = 'get_end_members_of_list' if recurse else 'get_members_of_list'
    res = moira.query(query, list_name)
    members = {
        'users': [],
        'lists': [],
        'emails': [],
        'kerberos': [],
    }
    for member in res:
        name = member['member_name']
        member_type = member['member_type']
        if member_type == 'USER':
            members['users'].append(name)
        elif member_type == 'LIST':
            members['lists'].append(name)
        elif member_type == 'STRING':
            members['emails'].append(name)
        elif member_type == 'KERBEROS':
            members['kerberos'].append(name)
        else:
            raise Exception(f'unrecognized member type {member_type}')
    return members


@app.put('/lists/<string:list_name>/members/<string:member_name>')
@webathena
@moira_query
def add_member(list_name, member_name, kerb):
    if member_name == 'me':
        member_name = kerb
    member_type = serialize_member_type(request.args.get('type', 'user'))
    moira.query('add_member_to_list', list_name, member_type, member_name)
    return Response('success', status=201, mimetype='text/plain')


@app.delete('/lists/<string:list_name>/members/<string:member_name>')
@webathena
@moira_query
@plaintext
def remove_member(list_name, member_name, kerb):
    if member_name == 'me':
        member_name = kerb
    member_type = serialize_member_type(request.args.get('type', 'user'))
    moira.query('delete_member_from_list', list_name, member_type, member_name)
    return 'success'


@app.get('/lists/<string:list_name>/belongings')
@webathena
@moira_query
def get_list_belongings(list_name, kerb):
    recurse = parse_bool(request.args.get('recurse', True))
    return get_ace_use(conditional_recursive_type('LIST', recurse), list_name)


@app.get('/lists/<string:list_name>/lists')
@webathena
@moira_query
def get_list_lists(list_name, kerb):
    include_properties = request.args.get('include_properties', False)
    recurse = request.args.get('recurse', True)
    res = moira.query('get_lists_of_member', conditional_recursive_type('LIST', recurse), list_name)
    if include_properties:
        return [parse_list_dict(entry) for entry in res]
    else:
        return [entry['list_name'] for entry in res]


@app.get('/lists/<string:list_name>/owner')
@webathena
@moira_query
def get_list_admin(list_name, kerb):
    res = moira.query('get_list_info', list_name)[0]
    return {
        'type': res['ace_type'].lower(),
        'name': res['ace_name'],
    }


@app.put('/lists/<string:list_name>/owner')
@webathena
@moira_query
@plaintext
def set_list_admin(list_name, kerb):
    attributes = create_update_list_input(list_name)
    attributes['ace_type'] = request.json['type'].upper()
    attributes['ace_name'] = request.json['name']
    moira.query('update_list', **attributes)
    return 'success'


@app.get('/lists/<string:list_name>/membership_admin')
@webathena
@moira_query
def get_list_membership_admin(list_name, kerb):
    res = moira.query('get_list_info', list_name)[0]
    if res['memace_type'] == 'NONE':
        return {
            'type': 'none',
        }
    return {
        'type': res['memace_type'].lower(),
        'name': res['memace_name'],
    }

@app.put('/lists/<string:list_name>/membership_admin')
@webathena
@moira_query
@plaintext
def set_list_membership_admin(list_name, kerb):
    attributes = create_update_list_input(list_name)
    attributes['memace_type'] = request.json['type'].upper()
    attributes['memace_name'] = request.json['name']
    moira.query('update_list', **attributes)
    return 'success'


@app.delete('/lists/<string:list_name>/membership_admin')
@webathena
@moira_query
@plaintext
def delete_list_membership_admin(list_name, kerb):
    attributes = create_update_list_input(list_name)
    attributes['memace_type'] = 'NONE'
    attributes['memace_name'] = 'NONE'
    moira.query('update_list', **attributes)
    return 'success'



# TODO: don't do this in production
if __name__ == '__main__':
    app.debug = True
    app.run()
else:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
