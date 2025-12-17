import os
from app import create_app, socketio

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)