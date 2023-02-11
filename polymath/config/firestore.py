from typing import Any, Union

from google.cloud import firestore


class FirestoreConfigStore:
    def __init__(self):
        self._client = firestore.Client()

    def get(self, config_type, path: Union[str, None] = None) -> Any:
        if path is None:
            path = config_type.__id__
        ref = self._client.document(path)
        config = ref.get().to_dict()
        return config_type(config)
