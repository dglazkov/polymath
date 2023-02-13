import os

import numpy as np
import pinecone
from library import EXPECTED_EMBEDDING_LENGTH, Bit, Library, vector_from_base64
from overrides import override

# TODO: Make this configurable. Alternatively if we run out of content before
# hitting our content bar, fetch another chunk of content from pinecone until we
# have enough to return as many as the user asked for.
TOP_K = 100


class PineconeConfig:
    def __init__(self, config):
        self.namespace = config['namespace']
        self.index = config.get('index', 'polymath')
        self.environment = config.get('environment', 'us-west1-gcp')
        self.api_key = config.get('api_key', os.getenv("PINECONE_API_KEY"))


class PineconeLibrary(Library):
    def __init__(self, config):
        self.config = PineconeConfig(config)
        super().__init__()

    @override
    def _produce_query_result(self, query_embedding):
        self.omit = 'embedding'
        pinecone.init(
            api_key=self.config.api_key,
            environment=self.config.environment)
        index = pinecone.Index(self.config.index)
        result = index.query(
            namespace=self.config.namespace,
            top_k=TOP_K,
            include_metadata=True,
            vector=query_embedding.tolist()
        )
        for item in result['matches']:
            bit = Bit(data={
                'id': item['id'],
                'text': item['metadata']['text'],
                'token_count': item['metadata'].get('token_count'),
                'access_tag': item['metadata'].get('access_tag'),
                'info': {
                    'url': item['metadata']['url'],
                    'image_url': item['metadata'].get('image_url'),
                    'title': item['metadata'].get('title'),
                    'description': item['metadata'].get('description'),
                }
            })
            self.insert_bit(bit)
