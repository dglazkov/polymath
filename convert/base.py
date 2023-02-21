from argparse import ArgumentParser, Namespace
from typing import Union, Iterable

RawChunk = dict[str, Union[str, dict[str, str]]]
GetChunksResult = Iterable[RawChunk]

class BaseImporter:
    def install_arguments(self, parser: ArgumentParser):
        """
        An opportunity to install arguments on the parser.

        Arguments should be in a new group, start with a `--{importer_name}-`
        and have a default.
        """
        pass


    def retrieve_arguments(self, args: Namespace):
        """
        An opportunity to retrieve arguments configured via install_arguments.
        """
        pass


    def output_base_filename(self, directory : str) -> str:
        return directory


    def get_chunks(self, directory : str) -> GetChunksResult:
        raise Exception('get_chunks must be overridden')