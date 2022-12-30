import ask_embeddings
import os

class NakedLibraryImporter:
    def get_chunks(self, filename, existing_library, max_lines = -1):
        # Will return a generator of (id, chunk) of chunks, possibly missing embedding and token_count.
        data = ask_embeddings.load_data_file(filename)

        chunks = data.get('content')
        if not chunks:
            raise Exception('Data did not have content as expected')
        count = 0
        total = len(chunks) if max_lines < 0 else max_lines
        for id, chunk in chunks.items():
            if max_lines >= 0 and count >= max_lines:
                print('Reached max lines')
                break
            if id in existing_library['content']:
                continue
            print(f'Processing new chunk {id} ({count + 1}/{total})')
            text = chunk.get('text')
            if not text:
                print('Skipping a row with id ' + id + ' that was missing text')
                continue
            yield (id, {
                    'text': text,
                    'info': chunk.get('info')
            })
            count += 1
    def output_base_filename(self, input_filename):
        base_filename, file_extension = os.path.splitext(input_filename)
        return base_filename