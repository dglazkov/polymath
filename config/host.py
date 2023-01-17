
import argparse
import json
import os
import secrets
import base64
import re

DEFAULT_CONFIG_FILE = 'host.SECRET.json'

# A map of property name to example
SETTABLE_PROPERTIES = {
    'endpoint': 'https://example.com',
    'restricted.message': 'Contact alex@komoroske.com for a token'
}

BOOLEAN_STRINGS = {
    'true': True,
    'false': False,
    '0': False,
    '1': True
}

def generate_token_for_user(user_id):
    base = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    base = base.replace('=', '')
    base = base.replace('-', '_')
    safe_user_id = user_id.replace('@', '_at_')
    safe_user_id = re.sub(r'[^a-zA-Z0-9_]', '_', safe_user_id)
    return 'sk_' + safe_user_id + '_' + base


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
    changes_made = False
    if 'token' in user:
        if force:
            user['token'] = token
            changes_made = True
        else:
            print('That user already had a token set, so returning that instead of generating a new one. Pass --force to force creating one.')
    else:
        user['token'] = token
        changes_made = True

    if tags:
        if 'access_tags' not in user or user['access_tags'] != tags:
            print(f'Setting access tags to {tags}')
            user['access_tags'] = tags
    else:
        if 'access_tags' in user:
            print('Removing access_tags and setting to default')
            del user['access_tags']
            changes_made = True

    if changes_made:
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

    if len(user) == 0:
        del tokens[user_id]

    save_config_file(data, access_file)
    print(f'Removed the token for {user_id} from {access_file}')    


def access_command(args):
    command = args.command
    user_id = args.user_id
    force = args.force
    file = args.file
    tags = args.access_tags
    if command == 'grant':
        add_token_for_user(user_id, tags=tags, access_file=file, force=force)
    elif command == 'revoke':
        revoke_token_for_user(user_id, access_file=file, force=force)
    else:
        print(f'Unknown command {command}')


def set_property_in_data(data, property, value):
    property_parts = property.split('.')
    if len(property_parts) == 1:
        data[property] = value
        return
    first_property_part = property_parts[0]
    rest = '.'.join(property_parts[1:])
    if first_property_part not in data:
        data[first_property_part] = {}
    set_property_in_data(data[first_property_part], rest, value)
        

def unset_property_in_data(data, property):
    """
    Returns True if it made a change, False if not
    """
    property_parts = property.split('.')
    if len(property_parts) == 1:
        if property in data:
            del data[property]
            return True
        return False
    first_property_part = property_parts[0]
    rest = '.'.join(property_parts[1:])
    if first_property_part not in data:
        return False
    result = unset_property_in_data(data[first_property_part], rest)
    if len(data[first_property_part]) == 0:
        del data[first_property_part]
    return result


def set_command(args):
    property = args.property
    value = args.value
    original_value = args.value
    config_for_property = SETTABLE_PROPERTIES[property]
    access_file = args.file
    if isinstance(config_for_property, int):
        value = int(value)
    if isinstance(config_for_property, bool):
        if value not in BOOLEAN_STRINGS:
            known_strings = list(BOOLEAN_STRINGS.keys())
            raise Exception(f'Unknown value for a boolean property: {value} (known values are {known_strings})')
        value = BOOLEAN_STRINGS[value]
    data = load_config_file(access_file)
    set_property_in_data(data, property, value)
    save_config_file(data, access_file=access_file)
    print(f'Set {property} to {original_value}')


def unset_command(args):
    property = args.property
    access_file = args.file
    data = load_config_file(access_file)
    made_change = unset_property_in_data(data, property)
    if not made_change:
        print(f'{property} was not configured, nothing to do')
        return
    save_config_file(data, access_file=access_file)
    print(f'Unset {property}')


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
access_parser.add_argument("access_tags", help="Optional access tags to set", nargs='*')
access_parser.set_defaults(func=access_command)
set_parser = sub_parser.add_parser('set', parents=[base_parser])
set_parser.add_argument('property', help='The name of the property to set', choices=list(SETTABLE_PROPERTIES.keys()))
set_parser.add_argument('value', help='The value to set')
set_parser.set_defaults(func=set_command)
unset_parser = sub_parser.add_parser('unset', parents=[base_parser])
unset_parser.add_argument('property', help='The name of the property to unset', choices=list(SETTABLE_PROPERTIES.keys()))
unset_parser.set_defaults(func=unset_command)

args = parser.parse_args()
args.func(args)