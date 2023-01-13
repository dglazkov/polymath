from pathlib import Path

import ask_embeddings

from .chunker import generate_chunks


class NakedLibraryImporter:
    def get_chunks(self, filename):
        # Will return a generator of (id, chunk) of chunks, possibly missing embedding and token_count.
        data = ask_embeddings.load_data_file(filename)

        chunks = data.get('content')
        if not chunks:
            raise Exception('Data did not have content as expected')
        for id, chunk in chunks.items():
            text = chunk.get('text')
            if not text:
                print('Skipping a row with id ' +
                      id + ' that was missing text')
                continue

            for text_chunk in generate_chunks([[text]]):
                yield (id, {
                    'text': text_chunk,
                    'info': chunk.get('info')
                })

    def output_base_filename(self, input_filename):
        return Path(input_filename).stem
