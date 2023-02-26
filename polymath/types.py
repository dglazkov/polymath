from typing import Union, List

BitInfoData = dict[str, str]
BitData = dict[str, Union[None, str, int, float, BitInfoData]]
LibraryDetailsCountsData = dict[str, int]
LibraryDetailsData = dict[str, Union[str, LibraryDetailsCountsData]]
LibraryData = dict[str, Union[str, int, List[str], LibraryDetailsData, List[BitData]]]