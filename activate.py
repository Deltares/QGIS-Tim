import json
import os
import subprocess
import sys


env_vars_json = sys.argv[1]
interpreter = sys.argv[2]
port = sys.argv[3]

with open(env_vars_json, "r") as f:
    env_vars = json.loads(f.read())

for key in os.environ:
    os.environ.pop(key)

for key, value in env_vars.items():
    os.environ[key] = value

subprocess.call(f"{interpreter} -m gistim {port}")
