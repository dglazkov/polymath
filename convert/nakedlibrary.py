from pathlib import Path
from overrides import override

from polymath import Library

from .chunker import generate_chunks
from .base import BaseImporter, GetChunksResult

class NakedLibraryImporter(BaseImporter):

    @override
    def get_chunks(self, directory : str) -> GetChunksResult:
        # Will return a generator of chunks, possibly missing embedding and token_count.
        data = Library.load_data_file(directory)

        chunks = data.get('bits')
        if not chunks:
            raise Exception('Data did not have content as expected')
        for chunk in chunks:
            text = chunk.get('text')
            if not text:
                print('Skipping a row that was missing text')
                continue

            for text_chunk in generate_chunks([[text]]):
                yield {
                    'text': text_chunk,
                    'info': chunk.get('info')
                }

    @override
    def output_base_filename(self, directory : str) -> str:
        return Path(directory).stem
