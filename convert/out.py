
import os
import pinecone
import argparse

from polymath import Library
from dotenv import load_dotenv
import numpy as np


load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = "us-west1-gcp"  # TODO: Make this configurable
VECTOR_DIMENSIONS = 1536
BATCH_SIZE = 100 # Size of the vector batch to send to Pinecone


class NullExporter:
    def start(self, args):
        pass

    def export_bit(self, bit):
        pass

    def finish(self):
        pass

    def install_args(self, parser):
        pass


class PineconeExporter:
    def __init__(self) -> None:
        self.index_name = None
        self.namespace = None
        self.vectors = []

    def start(self, args: argparse.Namespace) -> None:
        self.index_name = args.index
        self.namespace = args.namespace
        return True

    def install_args(self, parser: argparse.ArgumentParser):
        parser.add_argument('--index',
                            help='Name of Pinecone index to export to',
                            default='polymath')
        parser.add_argument('--namespace',
                            help='Pinecone index namespace to export to',
                            default=None)

    def export_bit(self, bit):
        metadata = {
            'text': bit.text,
            'url': bit.info.url,
        }
        if bit.info.image_url:
            metadata['image_url'] = bit.info.image_url
        if bit.info.title:
            metadata['title'] = bit.info.title
        if bit.info.description:
            metadata['description'] = bit.info.description
        if bit.token_count:
            metadata['token_count'] = bit.token_count
        if bit.access_tag:
            metadata['access_tag'] = bit.access_tag

        embedding = bit.embedding.tolist()
        self.vectors.append((bit.id, embedding, metadata))

    def finish(self):
        def make_batches(vectors, size):
            for i in range(0, len(vectors), size):
                yield vectors[i:i + size]

        pinecone.init(
            api_key=PINECONE_API_KEY,
            environment=PINECONE_ENVIRONMENT)
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(self.index_name, dimension=VECTOR_DIMENSIONS)
        index = pinecone.Index(self.index_name)
        for batch in make_batches(self.vectors, BATCH_SIZE):
            index.upsert(
                vectors=batch,
                namespace=self.namespace)


EXPORTERS = {
    'pinecone': PineconeExporter(),
}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exporter',
                        help='Which exporter to use',
                        choices=EXPORTERS.keys(),
                        required=True)
    parser.add_argument('--library',
                        help='Path to library file to export',
                        required=True)
    [exporter.install_args(parser) for exporter in EXPORTERS.values()]
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()

    exporter = EXPORTERS.get(args.exporter, NullExporter)
    print(f'Starting exporter "{args.exporter}" ...')
    if not exporter.start(args):
        print('Failed to set up exporter')
        exit(1)
    library = Library(filename=args.library)
    for bit in library.bits:
        print(f'Exporting bit {bit.id} ...')
        exporter.export_bit(bit)
    print('Finishing export ...')
    exporter.finish()
    print('Done!')
