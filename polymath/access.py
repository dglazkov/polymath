import os
import json

DEFAULT_CONFIG_FILE = 'host.SECRET.json'
DEFAULT_PRIVATE_ACCESS_TAG = 'unpublished'

access_data = None


def _get_access_data():
    if access_data:
        return access_data
    # TODO: allow overriding this
    access_file = DEFAULT_CONFIG_FILE
    if not os.path.exists(access_file):
        return {}
    with open(DEFAULT_CONFIG_FILE, 'r') as f:
        access_data = json.load(f)
    return access_data


def permitted_access(access_token):
    """
    Returns the set of permitted access tags, whether to include restricted_count in the result,
    and a message to return in the library if any results were filtered.
    """

    data = _get_access_data()

    restricted = data.get('restricted', {})
    include_restricted_count = restricted.get('count', False)
    restricted_message = restricted.get('message', "")

    if not access_token:
        return set([]), include_restricted_count, restricted_message

    if 'tokens' not in data:
        raise Exception(
            f'The data in {DEFAULT_CONFIG_FILE} did not contain a key of "tokens" as expected')

    private_access_tag = data['default_private_access_tag'] if 'default_private_access_tag' in data else DEFAULT_PRIVATE_ACCESS_TAG

    token_record = None
    for record in data['tokens'].values():
        if 'token' not in record:
            continue
        if record['token'] == access_token:
            token_record = record
            break

    if not token_record:
        return set([]), include_restricted_count, restricted_message

    tags = token_record['access_tags'] if 'access_tags' in token_record else [
        private_access_tag]

    return set(tags), include_restricted_count, restricted_message