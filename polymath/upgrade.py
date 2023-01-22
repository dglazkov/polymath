

def _upgrade_from_0(library_data):
    if library_data.get('version', 0) == 1:
        return False
    library_data['version'] = 1
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


