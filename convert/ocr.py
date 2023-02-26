import pytesseract

from pathlib import Path
from argparse import Namespace
from .chunker import generate_chunks
from overrides import override

from .base import BaseImporter, GetChunksResult

class OCRImporter(BaseImporter):

    def __init__(self):
      self._debug = False

    @override
    def retrieve_arguments(self, args: Namespace):
        self._debug = args.debug

    @override
    def output_base_filename(self, filename) -> str:
        return Path(filename).stem

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        try:
            friendly_filename = Path(filename).stem

            # Currently assumes eng. TODO: add language support.
            text = pytesseract.image_to_string(filename, config='--oem 1 --psm 6')
  
            if self._debug == True:
                print(f'DEBUG: {text}')
  
            for chunk in generate_chunks([[text]]):
                yield {
                    "text": chunk,
                    "info": {
                        "url": friendly_filename,
                        "title": friendly_filename
                    }
                }
        except pytesseract.TesseractNotFoundError:
            # Tesseract not found.
            print("Tesseract not found.")
   
    
