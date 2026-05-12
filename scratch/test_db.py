import pg8000
try:
    conn = pg8000.connect(user="postgres", password="postgres", host="127.0.0.1", port=5433, database="stock_intelligence")
    print("Connection successful!")
    conn.close()
except Exception as e:
    print("Connection failed:", e)
