
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from overrides import override

from .base import BaseImporter, GetChunksResult

from convert.chunker import generate_chunks

SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

TOKEN_FILE_LOCATION = 'token.SECRET.json'
CREDENTIALS_FILE_LOCATION = 'credentials.SECRET.json'


def authorize():
    """More or less copied from the Google Docs API quickstart guide."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE_LOCATION):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE_LOCATION, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE_LOCATION, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE_LOCATION, 'w') as token:
            token.write(creds.to_json())
    return creds


def get_paragraph(element):
    text_run = element.get('textRun')
    if not text_run:
        return ''
    return text_run.get('content')


def get_elements(elements, current_heading_id='', current_run=None):
    """"
    Takes a list of StructuralElements, and a current_heading_id and run of
    items to append to.

    If current_run is None, Yields a sequence of (heading_id : str, bits:
    List[str]). 

    If current_run is provided, then it extends current_run with items it finds
    until it comes across a new heading, at which point it yields a tuple and
    then continues working on the next one.
    """
    top_level = False
    if not current_run:
        top_level = True
        current_run = []
    for value in elements:
        if 'paragraph' in value:
            paragraph = value.get('paragraph')
            style = value.get('paragraphStyle')
            if style:
                heading_id = style.get('headingId')
                if heading_id:
                    # if we found a new heading, return the one we were working
                    # on and start a new one, if there are any items
                    if len(current_run):
                        yield (current_heading_id, current_run)
                    current_heading_id = heading_id
                    current_run = []
            elements = paragraph.get('elements')
            for elem in elements:
                current_run.append(get_paragraph(elem))
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    yield from get_elements(cell.get('content'), current_heading_id=current_heading_id, current_run=current_run)
        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            toc = value.get('tableOfContents')
            yield from get_elements(toc.get('content'), current_heading_id=current_heading_id, current_run=current_run)
        if top_level and len(current_run):
            # if we were the top level and there are some lingering items at the
            # end of the doc, return them. recursive calls might be within a
            # heading run so shouldn't return unless we know it's full end of
            # all input.
            yield (current_heading_id, current_run)

class GoogleDocsImporter(BaseImporter):

    @override
    def output_base_filename(self, filename) -> str:
        return filename

    @override
    def get_chunks(self, filename: str) -> GetChunksResult:
        creds = authorize()
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=filename).execute()
        title = document.get('title')
        content = document.get('body').get('content')
        for heading_id, bits in get_elements(content):
            for chunk in generate_chunks(bits):
                url = f"https://docs.google.com/document/d/{filename}/edit" + ('#heading=' + heading_id if heading_id else '')
                yield {
                    "text": chunk,
                    "info": {
                        "url": url,
                        "title": title
                    }
                }
