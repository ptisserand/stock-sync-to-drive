#!/usr/bin/env python
import pickle
import os.path
import sys
from configparser import ConfigParser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# The ID and range of a sample spreadsheet (retrieve from config)
parser = ConfigParser()
parser.read('./config.ini')

BDD_SPREADSHEET_ID = parser.get('drive', 'spreadsheet')
ID_TITLE = parser.get('drive', 'ID_title')
STOCK_TITLE = parser.get('drive', 'stock_title')
ID_RANGE = 'BDD!A:A'


MAGIC_NUMBER = 64


def col_to_a1(col):
    col = col + 1
    div = col
    column_label = ''
    while div:
        (div, mod) = divmod(div, 26)
        if mod == 0:
            mod = 26
            div -= 1
        column_label = chr(mod + MAGIC_NUMBER) + column_label
    label = f'{column_label}'
    return label


def rowcol_to_a1(row, col):
    """Translates a row and column cell address to A1 notation.
    :param row: The row of the cell to be converted.
        Rows start at index 0.
    :type row: int, str
    :param col: The column of the cell to be converted.
        Columns start at index 0.
    :type row: int, str
    :returns: a string containing the cell's coordinates in A1 notation.
    Example:
    >>> rowcol_to_a1(0, 0)
    A1
    """
    row = int(row)
    col = int(col)
    # First 'usable' row is row 2
    label = f'{col_to_a1(col)}{row + 2}'
    return label


def retrieve_product_ids(sheet, sheetId=BDD_SPREADSHEET_ID, idRange=ID_RANGE):
    result = sheet.values().get(spreadsheetId=sheetId,
                                range=idRange).execute()
    values = result.get('values', [])
    # Use -1 id for unknown values
    # We skip the first elem since this is column title
    ids = []
    for vv in values[1:]:
        if len(vv) == 1:
            ids.append(int(vv[0]))
        else:
            ids.append(-1)
    return ids


def get_ids_mapping(ids: list) -> dict:
    ret = {}
    for ii in range(0, len(ids)):
        ret[ids[ii]] = ii
    return ret


def check_duplicated(values):
    aserie = pd.Series(values)
    aduplicated = aserie.duplicated()
    duplicated_index = aduplicated[aduplicated == True].index.values
    duplicated_values = aserie[duplicated_index]
    return duplicated_values


def get_column_ref(sheet, key: str, sheetId=BDD_SPREADSHEET_ID) -> (str, int):
    result = sheet.values().get(spreadsheetId=sheetId,
                                range='BDD!1:1').execute()
    values = result.get('values', [])
    # we retrieve only 1 row
    values = values[0]
    try:
        idx = values.index(key)
        return col_to_a1(idx), idx
    except ValueError:
        return '', -1


def batch_element(row, col, value) -> dict:
    range_name = rowcol_to_a1(row, col)
    return {
        'values': [
            [value]
        ],
        'range': range_name
    }


def commit_batch(sheet, data: list):
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    result = sheet.values().batchUpdate(
        spreadsheetId=BDD_SPREADSHEET_ID, body=body).execute()
    return result


def retrieve_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def main(stock_file):
    creds = retrieve_credentials()
    service = build('sheets', 'v4', credentials=creds)
    # Call the Sheets API
    sheet = service.spreadsheets()

    # Read stock file
    print("Reading xls file")
    tmp = pd.read_excel(stock_file)
    stock = tmp[['id', 'qty_available']]
    print("Retrieving drive column title")
    stock_column_name, stock_column_id = get_column_ref(sheet, STOCK_TITLE)
    print("Retrieving drive product ids")
    id_column_name, id_column_id = get_column_ref(sheet, ID_TITLE)
    product_ids = retrieve_product_ids(sheet)
    product_ids_mapping = get_ids_mapping(product_ids)

    data = []
    for elem in stock.values:
        product_id = int(elem[0])
        product_qty = elem[1]
        row = product_ids_mapping.get(product_id, None)
        if row is not None:
            # print(f"Row: {row}, Id: {product_id}, Qty: {product_qty}")
            # First row is title
            batch_entry = batch_element(row, stock_column_id, product_qty)
            data.append(batch_entry)
    print("Batch update")
    result = commit_batch(sheet, data)
    print(result)



if __name__ == '__main__':

    stock_file = sys.argv[1]
    main(stock_file)

