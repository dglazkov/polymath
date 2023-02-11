from typing import Any, Union

from google.cloud import firestore


class FirestoreConfigStore:
    def __init__(self):
        self._client = firestore.Client()

    def default(self, config_type) -> str:
        return config_type.__id__

    def load(self, config_type, path: Union[str, None] = None) -> Any:
        if path is None:
            path = self.default(config_type)
        ref = self._client.document(path)
        config = ref.get().to_dict()
        return config_type(config)
