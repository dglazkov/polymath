from typing import Union, TypeVar, Callable

from google.cloud import firestore

T = TypeVar('T', bound=Callable)

class FirestoreConfigStore:
    def __init__(self):
        self._client = firestore.Client()

    def default(self, config_type) -> str:
        return config_type.__id__

    def load(self, config_type: T, path: Union[str, None] = None) -> T:
        if path is None:
            path = self.default(config_type)
        ref = self._client.document(path)
        config = ref.get().to_dict()
        return config_type(config)
