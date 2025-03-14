from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import os
import requests
from werkzeug.utils import secure_filename
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
            <input type="file" name="file" accept=".xlsx,.csv" required>
            <br><br>
            <input type="submit" value="Convert">
        </form>
    </body>
    </html>
    '''


@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Secure filename and determine file extension
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        txt_filename = os.path.splitext(filename)[0] + '.txt'
        txt_filepath = os.path.join(OUTPUT_FOLDER, txt_filename)

        if file_ext == ".xlsx":
            df_dict = pd.read_excel(filepath, sheet_name=None)
        elif file_ext == ".csv":
            df_dict = {"CSV Sheet": pd.read_csv(filepath)}
        else:
            return jsonify({"error": "Unsupported file format. Only XLSX and CSV are allowed."}), 400

        with open(txt_filepath, 'w', encoding='utf-8') as txt_file:
            for sheet_name, data in df_dict.items():
                txt_file.write(f'=== {sheet_name} ===\n')
                txt_file.write(data.to_csv(sep='\t', index=False, header=True))
                txt_file.write('\n\n')

        # Create a new item in Monday.com
        item_id = create_monday_item(filename)
        if not item_id:
            return jsonify({"error": "Failed to create item in Monday.com"}), 500

        # Upload files to Monday.com
        upload_responses = {}
        if file_ext == ".xlsx":
            upload_responses["xlsx_upload_response"] = upload_to_monday(item_id, filepath, COLUMN_XLSX_ID)
        elif file_ext == ".csv":
            upload_responses["csv_upload_response"] = upload_to_monday(item_id, filepath, COLUMN_XLSX_ID)

        upload_responses["txt_upload_response"] = upload_to_monday(item_id, txt_filepath, COLUMN_TXT_ID)

        # 🎉 Show a success message
        success_html = f"""
        <!doctype html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    text-align: center;
                    padding: 50px;
                }}
                .container {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
                    display: inline-block;
                }}
                h2 {{ color: #28a745; }}
                p {{ color: #333; }}
                .button {{
                    background-color: #007bff;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin-top: 10px;
                }}
                .button:hover {{
                    background-color: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ File Conversion Successful!</h2>
                <p>Your file <b>{filename}</b> has been successfully converted and uploaded to Monday.com.</p>
                <a href="/" class="button">Upload Another File</a>
            </div>
        </body>
        </html>
        """
        return render_template_string(success_html)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
