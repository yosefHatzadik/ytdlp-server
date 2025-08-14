from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/update', methods=['GET'])
def update():
    token = request.args.get('token')
    if token != 'your_secret_token_123':
        return "גישה נדחתה", 403
    result = os.system("git pull && pip install -r requirements.txt")
    if result == 0:
        return "עדכון והתקנה בוצעו בהצלחה!"
    else:
        return "שגיאה בעדכון", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
