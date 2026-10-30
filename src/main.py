import os
import json
import copy
from datetime import datetime

from fetch_data import fetch_all_peer_rates, fetch_fred_data
from generate_report import generate_report
from send_email import build_html_email, send_email
from excel_output import build_excel

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/banks.json")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
FRED_API_KEY      = os.environ["FRED_API_KEY"]

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def run():
    config = load_config()
    week_date = datetime.now().strftime("%b %d, %Y")

    print(f"[{week_date}] DepositIQ — {config['client']['name']} — starting run")

    print("  Fetching FRED benchmarks...")
    fred_data = fetch_fred_data(FRED_API_KEY)

    print("  Fetching peer bank rates from FDIC...")
    peer_groups = fetch_all_peer_rates(copy.deepcopy(config))

    config_with_rates = dict(config)
    config_with_rates["peer_groups"] = peer_groups

    subject_banks = config["subject_banks"]

    print("  Generating AI report...")
    report = generate_report(subject_banks, peer_groups, fred_data)

    print("  Building HTML email...")
    html_body = build_html_email(config_with_rates, report, fred_data)

    print("  Building Excel workbook...")
    excel_path = build_excel(config_with_rates, report, fred_data, week_date)
    print(f"  Excel saved: {excel_path}")

    to_email = config["client"]["report_email"]
    print(f"  Sending email to {to_email}...")
    status = send_email(html_body, to_email, None, week_date)
    print(f"  Email status: {status}")

    print("  Done.")

if __name__ == "__main__":
    run()
