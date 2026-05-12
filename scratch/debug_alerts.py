import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from api.main import get_alerts
import traceback

try:
    print("Attempting to call get_alerts()...")
    res = get_alerts(limit=1)
    print("Result:", res)
except Exception as e:
    print("Caught Exception:")
    traceback.print_exc()
