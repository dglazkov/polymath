import ask_embeddings
import os

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
                print('Skipping a row with id ' + id + ' that was missing text')
                continue
            yield (id, {
                    'text': text,
                    'info': chunk.get('info')
            })
    def output_base_filename(self, input_filename):
        base_filename, file_extension = os.path.splitext(input_filename)
        return base_filename