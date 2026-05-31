import sys
import os
import time

sys.path.append(os.getcwd())
from intelligence.rl_inference_service import get_rl_signal

tickers = ["ADANIENT", "LT", "TCS", "INFY"]
print("Scanning stocks for BUY signals...")

for ticker in tickers:
    # Trigger inference (this will spawn training if not exists)
    res = get_rl_signal(ticker)
    if res['signal'] == 'PROCESSING':
        print(f"{ticker} is training in background... waiting for it to finish.")
        
# Wait for all to finish
while True:
    all_ready = True
    results = {}
    for ticker in tickers:
        res = get_rl_signal(ticker)
        if res['signal'] == 'PROCESSING':
            all_ready = False
        else:
            results[ticker] = res
            
    if all_ready:
        print("\nAll models trained. Here are the signals:")
        for t, r in results.items():
            print(f"{t}: {r['signal']} (Confidence: {r['confidence'] * 100:.1f}%)")
        break
    time.sleep(5)
