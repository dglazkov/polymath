from polymath.config.json import JSONConfigStore
from polymath.config.types import HostConfig

DEFAULT_PRIVATE_ACCESS_TAG = 'unpublished'

HOST_CONFIG : HostConfig = JSONConfigStore().load(HostConfig)

def permitted_access(access_token):
    """
    Returns the set of permitted access tags
    """

    if not access_token:
        return set([])

    # TODO: make default_private_access_tag on HOST_CONFIG too.
    private_access_tag = DEFAULT_PRIVATE_ACCESS_TAG

    token_record = None
    for record in HOST_CONFIG.tokens.values():
        if 'token' not in record:
            continue
        if record['token'] == access_token:
            token_record = record
            break

    if not token_record:
        return set([])

    tags = token_record['access_tags'] if 'access_tags' in token_record else [
        private_access_tag]

    return set(tags)