import pandas as pd
import json
import re

# Load the Excel file
file_path = "data/Recorded-Crime-Victims-2023/1. Victims of crime, Australia (Tables 1 to 8).xlsx"
xls = pd.ExcelFile(file_path)

# Parse the 'Table 1' sheet
df = xls.parse('Table 1', header=5, nrows = 35)
df = df.map(lambda x: re.sub(r'\(.*?\)', '', str(x)).strip() if pd.notnull(x) else x)
df.columns = [re.sub(r'\(.*?\)', '', str(col)).strip() for col in df.columns]
df = df.dropna(how='any')
df = df.replace('np', -1)

df['method'] = ['person'] * 15 + ['rate'] * 6
df['state'] = 'total'
df1 = df.apply(pd.to_numeric, errors='ignore')

file_path = "data/Recorded-Crime-Victims-2023/2. Victims of crime, states and territories (Tables 9 to 16).xlsx"
xls = pd.ExcelFile(file_path)

# Parse the 'Table 9' sheet
df = xls.parse('Table 9', header=5, nrows = 200)
df = df.map(lambda x: re.sub(r'\(.*?\)', '', str(x)).strip() if pd.notnull(x) else x)
df.columns = [re.sub(r'\(.*?\)', '', str(col)).strip() for col in df.columns]
df = df.dropna(how='any')
df = df.replace('np', -1)

df['method'] = 'person'
state = ['nsw', 'vic', 'qld', 'sa', 'wa', 'tas', 'nt', 'act']
states = [state for state, count in zip(state, [16] * 8) for _ in range(count)]
df['state'] = states

df9 = df.apply(pd.to_numeric, errors='ignore')

# Parse the 'Table 10' sheet
df = xls.parse('Table 10', header=5, nrows = 200)
df = df.map(lambda x: re.sub(r'\(.*?\)', '', str(x)).strip() if pd.notnull(x) else x)
df.columns = [re.sub(r'\(.*?\)', '', str(col)).strip() for col in df.columns]
df = df.dropna(how='any')
df = df.replace('np', -1)

df['method'] = 'rate'
state = ['nsw', 'vic', 'qld', 'sa', 'wa', 'tas', 'nt', 'act']
states = [state for state, count in zip(state, [7] * 8) for _ in range(count)]
df['state'] = states

df10 = df.apply(pd.to_numeric, errors='ignore')

df = pd.concat([df1, df9, df10], ignore_index=True)
df = df.replace('na', -1)
year_cols = [col for col in df.columns if col.isdigit() and len(col) == 4]
df[year_cols] = df[year_cols].apply(pd.to_numeric, errors='coerce')

df.insert(0, "ID", range(1, len(df) + 1))

# Convert to list of dictionaries (JSON-ready)
json_data = df.to_dict(orient='records')
output_path = "crime_victim_selected_year_state.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"Saved JSON to {output_path}")