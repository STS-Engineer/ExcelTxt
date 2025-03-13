from flask import Flask, request, render_template, send_file, jsonify
import pandas as pd
import os
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

MONDAY_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQwNDE0OTkyOCwiYWFpIjoxMSwidWlkIjo0NzM5NDQ2OCwiaWFkIjoiMjAyNC0wOC0zMFQwODozMzo0OC4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6NDUyNTc0NywicmduIjoidXNlMSJ9.MnwSb_3K2NzqDIxpQkv3KCRVQIyeucGeYvCmhUW7kDM"  # Replace with your Monday.com API Token
BOARD_ID = "8678565478"  # Replace with your Monday.com Board ID
COLUMN_XLSX_ID ="file_mknz5f74"  # Replace with the ID of the File Column
COLUMN_TXT_ID = "file_mknz8vsn"
HEADERS = {
    "Authorization": MONDAY_API_TOKEN,
    "Content-Type": "application/json"
}


def create_monday_item(file_name):
    """ Create a new item in Monday.com """
    url = "https://api.monday.com/v2"
    query = f"""
    mutation {{
      create_item (board_id: {BOARD_ID}, item_name: "{file_name}") {{
        id
      }}
    }}
    """

    response = requests.post(url, headers=HEADERS, json={"query": query})
    data = response.json()

    if "data" in data and "create_item" in data["data"]:
        return data["data"]["create_item"]["id"]
    return None


def upload_to_monday(item_id, file_path, column_id):
    """ Upload a file to a specific column in Monday.com under a specific item """
    url = "https://api.monday.com/v2/file"

    query = f"""
    mutation ($file: File!) {{
      add_file_to_column (
        item_id: {item_id},
        column_id: "{column_id}",
        file: $file
      ) {{
        id
      }}
    }}
    """

    with open(file_path, 'rb') as file:
        response = requests.post(
            url,
            headers={"Authorization": MONDAY_API_TOKEN},
            files={"variables[file]": file},
            data={"query": query}
        )

    return response.json()


@app.route('/')
def upload_form():
    return '''
    <!doctype html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                text-align: center;
                padding: 50px;
            }
            h2 {
                color: #333;
            }
            form {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
                display: inline-block;
            }
            input[type="file"] {
                margin-bottom: 10px;
            }
            input[type="submit"] {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                cursor: pointer;
                font-size: 16px;
                border-radius: 5px;
            }
            input[type="submit"]:hover {
                background-color: #218838;
            }
        </style>
    </head>
    <body>
        <h2>Upload XLSX File to launch the analysis AI</h2>
        <form action="/convert" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".xlsx" required>
            <br><br>
            <input type="submit" value="Convert">
        </form>
    </body>
    </html>
    '''


@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Convert XLSX to TXT
        df = pd.read_excel(filepath, sheet_name=None)  # Read all sheets
        txt_filename = os.path.splitext(file.filename)[0] + '.txt'
        txt_filepath = os.path.join(OUTPUT_FOLDER, txt_filename)

        with open(txt_filepath, 'w', encoding='utf-8') as txt_file:
            for sheet_name, data in df.items():
                txt_file.write(f'=== {sheet_name} ===\n')
                txt_file.write(data.to_csv(sep='\t', index=False, header=True))
                txt_file.write('\n\n')

        # Create a new item in Monday.com
        item_id = create_monday_item(file.filename)
        if not item_id:
            return "Failed to create item in Monday.com"

        # Upload the original XLSX to the XLSX column
        xlsx_upload_response = upload_to_monday(item_id, filepath, COLUMN_XLSX_ID)

        # Upload the converted TXT file to the TXT column
        txt_upload_response = upload_to_monday(item_id, txt_filepath, COLUMN_TXT_ID)

        return jsonify({
            "item_id": item_id,
            "xlsx_upload_response": xlsx_upload_response,
            "txt_upload_response": txt_upload_response
        })


if __name__ == '__main__':
    app.run(debug=True)
