
import pandas as pd
import os

file_path = "C:\\dev\\newwave\\Screening_Table_Complete.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print("Sheet names:", xl.sheet_names)
    
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = xl.parse(sheet, nrows=5)
        print("Columns:", list(df.columns))
        print("First row example:", df.iloc[0].to_dict() if not df.empty else "Empty")
except Exception as e:
    print(f"Error reading excel: {e}")
