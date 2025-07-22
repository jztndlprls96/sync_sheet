import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
import base64

# Load credentials from base64-encoded secret
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Decode base64 string and load JSON credentials
creds_b64 = os.environ["CREDENTIALS_B64"]
creds_json = base64.b64decode(creds_b64).decode("utf-8")
service_account_info = json.loads(creds_json)

# Authenticate
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)


# Destination spreadsheet name
DESTINATION_SHEET_NAME = "PYTHON SYNC SHEETS"
dest_ss = client.open(DESTINATION_SHEET_NAME)

# Define sources and their relevant sheet names
sources = {
    "BAGUIO 2025-MPC": ["AICS BAGUIO", "AKAP BAGUIO"],
    "APAYAO 2025-MPC": ["AICS APAYAO", "AKAP APAYAO"],
    "ABRA 2025-MPC": ["AICS ABRA", "AKAP ABRA"],
    "BENGUET 2025-MPC": ["AICS BENGUET", "AKAP BENGUET"],
    "IFUGAO 2025-MPC": ["AICS IFUGAO", "AKAP IFUGAO"],
    "KALINGA 2025-MPC": ["AICS KALINGA", "AKAP KALINGA"],
    "MT. PROVINCE 2025-MPC": ["AICS MT. PROVINCE", "AKAP MT. PROVINCE"],
    "PYTHON-GLS": ["GL", "GL - APPSHEET"]
}

# Columns to extract
selected_columns = [
    "DATE (MM/DD/YYYY)", "ADA/CHECK/DV/PAYROLL/ REFERENCE NO.", "LAST NAME", "FIRST NAME", "MIDDLE NAME", "EXT.",
    "TYPE OF ASSISTANCE", "CASH ADVANCE RECEIVED/ (REFUNDED)", "DOBCLIENT (MM/DD/YYYY)", "RELATIONSHIP TO THE BENEFICIARY",
    "B LAST NAME", "B FIRST NAME", "B MIDDLE NAME", "B EXT.",
    "PROVINCE", "MUNICIPALITY/CITY", "BARANGAY", "SOCIAL WORKER"
]

# CSV export folder
EXPORT_FOLDER = "csv_exports"
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# Loop through each source sheet and copy its specified tabs
for source_name, tab_names in sources.items():
    try:
        source_ss = client.open(source_name)
        for tab_name in tab_names:
            try:
                ws = source_ss.worksheet(tab_name)
                data = ws.get_all_values()
                if not data or len(data) < 2:
                    print(f"⚠️ No data in {source_name} - {tab_name}")
                    continue

                df = pd.DataFrame(data[1:], columns=data[0])
                df = df[[col for col in selected_columns if col in df.columns]]

                # Try to load destination worksheet
                try:
                    dest_ws = dest_ss.worksheet(tab_name)
                    dest_data = dest_ws.get_all_values()
                    if dest_data:
                        dest_df = pd.DataFrame(dest_data[1:], columns=dest_data[0])
                        dest_df = dest_df[[col for col in selected_columns if col in dest_df.columns]]
                        if df.equals(dest_df):
                            print(f"⏩ Skipped (no changes): {source_name} > {tab_name}")
                            continue
                except gspread.exceptions.WorksheetNotFound:
                    dest_ws = dest_ss.add_worksheet(title=tab_name, rows="1000", cols="20")

                # Clear destination and update with new data
                dest_ws.clear()
                dest_ws.update([df.columns.values.tolist()] + df.values.tolist())

                # Export to CSV
                csv_filename = f"{tab_name.replace(' ', '_')}.csv"
                csv_path = os.path.join(EXPORT_FOLDER, csv_filename)
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"📁 Exported to CSV: {csv_path}")

                print(f"✅ Synced: {source_name} > {tab_name}")

            except Exception as e:
                print(f"❌ Error in sheet '{tab_name}' from '{source_name}': {e}")
    except Exception as e:
        print(f"❌ Cannot open source sheet '{source_name}': {e}")

print("🎉 All sheets synced.")
