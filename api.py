import json
import subprocess
from flask import Flask, request, jsonify
from decorators import webathena, plaintext

app = Flask(__name__)

@app.get('/test')
@webathena
@plaintext
def test():
    result = subprocess.run('klist', stdout=subprocess.PIPE)
    return result.stdout.decode()

@app.route('/')
def index():
    return {
        'hello': 'world',
        'name': request.args.get('name'),
    }

if __name__ == '__main__':
    app.run(debug=True)