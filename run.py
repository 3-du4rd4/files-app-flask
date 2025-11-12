from app import create_app
from dotenv import load_dotenv
import os

load_dotenv()
app = create_app()

if __name__ == "__main__":
    host = os.getenv('FLASK_HOST')
    port = int(os.getenv('FLASK_PORT'))
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(host=host, port=port, debug=debug)
