
import argparse
import json
import os
import secrets
import base64
import re

DEFAULT_ACCESS_FILE = 'access.SECRET.json'


def generate_token_for_user(user_id):
    base = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8')
    base = base.replace('=', '')
    return 'sk_' + user_id + '_' + base


def save_access_file(data, access_file=DEFAULT_ACCESS_FILE):
    with open(access_file, 'w') as f:
        json.dump(data, f, indent='\t')
    print(f"Don't forget to redeploy with the updated {access_file}")


def load_access_file(access_file=DEFAULT_ACCESS_FILE):
    data = {}
    if os.path.exists(access_file):
        with open(access_file, 'r') as f:
            data = json.load(f)
    return data


def add_token_for_user(user_id, access_file=DEFAULT_ACCESS_FILE, force=False):
    token = generate_token_for_user(user_id)
    data = load_access_file(access_file)
    if 'tokens' not in data:
        data['tokens'] = {}
    tokens = data['tokens']
    if user_id not in tokens:
        tokens[user_id] = {}
    user = tokens[user_id]
    if not force and 'token' in user:
        print('That user already had a token set, so returning that instead of generating a new one. Pass --force to force creating one.')
    else:
        user['token'] = token
        save_access_file(data, access_file)
    print('Pass the following line to the user to add to their client.SECRET.json for this endpoint:')
    print(user['token'])


def revoke_token_for_user(user_id, access_file=DEFAULT_ACCESS_FILE, force=False):
    data = load_access_file(access_file)
    if 'tokens' not in data:
        print(f'{access_file} had no tokens.')
        return
    tokens = data['tokens']
    if user_id not in tokens:
        print(f'{access_file} did not have a user with id {user_id}.')
        return
    user = tokens[user_id]
    if 'token' not in user:
        print(f'{access_file} {user_id} had no token set.')
        return
    if not force:
        print('You must pass --force to remove the token.')
        return
    del user['token']
    save_access_file(data, access_file)
    print(f'Removed the token for {user_id} from {access_file}')    


parser = argparse.ArgumentParser()
parser.add_argument("command", help="The command to run", choices=['add', 'revoke'],
                    default='add')
parser.add_argument("user_id", help="The id of the user to modify")
parser.add_argument("--force", help="Whether to force the action", action="store_true")
parser.add_argument("--file", help="The access file to operate on", default=DEFAULT_ACCESS_FILE)
args = parser.parse_args()

command = args.command
user_id = args.user_id
force = args.force
file = args.file

if command == 'add':
    add_token_for_user(user_id, access_file=file, force=force)
elif command == 'revoke':
    revoke_token_for_user(user_id, access_file=file, force=force)