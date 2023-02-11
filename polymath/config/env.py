import os
from typing import Any

from dotenv import load_dotenv


class EnvConfigStore:
    def __init__(self):
        load_dotenv()

    def _load(self) -> Any:
        return {
            key.lower(): value for key, value in os.environ.items()
        }

    def get(self, config_type) -> Any:
        config = self._load()
        return config_type(config)
