import pandas as pd
from utils_export import generate_excel_diff_report

# Test basic dataframe formatting with Excel colors
diffs = [
    {"Contexte": "General", "Identifiant": "1", "Champ": "Shipper", "FileA": "Company ABC", "FileB": "Company BCD"},
    {"Contexte": "BL", "Identifiant": "1", "Champ": "Consignee", "FileA": "Company ABD", "FileB": "Company ABD"}
]

generate_excel_diff_report(diffs, 'test_export_logic.xlsx')
df = pd.read_excel('test_export_logic.xlsx')
print(f"Generated successfully with {len(df)} rows.")

import os
if os.path.exists('test_export_logic.xlsx'):
    os.remove('test_export_logic.xlsx')
