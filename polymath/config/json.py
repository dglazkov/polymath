import json
import os
from typing import Any, Union, TypeVar, Callable

T = TypeVar('T', bound=Callable)

class JSONConfigStore:
    def __init__(self, path: str = ''):
        self._cache = {}
        self.path = path

    def _load(self, filename: str) -> Any:
        location = os.path.join(self.path, filename)
        if location in self._cache:
            return self._cache[location]
        if not os.path.exists(location):
            return {}
        with open(location, 'r') as f:
            result = json.load(f)
        self._cache[location] = result
        return result

    def default(self, config_type) -> str:
        return f'{config_type.__id__}.SECRET.json'

    def load(self, config_type : T, filename: Union[str, None] = None) -> T:
        if filename is None:
            filename = self.default(config_type)
        else:
            if not os.path.exists(filename):
                raise Exception(f'Config file "{filename}" does not exist')
        config = self._load(filename)
        return config_type(config)

    def save(self, config: Any, filename: Union[str, None] = None) -> None:
        config_type = type(config)
        if filename is None:
            filename = self.default(config_type)
        location = os.path.join(self.path, filename)
        with open(location, 'w') as f:
            json.dump(config.to_dict(), f, indent=4)
