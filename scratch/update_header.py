
import os
import sys
import logging
from src.browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)

def main():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    justification = "Required by bs37. Software used for research."
    
    print(f"Updating header for report: {report_name}")
    try:
        res = client.update_report(
            old_name=report_name,
            new_name=report_name,
            new_purpose=justification,
            new_comment=justification,
            headless=True
        )
        print("Success!")
        print(res)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
