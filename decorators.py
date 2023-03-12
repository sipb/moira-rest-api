import binascii
from tempfile import NamedTemporaryFile
from flask import request, make_response
import json
import base64
from make_ccache import make_ccache
import os
import moira
import functools
import inspect

"""
Decorator that makes endpoint return plaintext instead of HTML
"""
def plaintext(func):
    # https://realpython.com/primer-on-python-decorators/#who-are-you-really
    # Necessary for Flask
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        orig_response = func(*args, **kwargs)
        response = make_response(orig_response, 200)
        response.mimetype = 'text/plain'
        # https://stackoverflow.com/questions/57296472/how-to-return-plain-text-from-flask-endpoint-needed-by-prometheus
        return response
    
    return wrapped


"""
Decorator that makes sure a webathena token is passed to the request.
API requests accept two forms of passing it:

* "Authorization: webathena [base64-encoded JSON]" header
* "webathena" GET parameter (also base64-encoded JSON)

The username of the authenticated user is passed as a name parameter `kerb`

Pattern inspired by mailto code.
"""
def webathena(func):
    def get_webathena_json() -> dict | None:
        if 'Authorization' in request.headers:
            prefix, auth = request.headers['Authorization'].split(' ')
        elif 'webathena' in request.args:
            auth = request.args['webathena']
        else:
            return None
        return json.loads(base64.b64decode(auth))

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            cred = get_webathena_json()
        except binascii.Error:
            return {'error': {'description': 'Invalid base64 given in "webathena"'}}, 400
        except json.decoder.JSONDecodeError:
            return {'error': {'description': 'base64 does not decode to JSON!'}}, 400
        if not cred:
            from api import app
            # Make local testing easier by using own tickets
            if app.debug:
                return func(*args, **kwargs, kerb=os.environ['USER'])
            else:
                return {'error': {'description': 'No authentication given!'}}, 401
        else:
            # temporary file only exists in "with" scope
            with NamedTemporaryFile(prefix='ccache_') as ccache:
                try:
                    ccache.write(make_ccache(cred))
                    kerb = cred['cname']['nameString'][0]
                except KeyError as e:
                    return {'error': {'description': f'Malformed credential, missing key {e.args[0]}'}}, 400
                ccache.flush()
                os.environ['KRB5CCNAME'] = ccache.name
                response = func(*args, **kwargs, kerb=kerb)

                # Make sure to unset the environment variable, just in case
                del os.environ['KRB5CCNAME']
                return response
    return wrapped


_moira_errors_inverse = {v:k for k,v in moira.errors().items()}
def get_moira_error_name(code):
    return _moira_errors_inverse[code]

def moira_query(func):
    """
    A decorator that opens an authenticated Moira session before the wrapped
    function is executed.

    Afterwards, it parses errors and returns them according to the API spec

    With this decorator combined with @webathena, all you need to do to define
    an API method is to call moira.query with the desired query and then parse
    the output if needed

    Initially taken from mailto code.
    """
    # webmoira2 is one character too long
    CLIENT_NAME = 'python3'

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        # fname = inspect.currentframe().f_code.co_name
        fname = inspect.stack()[0][3]
        moira.connect()
        moira.auth(CLIENT_NAME)
        try:
            response = func(*args, **kwargs)
            moira.disconnect()
            return response
        except moira.MoiraException as e:
            error_code = e.code
            error_message = e.message
            error_name = get_moira_error_name(error_code)
            status_code = 500
            
            # Some special case status codes:
            if error_name == 'MR_PERM':
                status_code = 403
            elif error_name == 'MR_NO_MATCH':
                status_code = 404
            elif error_name == 'MR_IN_USE':
                # i.e. can't delete a list because it is in use
                # the precondition is that it must not have any members etc
                # (i'm unsure if this is the best status code to return, probably not)
                status_code = 412
            elif error_name == 'MR_EXISTS':
                status_code = 409
            
            return {
                'code': error_code,
                'name': error_name,
                'message': error_message,
            }, status_code

    return wrapped


def authenticated_moira(func):
    """
    Decorator that nests both decorators, because Python decorator behavior
    seems inconsistent, and you need to have tickets in order to 
    authenticate with moira
    """
    return webathena(moira_query(func))