import os
import sys
import uvicorn
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("=" * 70)
    print("   Starting MarketIntel Institutional Backend API Server")
    print("   Swagger Interactive Docs: http://127.0.0.1:8000/docs")
    print("   OpenAPI Schema:           http://127.0.0.1:8000/openapi.json")
    print("   WebSockets Live Stream:   ws://127.0.0.1:8000/ws/live")
    print("=" * 70)
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)

