
import argparse
import json
import os
import secrets
import base64

DEFAULT_CONFIG_FILE = 'host.SECRET.json'


def generate_token_for_user(user_id):
    base = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8')
    base = base.replace('=', '')
    return 'sk_' + user_id + '_' + base


def save_config_file(data, access_file=DEFAULT_CONFIG_FILE):
    with open(access_file, 'w') as f:
        json.dump(data, f, indent='\t')
    print(f"Don't forget to redeploy with the updated {access_file}")


def load_config_file(access_file=DEFAULT_CONFIG_FILE):
    data = {}
    if os.path.exists(access_file):
        with open(access_file, 'r') as f:
            data = json.load(f)
    return data


def add_token_for_user(user_id, tags=None, access_file=DEFAULT_CONFIG_FILE, force=False):
    token = generate_token_for_user(user_id)
    data = load_config_file(access_file)
    if not tags or len(tags) == 0:
        tags = None
    if 'tokens' not in data:
        data['tokens'] = {}
    tokens = data['tokens']
    if user_id not in tokens:
        tokens[user_id] = {}
    user = tokens[user_id]
    if not force and 'token' in user:
        print('That user already had a token set, so returning that and leaving it unmodified instead of generating a new one. Pass --force to force creating one.')
    else:
        user['token'] = token
        if tags:
            user['access_tags'] = tags
        elif 'access_tags' in user:
            del user['access_tags']
        save_config_file(data, access_file)
    print('Pass the following line to the user to add to their client.SECRET.json for this endpoint:')
    print(user['token'])


def revoke_token_for_user(user_id, access_file=DEFAULT_CONFIG_FILE, force=False):
    data = load_config_file(access_file)
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
    save_config_file(data, access_file)
    print(f'Removed the token for {user_id} from {access_file}')    


def access_command(args):
    command = args.command
    user_id = args.user_id
    force = args.force
    file = args.file
    if command == 'grant':
        add_token_for_user(user_id, access_file=file, force=force)
    elif command == 'revoke':
        revoke_token_for_user(user_id, access_file=file, force=force)
    else:
        print(f'Unknown command {command}')


parser = argparse.ArgumentParser()

base_parser = argparse.ArgumentParser(add_help=False)
base_parser.add_argument("--force", help="Whether to force the action", action="store_true")
base_parser.add_argument("--file", help="The config file to operate on", default=DEFAULT_CONFIG_FILE)

sub_parser = parser.add_subparsers(title='action')
sub_parser.required = True
access_parser = sub_parser.add_parser('access', parents=[base_parser])
access_parser.add_argument("command", help="The command to run", choices=['grant', 'revoke'],
                    default='grant')
access_parser.add_argument("user_id", help="The id of the user to modify")
access_parser.set_defaults(func=access_command)

args = parser.parse_args()
args.func(args)