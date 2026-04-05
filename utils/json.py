import json
from pydantic_core import to_jsonable_python

def jsonify(value):
        return json.dumps(to_jsonable_python(value))