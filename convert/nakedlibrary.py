from pathlib import Path

from polymath import Library

from .chunker import generate_chunks


class NakedLibraryImporter:
    def get_chunks(self, filename):
        # Will return a generator of chunks, possibly missing embedding and token_count.
        data = Library.load_data_file(filename)

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

    def output_base_filename(self, input_filename):
        return Path(input_filename).stem
