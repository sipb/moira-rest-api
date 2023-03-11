import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index_get():
    return {
        'hello': 'world',
        'name': request.args.get('name'),
    }

if __name__ == '__main__':
    app.run(debug=True)