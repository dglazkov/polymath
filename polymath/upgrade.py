

def _upgrade_from_0(library_data):
    if library_data.get('version', 0) == 1:
        return False
    library_data['version'] = 1
    library_data['bits'] = library_data['content']
    del library_data['content']
    sort = library_data.get('sort', {})
    sort_ids = sort.get('ids', [])
    sort_type = sort.get('type', '')
    sort_reversed = sort.get('reversed', False)
    sort_seed = sort.get('seed', '')
    if 'sort' in library_data:
        del library_data['sort']
    bits_dict = library_data.get('bits', {})
    if not sort_ids:
        sort_ids =[key for key in bits_dict.keys()]
    bits = []
    for bit_id in sort_ids:
        bits.append(bits_dict.get(bit_id, {}))
    library_data['bits'] = bits
    if sort_type:
        library_data['sort'] = sort_type
    if sort_reversed:
        library_data['reversed'] = sort_reversed
    if sort_seed:
        library_data['seed'] = sort_seed
    return True

# Each upgrader knows how to upgrade from the version integer at key, up by one
# version.
_UPGRADERS = {
    0: _upgrade_from_0
}

def upgrade_library_data(library_data):
    """"
    Upgrades the library data in place, until it is the highest version
    number it knows how to convert.

    Returns True if changes were made, False otherwise
    """
    upgrader = _UPGRADERS.get(library_data.get('version', 0), None)
    changes_made = False
    while upgrader:
        upgrader_changes_made = upgrader(library_data)
        if not upgrader_changes_made:
            # Nothing changed; avoid an infinite loop
            return changes_made
        changes_made = True
        upgrader = _UPGRADERS.get(library_data.get('version', 0), None)

    return changes_made


