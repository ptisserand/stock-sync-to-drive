
from googleapiclient.discovery import build
import pandas as pd
import xlrd



MAGIC_NUMBER = 64

TVA_VALUE_MAPPING = {
    '__export__.account_tax_4': 'taux-reduit',
    '__export__.account_tax_2': 'taux-normal',
}

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


class DriveDocument(object):
    def __init__(self, *, sheetId, sheetLabel, credentials):
        service = build('sheets', 'v4', credentials=credentials)
        self.sheet = service.spreadsheets()
        self.sheetId = sheetId
        self.sheetLabel = sheetLabel
        self._column_titles = None
    
    def retrieve_column(self, column_name, formula=False) -> list:
        range = f'{self.sheetLabel}!{column_name}:{column_name}'
        kwargs = {}
        if formula is True:
            kwargs['valueRenderOption'] = 'FORMULA'
        result = self.sheet.values().get(spreadsheetId=self.sheetId,
            range=range, **kwargs).execute()
        values = result.get('values', [])
        data = []
        # First element is column title
        for vv in values[1:]:
            if len(vv) == 1:
                value = vv[0]
            else:
                value = None
            data.append(value)
        return data
    
    def get_column_ref(self, key: str, refresh: bool=False) -> (str, int):
        if self._column_titles is None or refresh is True:
            result = self.sheet.values().get(spreadsheetId=self.sheetId,
                range=f'{self.sheetLabel}!1:1').execute()
            values = result.get('values', [])
            # we retrieve only 1 row
            values = values[0]
            self._column_titles = values
        else:
            values = self._column_titles
        try:
            idx = values.index(key)
            return col_to_a1(idx), idx
        except ValueError:
            return '', -1
    
    def batch_element(self, row, col, value) -> dict:
        range_name = rowcol_to_a1(row, col, sheetLabel=self.sheetLabel)
        return {
            'values': [
                [value]
            ],
            'range': range_name
        }
    
    def commit_batch(self, data: list):
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data    
        }
        result = self.sheet.values().batchUpdate(
            spreadsheetId=self.sheetId, body=body
        ).execute()
        return result

class StockSyncer(object):
    def __init__(self, *, drive: dict, stock: dict, credentials):
        service = build('sheets', 'v4', credentials=credentials)
        # Call the Sheets API
        self.sheet = service.spreadsheets()
        self.doc = DriveDocument(sheetId=drive['sheetId'], sheetLabel=drive['sheetLabel'], credentials=credentials)
        self.drive = drive
        self.stock = stock
        self.product_ids = []
        self.product_ids_mapping = {}
        self.drive_column_title = None
        self._column_title = None


    def _retrieve_product_ids(self):
        values = self.doc.retrieve_column(column_name='A')
        # Use -1 id for unknown values
        # We skip the first elem since this is column title
        ids = []
        ids_mapping = {}
        idx = 0
        for vv in values:
            value = vv
            if vv is None:
                value = -1
            ids.append(value)
            ids_mapping[value] = idx
            idx = idx + 1
        self.product_ids = ids
        self.product_ids_mapping = ids_mapping
        return ids
    
    def _retrieve_column(self, column_name) -> list:
        return self.doc.retrieve_column(column_name=column_name)

    def _get_column_ref(self, key: str) -> (str, int):
        return self.doc.get_column_ref(key=key)

    def _batch_element(self, row, col, value) -> dict:
        return self.doc.batch_element(row=row, col=col, value=value)

    def _commit_batch(self, data: list):
        return self.doc.commit_batch(data=data)
    
    def _conditioned_formula(self, row, quantity_price_column_id, cond_column_id):
        # =AE2*VALUE(REGEXEXTRACT(AG2;"^\s*[0-9]+")) / 1000
        quantity_price_cell = rowcol_to_a1(row, quantity_price_column_id)
        cond_cell = rowcol_to_a1(row, cond_column_id)
        formula = f'={quantity_price_cell} * VALUE(REGEXEXTRACT({cond_cell}; "^\s*[0-9]+")) / 1000'
        return formula

    def sync(self, xls_data: bytes, tva: bool=False):
        book = xlrd.open_workbook(file_contents=xls_data)
        tmp = pd.read_excel(book, engine='xlrd')
        stock_keys = [
            self.stock['ID_title'],
            self.stock['stock_title'],
            self.stock['price_title']
        ]
        if tva is True:
            stock_keys.append(self.stock['TVA_title'])
        
        stock = tmp[stock_keys]
        print("retrieving drive stock column ref")
        stock_column_name, stock_column_id = self._get_column_ref(self.drive['stock_title'])
        print("retrieving drive price column ref")
        price_column_name, price_column_id = self._get_column_ref(self.drive['price_title'])
        print("Retrieving drive quantity price column ref")
        quantity_price_column_name, quantity_price_column_id = self._get_column_ref(self.drive['quantity_price_title'])
        print("Retrieving conditionning column ref")
        cond_column_name, cond_column_id = self._get_column_ref(self.drive['cond_title'])
        if tva is True:
            print("Retrieving TVA column ref")
            tva_column_name, tva_column_id = self._get_column_ref(self.drive['TVA_title'])

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
                        data.append(batch_entry)
                    else:
                        formula = self._conditioned_formula(row, quantity_price_column_id, cond_column_id)
                        batch_entry = self._batch_element(row, price_column_id, formula)
                        data.append(batch_entry)
                        batch_entry = self._batch_element(row, quantity_price_column_id, product_price)
                        data.append(batch_entry)
                    
                    if tva is True:
                        tva_value = elem[3]
                        if tva_value in TVA_VALUE_MAPPING:
                            tva_value = TVA_VALUE_MAPPING[tva_value]
                            batch_entry = self._batch_element(row, tva_column_id, tva_value)
                            data.append(batch_entry)

            except AttributeError as e:
                print(f"Issue with an element: {e}")
                count += 1
            
        result = self._commit_batch(data)
        print(f"Number of dropped elements: {count}")
        return result


