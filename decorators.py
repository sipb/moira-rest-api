import binascii
from tempfile import NamedTemporaryFile
from flask import request, make_response
import json
import base64
from make_ccache import make_ccache
import os
import moira
import functools

from moira_query import moira_query_modwith


def plaintext(func):
    """
    Decorator that makes endpoint return plaintext instead of HTML
    """
    
    # https://realpython.com/primer-on-python-decorators/#who-are-you-really
    # Necessary for Flask
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        orig_response = func(*args, **kwargs)
        # https://stackoverflow.com/questions/57296472/how-to-return-plain-text-from-flask-endpoint-needed-by-prometheus
        response = make_response(orig_response, 200)
        response.mimetype = 'text/plain'
        return response
    
    return wrapped


def jsoned(func):
    """
    Decorator that makes endpoint return JSON
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        orig_response = func(*args, **kwargs)
        json_response = orig_response \
            if isinstance(orig_response, str) or isinstance(orig_response, bytes) \
            else json.dumps(orig_response)
        response = make_response(json_response, 200)
        response.mimetype = 'application/json'
        return response
    return wrapped


def webathena(func):
    """
    Decorator that makes sure a webathena token is passed to the request.
    API requests accept two forms of passing it:

    * "Authorization: webathena [base64-encoded JSON]" header
    * "webathena" GET parameter (also base64-encoded JSON)

    The username of the authenticated user is passed as a name parameter `kerb`

    Pattern inspired by mailto code.
    """

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
                # Only if it exists that is
                if 'KRB5CCNAME' in os.environ:
                    del os.environ['KRB5CCNAME']
                return response
    return wrapped


_moira_errors_inverse = {v:k for k,v in moira.errors().items()}
def get_moira_error_name(code):
    return _moira_errors_inverse.get(code) or 'unknown error'

def moira_errors(func):
    """
    A decorator that parses Moira errors and returns them
    according to the API spec (as a Flask result, status code tuple)
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            return response
        except moira.MoiraException as e:
            error_code = e.code
            # TODO: re-contribute e.message to the moira api
            error_message = e.args[1].decode()
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


# TODO: I can't *wrap* (drum roll) my head around if this decorator should come before or after
# webathena
def allow_changing_modwith(func):
    """
    A decorator that passes a moira_query as first parameter to the decorated function
    that will be a moira_query function but with a modified modwith.

    It would use the default modwith of `python3`, unless the `modwith` header is 
    overriden.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if 'modwith' in request.headers:            
            modwith = request.headers['modwith']
        else:
            modwith = "python3"
        def moira_query(*args, **kwargs):
            return moira_query_modwith(modwith, *args, **kwargs)
        return func(moira_query, *args, **kwargs)

    return wrapped


def authenticated_moira(func):
    """
    Decorator that nests both decorators, because Python decorator behavior
    seems inconsistent, and you need to have tickets in order to 
    authenticate with moira
    """
    return webathena(moira_errors(allow_changing_modwith(func)))