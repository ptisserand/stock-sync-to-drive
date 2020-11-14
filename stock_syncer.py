
from googleapiclient.discovery import build
import pandas as pd
import xlrd



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

def rowcol_to_a1(row, col, sheetLabel=None):
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
    if sheetLabel is not None:
        label = f'{sheetLabel}!{label}'
    return label

def check_duplicated(values):
    aserie = pd.Series(values)
    aduplicated = aserie.duplicated()
    duplicated_index = aduplicated[aduplicated == True].index.values
    duplicated_values = aserie[duplicated_index]
    return duplicated_values



class StockSyncer(object):
    def __init__(self, *, drive: dict, stock: dict, credentials):
        service = build('sheets', 'v4', credentials=credentials)
        # Call the Sheets API
        self.sheet = service.spreadsheets()
        self.sheetId = drive['sheetId']
        self.sheetLabel = drive['sheetLabel']
        self.drive = drive
        self.stock = stock
        self.product_ids = []
        self.product_ids_mapping = {}
        self.drive_column_title = None


    def _retrieve_product_ids(self, idRange=None):
        if idRange is None:
            idRange=f'{self.sheetLabel}!A:A'
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
                value = vv[0]
            else:
                value = -1
            ids.append(value)
            ids_mapping[value] = idx
            idx = idx + 1
        self.product_ids = ids
        self.product_ids_mapping = ids_mapping
        return ids
    
    def _retrieve_column(self, column_name) -> list:
        range = f'{self.sheetLabel}!{column_name}:{column_name}'
        result = self.sheet.values().get(spreadsheetId=self.sheetId,
            range=range).execute()
        values = result.get('values', [])
        data = []
        for vv in values[1:]:
            if len(vv) == 1:
                value = vv[0]
            else:
                value = None
            data.append(value)
        return data


    def _get_column_ref(self, key: str) -> (str, int):
        if self.drive_column_title is None:
            result = self.sheet.values().get(spreadsheetId=self.sheetId,
                range=f'{self.sheetLabel}!1:1').execute()
            values = result.get('values', [])
            # we retrieve only 1 row
            values = values[0]
            self.drive_column_title = values
        else:
            values = self.drive_column_title
        try:
            idx = values.index(key)
            return col_to_a1(idx), idx
        except ValueError:
            return '', -1

    def _batch_element(self, row, col, value) -> dict:
        range_name = rowcol_to_a1(row, col, sheetLabel=self.sheetLabel)
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
        stock_keys = [
            self.stock['ID_title'],
            self.stock['stock_title'],
            self.stock['price_title']
        ]
        stock = tmp[stock_keys]
        print("retrieving drive stock column ref")
        stock_column_name, stock_column_id = self._get_column_ref(self.drive['stock_title'])
        print("retrieving drive price column ref")
        price_column_name, price_column_id = self._get_column_ref(self.drive['price_title'])
        print("Retrieving drive quantity price column ref")
        quantity_price_column_name, quantity_price_column_id = self._get_column_ref(self.drive['quantity_price_title'])
        print("Retrieving conditionning column ref")
        cond_column_name, cond_column_id = self._get_column_ref(self.drive['cond_title'])
        print("Retrieving drive product IDs column ref")
        id_column_name, id_column_id = self._get_column_ref(self.drive['ID_title'])

        self._retrieve_product_ids()
        product_cond = self._retrieve_column(column_name=cond_column_name)
        
        data = []
        count = 0
        for elem in stock.values:
            try:
                product_id = elem[0].replace('__export__.product_template_','')
                product_qty = elem[1]
                product_price = elem[2]
                row = self.product_ids_mapping.get(product_id, None)
                if row is not None:
                    # print(f"Row: {row}, Id: {product_id}, Qty: {product_qty}")
                    # First row is title
                    try:
                        cond = product_cond[row]
                    except:
                        print(f"No conditionning for {product_id} [{row}]")
                        continue
                    batch_entry = self._batch_element(row, stock_column_id, product_qty)
                    data.append(batch_entry)
                    if cond == '1':
                        batch_entry = self._batch_element(row, price_column_id, product_price)
                    else:
                        batch_entry = self._batch_element(row, quantity_price_column_id, product_price)
                    data.append(batch_entry)
            except AttributeError:
                print(f"Issue with an element")
                count += 1
            
        result = self._commit_batch(data)
        print(f"Number of dropped elements: {count}")
        return result


