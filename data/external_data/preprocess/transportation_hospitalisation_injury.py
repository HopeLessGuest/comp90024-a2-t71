import pandas as pd
import json

# Define paths
input_path = "data/hospitalisation_injury_publication_sep2023.xlsx"
output_path = "road_user_injuries.json"

# Load raw sheet to extract gendered categories
raw_df = pd.read_excel(input_path, sheet_name="T2.2", header=None)

column_mapping = {
    "Calendar year": "Year",
    "0-7": "age_0_7",
    "8-16": "age_8_16",
    "17-25": "age_17_25",
    "26-39": "age_26_39",
    "40-64": "age_40_64",
    "65-74": "age_65_74",
    "75+": "age_75_plus",
    "Total": "total"
}

records = []
row = 0
while row < 120:

    # Get category
    left_category = str(raw_df.iloc[row + 2, 0])
    right_category = str(raw_df.iloc[row + 2, 10])

    # Extract block with header row at row+3
    block_df = pd.read_excel(input_path, sheet_name="T2.2", header=row + 3, nrows=11)
    left_df = block_df.iloc[:, 0:9].copy()
    right_df = block_df.iloc[:, 10:19].copy()

    # Rename columns
    left_df.rename(columns=column_mapping, inplace=True)
    right_df.columns = [col.replace(".1", "") for col in right_df.columns]
    right_df.rename(columns=column_mapping, inplace=True)

    # Add Gender and Category
    left_df["Gender"] = "Male"
    left_df["Category"] = left_category.replace("Male ", "").strip()
    right_df["Gender"] = "Female"
    right_df["Category"] = right_category.replace("Female ", "").strip()
    
    # Combine
    combined = pd.concat([left_df, right_df], ignore_index=True)
    combined = combined[combined["Year"].apply(lambda x: str(x).isdigit())].copy()
    combined["Year"] = combined["Year"].astype(int)
    records.append(combined)

    row += 14  # Move to next block

# Final cleanup and save
final_df = pd.concat(records, ignore_index=True)

final_df.insert(0, "ID", range(1, len(final_df) + 1))
final_df.to_json(output_path, orient="records", indent=2)
print(f"✅ Saved {len(final_df)} records to {output_path}")