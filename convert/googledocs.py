
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


def get_elements(elements):
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                yield get_paragraph(elem)
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    yield from get_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            toc = value.get('tableOfContents')
            yield from get_elements(toc.get('content'))


class GoogleDocsImporter:
    def output_base_filename(self, filename) -> str:
        return filename

    def get_chunks(self, filename: str):
        creds = authorize()
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=filename).execute()
        title = document.get('title')
        content = document.get('body').get('content')
        for chunk in generate_chunks([get_elements(content)]):
            yield {
                "text": chunk,
                "info": {
                    "url": f"https://docs.google.com/document/d/{filename}/edit",
                    "title": title
                }
            }
