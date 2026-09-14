import os
import uvicorn
from dotenv import load_dotenv
from src.app import app

load_dotenv()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
