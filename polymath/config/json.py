
import json
import os
from typing import Any
from typing import Union

from polymath.config.types import HostConfig


from polymath.config.types import ConfigTypes, HostConfig

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

    def load_host_config(self, filename: Union[str, None] = None) -> HostConfig:
        if filename is None:
            filename = 'host.SECRET.json'
        config = self._config_store.load(filename)
        return HostConfig(config)


JSON = JSONConfigLoader()
