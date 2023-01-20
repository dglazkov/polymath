
import argparse
import json
import os

DEFAULT_CONFIG_FILE = 'directory.SECRET.json'

# A map of property name to example
HOST_SETTABLE_PROPERTIES = {
    'endpoint': 'https://example.com',
    'token': 'sk-SECRET-token',
    'dev_endpoint': 'http://127.0.0.1:8080',
    'note': 'Any extra information you want to store about the host'
}

FORCE_PROPERTIES = ['token']

# TODO: factor to share with host.py
BOOLEAN_STRINGS = {
    'true': True,
    'false': False,
    '0': False,
    '1': True
}

# TODO: factor to share with host.py
def save_config_file(data, access_file=DEFAULT_CONFIG_FILE):
    with open(access_file, 'w') as f:
        json.dump(data, f, indent='\t')


# TODO: factor to share with host.py
def load_config_file(access_file=DEFAULT_CONFIG_FILE):
    data = {}
    if os.path.exists(access_file):
        with open(access_file, 'r') as f:
            data = json.load(f)
    return data

# TODO: factor to share with host.py
def set_property_in_data(data, property, value):
    property_parts = property.split('.')
    if len(property_parts) == 1:
        if property in data and data[property] == value:
            return False
        data[property] = value
        return True
    first_property_part = property_parts[0]
    rest = '.'.join(property_parts[1:])
    if first_property_part not in data:
        data[first_property_part] = {}
    return set_property_in_data(data[first_property_part], rest, value)
        
# TODO: factor to share with host.py
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


def get_property_in_data(data, property):
    """
    Returns the value or None if it doesn't exit
    """
    property_parts = property.split('.')
    if len(property_parts) == 1:
        return data.get(property, None)
    first_property_part = property_parts[0]
    rest = '.'.join(property_parts[1:])
    if first_property_part not in data:
        return None
    return get_property_in_data(data[first_property_part], rest)


def host_name_from_input(input : str, data):
    """
    Returns the short_name where this host is stored.

    input may be the short_name, or an endpoint.

    returns the hostname and a boolean of whether it exists or not
    """
    hosts = data.get('hosts', {})
    input = input.lower()
    # It's a straightforward short_name
    if input in hosts:
        return input, True
    for id, value in hosts.items():
        if value.get('endpoint', None) == input:
            return id, True
        if value.get('dev_endpoint', None) == input:
            return id, True
    # TODO: suggest other names based on edit distance?
    # We don't have a name, but let's see if we can suggest one if it's an endpoint url.
    if not input.startswith('http'):
        return None, False
    input = input.removeprefix('https://')
    input = input.removeprefix('http://')
    parts = input.split('.')
    # throw out the TLD
    parts = parts[:-1]
    # throw out the polymath subdomain if it starts with that
    if parts[0] == 'polymath':
        parts = parts[1:]
    if len(parts) == 0:
        return None, False
    return parts[0], False


def host_property(host_name, property):
    return 'hosts.' + host_name + '.' + property


def host_set_command(args):
    access_file = args.file
    data = load_config_file(access_file)
    raw_host = args.host
    host_name, host_exists = host_name_from_input(raw_host, data)
    if not host_name:
        print(f'{raw_host} was not a valid host_name or endpoint')
        return
    if not host_exists:
        if not args.create:
            print(f'{raw_host} did not exist yet. If you pass --create, will create a new host with the short_name {host_name}')
            return
        endpoint_property = host_property(host_name, 'endpoint')
        set_property_in_data(data, endpoint_property, raw_host)
        print(f'Set {endpoint_property} to {raw_host}')
    property = host_property(host_name, args.property)
    value = args.value
    original_value = args.value
    config_for_property = HOST_SETTABLE_PROPERTIES[args.property]
    if isinstance(config_for_property, bool):
        value = value.lower()
        if value not in BOOLEAN_STRINGS:
            known_strings = list(BOOLEAN_STRINGS.keys())
            raise Exception(f'Unknown value for a boolean property: {value} (known values are {known_strings})')
        value = BOOLEAN_STRINGS[value]
    elif isinstance(config_for_property, int):
        value = int(value)
    changes_made = set_property_in_data(data, property, value)
    if not changes_made:
        print(f'{property} was already set to {value} so no changes to be made.')
        return
    save_config_file(data, access_file=access_file)
    print(f'Set {property} to {original_value}')


def host_unset_command(args):
    access_file = args.file
    data = load_config_file(access_file)
    raw_host = args.host
    host_name, _ = host_name_from_input(raw_host, data)
    if not host_name:
        print(f'{raw_host} was not a valid host_name or endpoint')
        return
    property = host_property(host_name, args.property)
    if get_property_in_data(data, property) == None:
        print(f'{property} was not configured, nothing to do')
        return
    force = args.force
    raw_property = args.property
    if raw_property in FORCE_PROPERTIES and not force:
        print(f'You must use --force to unset {raw_property}')
        return
    unset_property_in_data(data, property)
    save_config_file(data, access_file=access_file)
    print(f'Unset {property}')

def host_show_command(args):
    access_file = args.file
    data = load_config_file(access_file)
    raw_host = args.host
    host_name, _ = host_name_from_input(raw_host, data)
    if not host_name:
        print(f'{raw_host} was not a valid host_name or endpoint')
        return
    property = host_property(host_name, args.property)
    value = get_property_in_data(data, property)
    if value == None:
        print(f'{property} was not set')
        return
    print(f'{property} is set to:')
    print(f'{value}')


parser = argparse.ArgumentParser()

base_parser = argparse.ArgumentParser(add_help=False)
base_parser.add_argument("--file", help="The config file to operate on", default=DEFAULT_CONFIG_FILE)
base_parser.add_argument("--force", help="Forces the action", action="store_true")

sub_parser = parser.add_subparsers(title='action')
sub_parser.required = True
host_set_parser = sub_parser.add_parser('set', parents=[base_parser])
host_set_parser.add_argument('--create', help='Whether to create a new host entry from the endpoint if one doesn\'t exist', action='store_true')
host_set_parser.add_argument('host', help='The vanity name or endpoint of the host to set the property on')
host_set_parser.add_argument('property', help='The name of the property to set', choices=list(HOST_SETTABLE_PROPERTIES.keys()))
host_set_parser.add_argument('value', help='The value to set')
host_set_parser.set_defaults(func=host_set_command)
host_unset_parser = sub_parser.add_parser('unset', parents=[base_parser])
host_unset_parser.add_argument('host', help='The vanity name or endpoint of the host to unset the property on')
host_unset_parser.add_argument('property', help='The name of the property to unset', choices=list(HOST_SETTABLE_PROPERTIES.keys()))
host_unset_parser.set_defaults(func=host_unset_command)
host_show_parser = sub_parser.add_parser('show', parents=[base_parser])
host_show_parser.add_argument('host', help='The vanity name or endpoint of the host to show the property of')
host_show_parser.add_argument('property', help='The name of the property to show', choices=list(HOST_SETTABLE_PROPERTIES.keys()))
host_show_parser.set_defaults(func=host_show_command)

args = parser.parse_args()
args.func(args)