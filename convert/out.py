import os
import pinecone
import argparse
from overrides import override

from polymath import Library, Bit
from dotenv import load_dotenv


load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = "us-west1-gcp"  # TODO: Make this configurable
VECTOR_DIMENSIONS = 1536
BATCH_SIZE = 100 # Size of the vector batch to send to Pinecone


class BaseExporter:
    def start(self, args : argparse.Namespace) -> None:
        pass

    def export_bit(self, bit : Bit):
        pass

    def finish(self):
        pass

    def install_args(self, parser : argparse.ArgumentParser):
        pass


class PineconeExporter(BaseExporter):
    def __init__(self) -> None:
        self.index_name = None
        self.namespace = None
        self.vectors = []

    @override
    def start(self, args: argparse.Namespace) -> None:
        self.index_name = args.index
        self.namespace = args.namespace

    @override
    def install_args(self, parser: argparse.ArgumentParser):
        parser.add_argument('--index',
                            help='Name of Pinecone index to export to',
                            default='polymath')
        parser.add_argument('--namespace',
                            help='Pinecone index namespace to export to',
                            default=None)

    @override
    def export_bit(self, bit : Bit):
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

        raw_embedding = bit.embedding
        if not raw_embedding:
            return

        embedding = raw_embedding.tolist()
        self.vectors.append((bit.id, embedding, metadata))

    @override
    def finish(self):
        def make_batches(vectors, size):
            for i in range(0, len(vectors), size):
                yield vectors[i:i + size]

        api_key = PINECONE_API_KEY
        if not api_key:
            raise Exception('No pinecone key provided')
        
        index_name = self.index_name

        if not index_name:
            raise Exception('No index name provided')

        pinecone.init(
            api_key=api_key,
            environment=PINECONE_ENVIRONMENT)
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(index_name, dimension=VECTOR_DIMENSIONS)
        index = pinecone.Index(index_name)
        for batch in make_batches(self.vectors, BATCH_SIZE):
            index.upsert(
                vectors=batch,
                namespace=self.namespace)


EXPORTERS : dict[str, BaseExporter] = {
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

    exporter = EXPORTERS.get(args.exporter, BaseExporter())
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
