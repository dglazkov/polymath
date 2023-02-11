import json
import os
from typing import Any, Union


class JSONConfigStore:
    def __init__(self):
        self._cache = {}

    def _load(self, filename: str) -> Any:
        if filename in self._cache:
            return self._cache[filename]
        if not os.path.exists(filename):
            return {}
        with open(filename, 'r') as f:
            result = json.load(f)
        self._cache[filename] = result
        return result

    def default(self, config_type) -> str:
        return f'{config_type.__id__}.SECRET.json'

    def get(self, config_type, filename: Union[str, None] = None) -> Any:
        if filename is None:
            filename = self.default(config_type)
        else:
            if not os.path.exists(filename):
                raise Exception(f'Config file "{filename}" does not exist')
        config = self._load(filename)
        return config_type(config)
