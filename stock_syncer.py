from math import floor
from googleapiclient.discovery import build
import pandas as pd
import xlrd
import re
from numpy import isnan

import logging

logger = logging.getLogger("syncer")

MAGIC_NUMBER = 64

TVA_VALUE_MAPPING = {
    "__export__.account_tax_4": "taux-reduit",
    "__export__.account_tax_2": "taux-normal",
}

MASS_RE = re.compile(r"^\s*(?P<mass>[0-9]+)(g|ml)")


def col_to_a1(col):
    col = col + 1
    div = col
    column_label = ""
    while div:
        (div, mod) = divmod(div, 26)
        if mod == 0:
            mod = 26
            div -= 1
        column_label = chr(mod + MAGIC_NUMBER) + column_label
    label = f"{column_label}"
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
    label = f"{col_to_a1(col)}{row + 2}"
    if sheetLabel is not None:
        label = f"{sheetLabel}!{label}"
    return label


def check_duplicated(values):
    aserie = pd.Series(values)
    aduplicated = aserie.duplicated()
    duplicated_index = aduplicated[aduplicated == True].index.values
    duplicated_values = aserie[duplicated_index]
    return duplicated_values


class DriveDocument(object):
    def __init__(self, *, sheetId, sheetLabel, credentials):
        # see
        # https://stackoverflow.com/questions/40154672/importerror-file-cache-is-unavailable-when-using-python-client-for-google-ser
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.sheet = service.spreadsheets()
        self.sheetId = sheetId
        self.sheetLabel = sheetLabel
        self._column_titles = None

    def retrieve_column(self, column_name, formula=False) -> list:
        range = f"{self.sheetLabel}!{column_name}:{column_name}"
        kwargs = {}
        if formula is True:
            kwargs["valueRenderOption"] = "FORMULA"
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.sheetId, range=range, **kwargs)
            .execute()
        )
        values = result.get("values", [])
        data = []
        # First element is column title
        for vv in values[1:]:
            if len(vv) == 1:
                value = vv[0]
            else:
                value = None
            data.append(value)
        return data

    def get_column_ref(self, key: str, refresh: bool = False) -> (str, int):
        if self._column_titles is None or refresh is True:
            result = (
                self.sheet.values()
                .get(spreadsheetId=self.sheetId, range=f"{self.sheetLabel}!1:1")
                .execute()
            )
            values = result.get("values", [])
            # we retrieve only 1 row
            values = values[0]
            self._column_titles = values
        else:
            values = self._column_titles
        try:
            idx = values.index(key)
            return col_to_a1(idx), idx
        except ValueError:
            return "", -1

    def batch_element(self, row, col, value) -> dict:
        range_name = rowcol_to_a1(row, col, sheetLabel=self.sheetLabel)
        return {"values": [[value]], "range": range_name}

    def commit_batch(self, data: list):
        body = {"valueInputOption": "USER_ENTERED", "data": data}
        result = (
            self.sheet.values()
            .batchUpdate(spreadsheetId=self.sheetId, body=body)
            .execute()
        )
        return result


class Stock(object):
    def __init__(self, *, drive: dict, stock: dict, credentials):
        # Call the Sheets API
        self.doc = DriveDocument(
            sheetId=drive["sheetId"],
            sheetLabel=drive["sheetLabel"],
            credentials=credentials,
        )
        self.drive = drive
        self.stock = stock
        self.product_ids = []
        self.product_ids_mapping = {}
        self.drive_column_title = None
        self._column_title = None

    def _retrieve_product_ids(self):
        values = self.doc.retrieve_column(column_name="A")
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
        name, id = self.doc.get_column_ref(key=key)
        if id == -1:
            logger.error(f"Error retrieving column {key}")
        return name, id

    def _batch_element(self, row, col, value) -> dict:
        return self.doc.batch_element(row=row, col=col, value=value)

    def _commit_batch(self, data: list):
        return self.doc.commit_batch(data=data)

    def _conditioned_formula(self, *, row, quantity_price_column_id, cond_column_id):
        # =AE2*VALUE(REGEXEXTRACT(AG2;"^\s*[0-9]+")) / 1000
        quantity_price_cell = rowcol_to_a1(row, quantity_price_column_id)
        cond_cell = rowcol_to_a1(row, cond_column_id)
        formula = f'={quantity_price_cell} * VALUE(REGEXEXTRACT({cond_cell}; "^\s*[0-9]+")) / 1000'
        return formula

    def _quantity_price_formula(self, *, row, price_column_id, cond_column_id):
        price_cell = rowcol_to_a1(row, price_column_id)
        cond_cell = rowcol_to_a1(row, cond_column_id)
        formula = f'=ROUND({price_cell} * 1000 / VALUE(REGEXEXTRACT({cond_cell}; "^\s*[0-9]+")); 2)'
        return formula


class StockSyncer(Stock):
    def sync(self, xls_data: bytes, dry: bool = False):
        book = xlrd.open_workbook(file_contents=xls_data)
        tmp = pd.read_excel(book, engine="xlrd")
        stock_keys = [
            self.stock["ID_title"],
            self.stock["stock_title"],
            self.stock["price_title"],
            self.stock["name_title"],
            self.stock["by_unit_title"],
        ]
        tva_key = self.stock.get("TVA_title", None)
        tva = False
        if tva_key is not None:
            wait = tmp.get(tva_key, None)
            if wait is not None:
                logger.info("TVA enabled")
                tva = True
        if tva is True:
            stock_keys.append(self.stock["TVA_title"])

        stock = tmp[stock_keys]
        logger.info("Retrieving drive columns ref")
        logger.debug(f"Retrieving drive stock column ref {self.drive['stock_title']}")
        stock_column_name, stock_column_id = self._get_column_ref(
            self.drive["stock_title"]
        )
        logger.debug(f"Retrieving drive price column ref {self.drive['price_title']}")
        price_column_name, price_column_id = self._get_column_ref(
            self.drive["price_title"]
        )
        logger.debug(
            f"Retrieving drive quantity price column ref {self.drive['quantity_price_title']}"
        )
        quantity_price_column_name, quantity_price_column_id = self._get_column_ref(
            self.drive["quantity_price_title"]
        )
        logger.debug(f"Retrieving conditionning column ref {self.drive['cond_title']}")
        cond_column_name, cond_column_id = self._get_column_ref(
            self.drive["cond_title"]
        )
        if tva is True:
            logger.debug(f"Retrieving TVA column ref {self.drive['TVA_title']}")
            tva_column_name, tva_column_id = self._get_column_ref(
                self.drive["TVA_title"]
            )

        logger.debug(
            f"Retrieving drive product IDs column ref {self.drive['ID_title']}"
        )
        id_column_name, id_column_id = self._get_column_ref(self.drive["ID_title"])

        self._retrieve_product_ids()
        product_cond = self._retrieve_column(column_name=cond_column_name)

        data = []
        count = 0
        missing_ids = []
        missing_conds = []
        for elem in stock.values:
            try:
                if not isinstance(elem[0], str) or isnan(elem[1]) or isnan(elem[2]):
                    # empty line skipped
                    count += 1
                    continue
                product_id = elem[0].replace("__export__.product_template_", "")
                product_qty = elem[1]
                product_price = elem[2]
                product_name = elem[3]
                product_by_unit = elem[4]
                row = self.product_ids_mapping.get(product_id, None)
                if row is not None:
                    # logger.debug(f"Row: {row}, Id: {product_id}, Qty: {product_qty}")
                    # First row is title
                    try:
                        cond = product_cond[row]
                    except:
                        logger.warning(f"No conditionning for {product_id} [{row}]")
                        missing_conds.append(product_id)

                    if product_by_unit == 0.0:
                        # Product sell by unit
                        batch_entry = self._batch_element(
                            row, stock_column_id, product_qty
                        )
                        data.append(batch_entry)
                        batch_entry = self._batch_element(
                            row, price_column_id, product_price
                        )
                        data.append(batch_entry)
                        formula = self._quantity_price_formula(
                            row=row,
                            price_column_id=price_column_id,
                            cond_column_id=cond_column_id,
                        )
                        batch_entry = self._batch_element(
                            row, quantity_price_column_id, formula
                        )
                        data.append(batch_entry)
                    else:
                        try:
                            mass = MASS_RE.match(cond).group("mass")
                            mass = int(mass)
                        except AttributeError:
                            logger.error(
                                f"Attribute Error for {product_id}/{row} '{cond}'"
                            )
                            continue
                        if mass == 0:
                            logger.error(
                                f"Wrong conditionning for {product_id} '{cond}'"
                            )
                            continue
                        product_units = floor(product_qty * 1000 / mass)
                        if product_units < 0:
                            product_units = 0
                        batch_entry = self._batch_element(
                            row, stock_column_id, product_units
                        )
                        data.append(batch_entry)
                        formula = self._conditioned_formula(
                            row=row,
                            quantity_price_column_id=quantity_price_column_id,
                            cond_column_id=cond_column_id,
                        )
                        batch_entry = self._batch_element(row, price_column_id, formula)
                        data.append(batch_entry)
                        batch_entry = self._batch_element(
                            row, quantity_price_column_id, product_price
                        )
                        data.append(batch_entry)

                    if tva is True:
                        tva_value = elem[3]
                        if tva_value in TVA_VALUE_MAPPING:
                            tva_value = TVA_VALUE_MAPPING[tva_value]
                            batch_entry = self._batch_element(
                                row, tva_column_id, tva_value
                            )
                            data.append(batch_entry)
                else:
                    if product_qty > 0:
                        logger.debug(f"{product_id} not found in drive")
                        missing_ids.append({"id": product_id, "name": product_name})

            except AttributeError as e:
                logger.error(f"Issue with an element: {e}")
                count += 1

        if dry is False:
            result_commit = self._commit_batch(data)
        else:
            logger.debug("Dry run...")
            result_commit = None
        missing_ids.sort(key=lambda elem: int(elem["id"]))
        missing_conds.sort()

        logger.info(f"Number of dropped elements: {count}")
        logger.info(f"Number of missing ids: {len(missing_ids)}")
        logger.info(f"Number of missing conditionning: {len(missing_conds)}")
        result = {"commit": result_commit, "missing_ids": missing_ids}
        return result


class StockCheckerID(Stock):
    def check(self, xls_data: bytes):
        book = xlrd.open_workbook(file_contents=xls_data)
        tmp = pd.read_excel(book, engine="xlrd")
        stock_keys = [
            self.stock["ID_title"],
            self.stock["name_title"],
        ]

        stock = tmp[stock_keys]
        logger.info("Retrieving drive columns ref")
        logger.debug("retrieving drive name column ref")
        name_column_name, name_column_id = self._get_column_ref(
            self.drive["name_title"]
        )

        logger.debug("Retrieving drive product IDs column ref")
        id_column_name, id_column_id = self._get_column_ref(self.drive["ID_title"])

        self._retrieve_product_ids()
        product_names = self._retrieve_column(column_name=name_column_name)

        data = []
        count = 0
        matching = []
        for elem in stock.values:
            try:
                if not isinstance(elem[0], str) or not isinstance(elem[1], str):
                    # empty line skipped
                    count += 1
                    continue
                product_id = elem[0].replace("__export__.product_template_", "")
                product_name = elem[1]
                row = self.product_ids_mapping.get(product_id, None)
                if row is not None:
                    # logger.debug(f"Row: {row}, Id: {product_id}, Qty: {product_qty}")
                    # First row is title
                    try:
                        name = product_names[row]
                        if name != product_name:
                            matching.append(
                                {
                                    "id": product_id,
                                    "vrac_name": product_name,
                                    "drive_name": name,
                                }
                            )
                    except:
                        logger.warning(f"No name for {product_id} [{row}]")

            except AttributeError as e:
                logger.error(f"Issue with an element: {e}")
                count += 1

        matching.sort(key=lambda elem: int(elem["id"]))
        result = {"names": matching}
        return result

    def extra(self, xls_data: bytes):
        book = xlrd.open_workbook(file_contents=xls_data)
        tmp = pd.read_excel(book, engine="xlrd")
        stock_keys = [
            self.stock["ID_title"],
        ]

        stock = tmp[stock_keys]

        logger.info("Retrieving drive columns ref")
        logger.debug("retrieving drive name column ref")
        name_column_name, name_column_id = self._get_column_ref(
            self.drive["name_title"]
        )

        logger.debug("Retrieving drive product IDs column ref")
        id_column_name, id_column_id = self._get_column_ref(self.drive["ID_title"])

        self._retrieve_product_ids()
        product_names = self._retrieve_column(column_name=name_column_name)

        count = 0
        extra = []
        vrac_ids = []
        for elem in stock.values:
            if not isinstance(elem[0], str):
                continue
            vrac_ids.append(elem[0].replace("__export__.product_template_", ""))

        for product_id in self.product_ids:
            row = self.product_ids_mapping.get(product_id, None)
            if not product_id in vrac_ids:
                logger.warn(f"Row: {row}, Id: {product_id}")
                extra.append({"row": row, "id": product_id})

        result = {"extra": extra}
        return result


class StockImage(Stock):
    def doit(self, images_mapping: dict, dry: bool = False):
        logger.debug("Retrieving images title column ref")
        images_column_name, images_column_id = self._get_column_ref(
            self.drive["images_title"]
        )

        self._retrieve_product_ids()
        data = []
        for ugs, url in images_mapping.items():
            row = self.product_ids_mapping.get(ugs, None)
            if row is not None:
                batch_entry = self._batch_element(row, images_column_id, url)
                data.append(batch_entry)
            else:
                logger.info(f"UGS ({ugs}) not found")
        if not dry:
            result_commit = self._commit_batch(data)
        else:
            result_commit = []
        return result_commit
