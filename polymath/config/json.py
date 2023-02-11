import json
import os
from typing import Any
from typing import Union

from polymath.config.types import HostConfig


class JSONConfigStore:
    def __init__(self):
        self._cache = {}

    def load(self, filename: str) -> Any:
        if filename in self._cache:
            return self._cache[filename]
        if not os.path.exists(filename):
            return {}
        with open(filename, 'r') as f:
            result = json.load(f)
        self._cache[filename] = result
        return result


class JSONConfigLoader:
    def __init__(self):
        self._config_store = JSONConfigStore()

    def load(self, config_type, filename: Union[str, None] = None) -> Any:
        if filename is None:
            filename = f'{config_type.__id__}.SECRET.json'
        config = self._config_store.load(filename)
        return config_type(config)
