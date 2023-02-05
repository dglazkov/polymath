from google.cloud import firestore

from polymath.config.types import ConfigTypes, HostConfig


class FirestoreConfigStore:
    def load(self, ref) -> ConfigTypes:
        return ref.get().to_dict()


class FirestoreConfigLoader:
    def __init__(self):
        self._client = firestore.Client()

    def load_host_config(self, ref: firestore.DocumentReference = None) -> HostConfig:
        if ref is None:
            ref = self._client.document('sites/127')
        config = FirestoreConfigStore().load(ref)
        return HostConfig(config)


Firestore = FirestoreConfigLoader()
