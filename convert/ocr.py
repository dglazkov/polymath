import pytesseract

from pathlib import Path
from argparse import Namespace
from .chunker import generate_chunks

class OCRImporter:

    def __init__(self):
      self._debug = False

    def retrieve_arguments(self, args: Namespace):
        self._debug = args.debug

    def output_base_filename(self, input_filename):
        return Path(input_filename).stem

    def get_chunks(self, filename):
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
   
    
