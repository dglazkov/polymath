from polymath.config.json import JSONConfigStore
from polymath.config.types import HostConfig

DEFAULT_PRIVATE_ACCESS_TAG = 'unpublished'

HOST_CONFIG = JSONConfigStore().load(HostConfig)

def permitted_access(access_token):
    """
    Returns the set of permitted access tags
    """

    if not access_token:
        return set([])


    set_default_private_access_tag = HOST_CONFIG.default_private_access_tag

    private_access_tag = set_default_private_access_tag if set_default_private_access_tag else DEFAULT_PRIVATE_ACCESS_TAG

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