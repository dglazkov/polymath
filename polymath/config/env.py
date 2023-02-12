import os
from typing import Any, TypeVar, Callable

from dotenv import load_dotenv

T = TypeVar('T', bound=Callable)

class EnvConfigStore:
    def __init__(self):
        load_dotenv()

    def _load(self) -> Any:
        return {
            key.lower(): value for key, value in os.environ.items()
        }

    def load(self, config_type: T) -> T:
        config = self._load()
        return config_type(config)
