
import argparse
import json
import os
import secrets
import base64
import re

DEFAULT_ACCESS_FILE = 'access.SECRET.json'

# TODO: allow this to be specified
access_file = DEFAULT_ACCESS_FILE


def generate_token_for_user(user_id):
    base = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8')
    base = base.replace('=', '')
    return 'sk_' + user_id + '_' + base


def save_access_file(data):
    with open(access_file, 'w') as f:
        json.dump(data, f, indent='\t')
    print(f"Don't forget to redeploy with the updated {access_file}")

def add_token_for_user(user_id):
    token = generate_token_for_user(user_id)
    data = {}
    if os.path.exists(access_file):
        with open(access_file, 'r') as f:
            data = json.load(f)
    if 'tokens' not in data:
        data['tokens'] = {}
    tokens = data['tokens']
    if user_id not in tokens:
        tokens[user_id] = {}
    user = tokens[user_id]
    if 'token' in user:
        print('That user already had a token set, so returning that instead of generating a new one.')
    else:
        user['token'] = token
        save_access_file(data)
    print('Pass the following line to the user to add to their client.SECRET.json for this endpoint:')
    print(user['token'])


parser = argparse.ArgumentParser()
parser.add_argument("command", help="The command to run", choices=['add'],
                    default='add')
parser.add_argument("user_id", help="The id of the user to modify")
args = parser.parse_args()

command = args.command
user_id = args.user_id

if command == 'add':
    add_token_for_user(user_id)