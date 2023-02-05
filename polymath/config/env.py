
import os
from polymath.config.types import ConfigTypes, EnvironmentConfig

from dotenv import load_dotenv

class EnvConfigStore:
    def load(self) -> ConfigTypes:
        return {
            'openai_api_key': os.getenv("OPENAI_API_KEY"),
            'library_filename': os.getenv("LIBRARY_FILENAME"),
        }

class EnvConfigLoader:
    def __init__(self):
        load_dotenv()

    def load_environment_config(self) -> EnvironmentConfig:
        config = EnvConfigStore().load()
        return EnvironmentConfig(config)


Env = EnvConfigLoader()
