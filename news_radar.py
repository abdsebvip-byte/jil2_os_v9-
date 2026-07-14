# module: news_radar.py
import requests
import xml.etree.ElementTree as ET

class SECNewsRadar:
    def __init__(self):
        self.feed_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=exclude&count=40&output=atom"
        self.headers = {
            "User-Agent": "Abu Faisal Algorithmic Trading Platform abufaisal@quant.com"
        }
        self.seen_entry_ids = set()

    def fetch_latest_filings_rss(self):
        """
        Ultra-low-latency SEC Atom feed parser. Fetches the latest raw XML feed
        and extracts 8-K filings, CIKs, and titles in milliseconds.
        """
        print("fetch_latest_filings_rss: Connecting to SEC Atom feed...")
        try:
            response = requests.get(self.feed_url, headers=self.headers, timeout=8)
            if response.status_code != 200:
                print(f"fetch_latest_filings_rss: Request failed. HTTP {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            new_events = []
            
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

                # تصنيف وتحليل المحفز الإخباري بالكلمات المفتاحية
                is_positive = False
                for keyword in ["approval", "merger", "acquisition", "clinical trial", "positive", "partnership", "agreement"]:
                    if keyword in summary.lower() or keyword in title.lower():
                        is_positive = True
                        break

                new_events.append({
                    "Title": title,
                    "Company": company_name,
                    "CIK": cik,
                    "Time": updated,
                    "Summary": summary,
                    "Is_Positive_Catalyst": is_positive
                })
                
            return new_events
        except Exception as e:
            print(f"fetch_latest_filings_rss: Error: {str(e)}")
            return []

    def fetch_latest_filings(self):
        """
        Unified entry point. Tries to use the robust RSS parser for speed,
        maintaining a zero-dependency execution flow.
        """
        # يمكن تجربة edgartools هنا ولكن الـ RSS فائق السرعة هو الأنسب للتداول اللحظي
        return self.fetch_latest_filings_rss()
