import moira

"""
Several utilities (i.e. helper functions) for use
in the Flask Moira API
"""

def get_ace_use(ace_type, name):
    res = moira.query('get_ace_use', ace_type, name)
    return [
        {
            'type': entry['use_type'],
            'name': entry['use_name'],
        }
        for entry in res
    ]

def conditional_recursive_type(ace_type, recursive):
    if recursive:
        return 'R' + ace_type
    else:
        return ace_type

"""
Parse a GET parameter as bool
"""
def parse_bool(param):
    if isinstance(param, bool):
        return param
    if param == 1 or param == '1' or param.lower() == 'true':
        return True
    elif param == 0 or param == '0' or param.lower() == 'false':
        return False
    else:
        raise Exception(f'invalid boolean: {param}')


"""
Parses a mailing list entry dict
into the names we want for our API
"""
def parse_list_dict(entry):
    return {
        'name': entry['list_name'],
        'active': parse_bool(entry['active']),
        'public': parse_bool(entry['publicflg']),
        'hidden': parse_bool(entry['hidden']),
        'is_mailing_list': parse_bool(entry['maillist']),
        'is_afs_group': parse_bool(entry['grouplist']),
    }


"""
Parse a parameter as a bool-like "1" or "0"
for use in Moira queries
"""
def parse_bool_for_moira(param):
    if param == True or param == 1 or param == '1':
        return '1'
    elif param == False or param == 0 or param == '0':
        return '0'
    else:
        raise Exception(f'invalid boolean: {param}')


"""
Converts from REST API format of member type
to the format Moira wants
(user to USER, email to STRING, etc)
"""
def serialize_member_type(member_type):
    if member_type == 'email':
        member_type = 'string'
    return member_type.upper()


"""
Converts to Moira format to format REST API
defines (USER to user, STRING to email, etc)
"""
def parse_member_type(member_type):
    if member_type == 'STRING':
        member_type = 'EMAIL'
    return member_type.lower()


"""
From the output of get_list_info, prepare it as input
for update_list. If this is passed without modification
to update_list, it should be a no-op.
"""
def create_update_list_input(list_name):
    # Get current attributes
    attributes = moira.query('get_list_info', list_name)[0]
    # Delete modified attributes
    del attributes['modtime']
    del attributes['modby']
    del attributes['modwith']
    # Set name format
    del attributes['name']

    # Order matters! We want name and new name at the beginning
    input = {}
    input['name'] = list_name
    input['newname'] = list_name

    for k, v in attributes.items():
        input[k] = v
    return input
