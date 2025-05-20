import pandas as pd
import json
import re

# Load the Excel file
file_path = "data/Recorded Crime - Offenders, 2023-24/1. Offenders, Australia.xlsx"
xls = pd.ExcelFile(file_path)

# Parse the 'Table 2' sheet
df = xls.parse('Table 2', header=5, nrows = 34)
df = df.map(lambda x: re.sub(r'\(.*?\)', '', str(x)).strip() if pd.notnull(x) else x)
df.columns = [re.sub(r'\(.*?\)', '', str(col)).strip() for col in df.columns]
df = df.dropna(how='all')
male = df[1:17]
female = df[18:]
male['gender'] = 'male'
female['gender'] = 'female'

male_person = male.iloc[:, 0:17]
male_person['gender'] = 'male'
male_rate = male.iloc[:, 17:]
male_rate.insert(loc = 0, column = "Principal offence", value = male_person["Principal offence"])

female_person = female.iloc[:, 0:17]
female_person['gender'] = 'female'
female_rate = female.iloc[:, 17:]
female_rate.insert(loc = 0, column = "Principal offence", value = female_person["Principal offence"])

male_rate.columns = male_person.columns
female_rate.columns = female_person.columns
person = pd.concat([male_person, female_person])
rate = pd.concat([male_rate, female_rate])

person['method'] = 'person'
rate['method'] = 'rate'

df2 = pd.concat([person, rate])

df = xls.parse('Table 5', header=5, nrows = 60)
df = df.map(lambda x: re.sub(r'\(.*?\)', '', str(x)).strip() if pd.notnull(x) else x)
df.columns = [re.sub(r'\(.*?\)', '', str(col)).strip() for col in df.columns]
df = df.dropna(how='any')

person = df.iloc[:, 0:17]
rate = df.iloc[:, 17:]
rate.insert(0, 'Age', person['Age'])
rate = rate[~rate.apply(lambda row: row.astype(str).str.lower().eq('na')).any(axis=1)]
rate.columns = person.columns

person['gender'] = ['male'] * 18 + ['female'] * 18 + ['total'] * 18
rate['gender'] = ['male'] * 16 + ['female'] * 16 + ['total'] * 16

person['method'] = 'person'
rate['method'] = 'rate'

df5 = pd.concat([person, rate])

df = pd.concat([df2, df5])
df.insert(0, "ID", range(1, len(df) + 1))
df = df.fillna(-1)
year_cols = [col for col in df.columns if '–' in col and col[:4].isdigit()]
df[year_cols] = df[year_cols].astype(float)

# Convert to list of dictionaries (JSON-ready)
json_data = df.to_dict(orient='records')
output_path = "crime_offender_principle_year_sex_age.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"Saved JSON to {output_path}")
