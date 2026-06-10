# app.py
from dotenv import load_dotenv
load_dotenv(override=False)
load_dotenv(".env.local", override=False)

from modules import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
