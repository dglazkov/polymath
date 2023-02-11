from typing import Any

from google.cloud import firestore

from polymath.config.types import HostConfig


class FirestoreConfigStore:
    def load(self, ref) -> Any:
        return ref.get().to_dict()


class FirestoreConfigLoader:
    def __init__(self):
        self._client = firestore.Client()

    def load(self, config_type, path: str = 'sites/127') -> HostConfig:
        """The default is to load the config for the local host."""
        ref = self._client.document(path)
        config = FirestoreConfigStore().load(ref)
        return config_type(config)
