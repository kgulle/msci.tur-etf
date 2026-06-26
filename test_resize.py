import sys
sys.path.insert(0, 'src')
from sheets_writer import SheetsWriter

writer = SheetsWriter("1tg5OBvX_ohCrxdiz_2JvtQxTPKmE-hNW27C2WGxH7n0", "credentials/service_account.json")
writer.connect()
ws = writer._get_sheet("weight_matrix")

body = {
    "requests": [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": 100
                },
                "properties": {"pixelSize": 50},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": 2, # Column C
                    "endIndex": 3
                },
                "properties": {"pixelSize": 250},
                "fields": "pixelSize"
            }
        }
    ]
}

res = ws.spreadsheet.batch_update(body)
print("Sonuc:", res)
