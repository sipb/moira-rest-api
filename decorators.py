import binascii
from tempfile import NamedTemporaryFile
from flask import request, make_response
import json
import base64
from make_ccache import make_ccache
import os

"""
Decorator that makes endpoint return plaintext instead of HTML
"""
def plaintext(func):
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

    def wrapped(*args, **kwargs):
        # Just in case, clear environment variable (defensively)
        if 'KRB5CCNAME' in os.environ:
            del os.environ['KRB5CCNAME']

        try:
            cred = get_webathena_json()
        except binascii.Error:
            return {'error': 'Invalid base64 given in "webathena"'}, 400
        except json.decoder.JSONDecodeError:
            return {'error': 'base64 does not decode to JSON!'}, 400
        if not cred:
            return {'error': 'No authentication given!'}, 404
        else:
            # temporary file only exists in "with" scope
            with NamedTemporaryFile(prefix='ccache_') as ccache:
                try:
                    ccache.write(make_ccache(cred))
                except KeyError as e:
                    return {'error': f'Malformed credential, missing key {e.args[0]}'}
                ccache.flush()
                os.environ['KRB5CCNAME'] = ccache.name
                return func(*args, **kwargs)
    return wrapped