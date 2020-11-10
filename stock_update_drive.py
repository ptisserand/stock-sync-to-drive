#!/usr/bin/env python
import pickle
import os.path
import sys
from configparser import ConfigParser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
import xlrd

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

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

def check_duplicated(values):
    aserie = pd.Series(values)
    aduplicated = aserie.duplicated()
    duplicated_index = aduplicated[aduplicated == True].index.values
    duplicated_values = aserie[duplicated_index]
    return duplicated_values

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



class StockSyncer(object):
    def __init__(self, *, sheetId, IdTitle, stockTitle, credentials):
        service = build('sheets', 'v4', credentials=credentials)
        # Call the Sheets API
        self.sheet = service.spreadsheets()
        self.sheetId = sheetId
        self.IdTitle = IdTitle
        self.stockTitle = stockTitle
        self.product_ids = []
        self.product_ids_mapping = {}


    def _retrieve_product_ids(self, idRange=ID_RANGE):
        result = self.sheet.values().get(spreadsheetId=self.sheetId,
            range=idRange).execute()
        values = result.get('values', [])
        # Use -1 id for unknown values
        # We skip the first elem since this is column title
        ids = []
        ids_mapping = {}
        idx = 0
        for vv in values[1:]:
            if len(vv) == 1:
                value = int(vv[0])
            else:
                value = -1
            ids.append(value)
            ids_mapping[value] = idx
            idx = idx + 1
        self.product_ids = ids
        self.product_ids_mapping = ids_mapping
        return ids
    
    def _get_column_ref(self, key: str) -> (str, int):
        result = self.sheet.values().get(spreadsheetId=self.sheetId,
            range='BDD!1:1').execute()
        values = result.get('values', [])
        # we retrieve only 1 row
        values = values[0]
        try:
            idx = values.index(key)
            return col_to_a1(idx), idx
        except ValueError:
            return '', -1

    def _batch_element(self, row, col, value) -> dict:
        range_name = rowcol_to_a1(row, col)
        return {
            'values': [
                [value]
            ],
            'range': range_name
        }


    def _commit_batch(self, data: list):
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data    
        }
        result = self.sheet.values().batchUpdate(
            spreadsheetId=self.sheetId, body=body
        ).execute()
        return result
    
    def sync(self, xls_data: bytes):
        book = xlrd.open_workbook(file_contents=xls_data)
        tmp = pd.read_excel(book, engine='xlrd')
        stock = tmp[['id', 'qty_available']]
        print("retrieving drive column title")
        stock_column_name, stock_column_id = self._get_column_ref(self.stockTitle)
        print("retrieving drive product IDs")
        id_column_name, id_column_id = self._get_column_ref(self.IdTitle)
        self._retrieve_product_ids()

        data = []
        for elem in stock.values:
            product_id = int(elem[0])
            product_qty = elem[1]
            row = self.product_ids_mapping.get(product_id, None)
            if row is not None:
                # print(f"Row: {row}, Id: {product_id}, Qty: {product_qty}")
                # First row is title
                batch_entry = self._batch_element(row, stock_column_id, product_qty)
                data.append(batch_entry)
        print("Batch update")
        result = self._commit_batch(data)
        print(f"{result}")




def main(stock_file):
    creds = retrieve_credentials()
    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read('./config.ini')

    stockSyncer = StockSyncer(sheetId=parser.get('drive', 'spreadsheet'),
        IdTitle=parser.get('drive', 'ID_title'),
        stockTitle=parser.get('drive', 'stock_title'),
        credentials=creds
        )

    # Read stock file
    print("Reading xls file")
    with open(stock_file, 'rb') as f:
        xls_data = f.read()
    
    stockSyncer.sync(xls_data)



if __name__ == '__main__':

    stock_file = sys.argv[1]
    main(stock_file)

