import sys
import os

# Ensure project root is in python path
sys.path.append(os.getcwd())

from intelligence.prediction_service import PredictionService

def test_signals():
    print("Initializing Prediction Service...")
    service = PredictionService()
    
    tickers_to_test = ["SBIN", "ADANIENT", "LT", "TCS", "INFY", "HDFCBANK", "RELIANCE"]
    
    for ticker in tickers_to_test:
        print(f"\n{'='*50}")
        print(f"Testing Technical Scoring for: {ticker}")
        print(f"{'='*50}")
        
        # Get signal directly from the new logic
        result = service.get_signal(ticker)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            continue
            
        print(f"Signal:      {result['signal']}")
        print(f"Confidence:  {result['confidence'] * 100:.1f}%")
        print(f"Current Px:  {result['current_price']}")
        
        techs = result['technicals']
        print("\nUnderlying Technical Drivers:")
        print(f" - RSI (Momentum) : {techs['rsi']:.2f}")
        print(f" - MACD           : {techs['macd']:.2f} (Signal: {techs['macd_signal']:.2f})")
        print(f" - Price vs SMA20 : {result['current_price']:.2f} vs {techs['sma_20']:.2f}")
        print(f" - Price vs SMA50 : {result['current_price']:.2f} vs {techs['sma_50']:.2f}")

if __name__ == "__main__":
    test_signals()
