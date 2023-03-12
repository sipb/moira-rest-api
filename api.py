import subprocess
from flask import Flask, request
from decorators import webathena, plaintext, moira_query
import moira

app = Flask(__name__)

# I wanted to separate this into multiple files, but it seems
# non-trivial: 
# https://www.reddit.com/r/flask/comments/m3kp1i/splitting_flask_app_into_multiple_files/
# https://flask.palletsprojects.com/en/2.2.x/patterns/appfactories/
# So I think one file will suffice

@app.get('/test')
@webathena
@plaintext
def test():
    result = subprocess.run('klist', stdout=subprocess.PIPE)
    return result.stdout.decode()

@app.errorhandler(404)
def not_found(error):
    return {
        'name': 'METHOD_NOT_FOUND',
        'description': f'{error}',
    }

@app.get('/users/<string:user>')
@webathena
@moira_query
def get_user(user):
    res = moira.query('get_user_by_login', user)
    assert len(res) == 1
    return res[0]

# TODO: don't do this in production
app.debug = True
if __name__ == '__main__':
    app.run()