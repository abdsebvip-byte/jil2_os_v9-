# module: sec_scanner.py
import time
import requests
import xml.etree.ElementTree as ET

class SECRealTimeScanner:
    def __init__(self):
        self.feed_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=exclude&count=40&output=atom"
        self.headers = {
            "User-Agent": "Abu Faisal Algorithmic Trading Platform abufaisal@quant.com"
        }
        self.seen_entry_ids = set()

    def fetch_latest_catalysts(self):
        """
        Fetch latest 8-K filings from SEC Edgar feed.
        Console logs are strictly ASCII/English to prevent Windows terminal encoding crashes.
        """
        print("fetch_latest_catalysts: Checking SEC Edgar Atom feed...")
        try:
            response = requests.get(self.feed_url, headers=self.headers, timeout=8)
            if response.status_code != 200:
                print(f"fetch_latest_catalysts: SEC connection failed. HTTP {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            new_catalysts = []
            
            for entry in root.findall('atom:entry', namespaces):
                entry_id = entry.find('atom:id', namespaces).text
                if entry_id in self.seen_entry_ids:
                    continue
                
                self.seen_entry_ids.add(entry_id)
                title = entry.find('atom:title', namespaces).text
                summary = entry.find('atom:summary', namespaces).text if entry.find('atom:summary', namespaces) is not None else ""
                updated = entry.find('atom:updated', namespaces).text
                
                company_name = ""
                cik = ""
                if " - " in title:
                    parts = title.split(" - ")
                    if len(parts) > 1:
                        raw_company = parts[1]
                        if "(" in raw_company:
                            company_name = raw_company.split("(")[0].strip()
                            cik_part = raw_company.split("(")[1]
                            cik = cik_part.replace(")", "").replace("Filer", "").strip()

                new_catalysts.append({
                    "Title": title,
                    "Company": company_name,
                    "CIK": cik,
                    "Time": updated,
                    "Summary": summary
                })
                
            return new_catalysts
        except Exception as e:
            print(f"fetch_latest_catalysts: Error parsing SEC data: {str(e)}")
            return []

if __name__ == "__main__":
    scanner = SECRealTimeScanner()
    print("main: Starting SEC Edgar real-time monitor...")
    for _ in range(5):
        events = scanner.fetch_latest_catalysts()
        if events:
            print(f"main: Found {len(events)} new SEC events:")
            for event in events:
                print(f"Company: {event['Company']} (CIK: {event['CIK']})")
                print(f"Time: {event['Time']}")
                print(f"Title: {event['Title']}")
                print("-" * 50)
        else:
            print("main: No new events.")
        time.sleep(15)
