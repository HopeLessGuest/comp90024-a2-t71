import pandas as pd
import json

# Define file paths
input_path = "C:/Users/iaman/Documents/comp90024-a2-t71/data/mean_price_number_transfer.xlsx"
output_path = "house_transfer.json"

# Load the "Data1" sheet, skipping the metadata
df = pd.read_excel(input_path, sheet_name="Data1", header=0)
df = df.iloc[15:].copy()  # Skip metadata rows

# Rename date column and parse dates
df.rename(columns={df.columns[0]: "Date"}, inplace=True)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"])

# Define series categories
categories = {
    "Median_Est_House": "Median Price of Established House Transfers",
    "Median_Att_Dwell": "Median Price of Attached Dwelling Transfers",
    "Num_Est_House": "Number of Established House Transfers",
    "Num_Att_Dwell": "Number of Attached Dwelling Transfers"
}

# Prepare long-form records
records = []

for col in df.columns:
    for key, keyword in categories.items():
        if keyword.lower() in col.lower():
            region = col.split(";")[1].strip()
            for _, row in df.iterrows():
                date = pd.to_datetime(row["Date"], errors="coerce")
                if pd.isna(date):
                    continue
                records.append({
                    "Month": date.month,
                    "Year": date.year,
                    "Region": region,
                    key: row[col]
                })

# Convert to DataFrame
df_long = pd.DataFrame(records)

# Group and combine into wide format
df_combined = df_long.groupby(["Month", "Year", "Region"], as_index=False).first()

# Add unique ID
df_combined.insert(0, "ID", range(1, len(df_combined) + 1))

# Save to JSON
with open(output_path, "w") as f:
    json.dump(df_combined.to_dict(orient="records"), f, indent=2)

print(f"Exported {len(df_combined)} records to {output_path}")
