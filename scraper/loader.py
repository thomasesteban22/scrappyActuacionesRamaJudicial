import openpyxl
from .config import EXCEL_PATH

def cargar_procesos():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb.active
    return [ row[1] for row in ws.iter_rows(min_row=2, values_only=True) if row[1] ]
