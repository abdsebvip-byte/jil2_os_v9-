# debug_api.py
import requests

def debug():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL,MSFT,NVDA"
    print(f"Sending GET request to: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"HTTP Status Code: {response.status_code}")
        print("Response Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        print("\nResponse Body:")
        print(response.text[:2000])
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    debug()
