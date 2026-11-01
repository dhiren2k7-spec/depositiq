import os
import json
import copy
from datetime import datetime

from fetch_data import fetch_all_peer_rates, fetch_fred_data
from fetch_popular_direct import fetch_popular_direct_rates
from generate_report import generate_report
from send_email import build_html_email, send_email
from html_workbook import build_html_workbook

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

    print("  Fetching Popular Direct live rates from cdvalet.com...")
    for bank in config["subject_banks"]:
        if bank.get("id") == "popular_direct":
            bank["rates"] = fetch_popular_direct_rates(bank.get("rates", {}))

    config_with_rates = dict(config)
    config_with_rates["peer_groups"] = peer_groups

    # Resolve promo excel path relative to config file so it works from any CWD
    _config_dir = os.path.dirname(os.path.abspath(CONFIG_PATH))
    if config_with_rates.get("promo_cd_excel_path"):
        config_with_rates["promo_cd_excel_path"] = os.path.join(
            _config_dir, "..", config_with_rates["promo_cd_excel_path"]
        )

    subject_banks = config["subject_banks"]

    print("  Generating AI report...")
    report = generate_report(subject_banks, peer_groups, fred_data)

    print("  Building HTML email...")
    html_body = build_html_email(config_with_rates, report, fred_data)

    print("  Building HTML workbook...")
    workbook_html = build_html_workbook(config_with_rates, report, fred_data, week_date)

    # Save HTML outputs to disk
    os.makedirs("../output", exist_ok=True)
    safe_date = week_date.replace(" ", "_").replace(",", "")
    html_path = f"../output/DepositIQ_{safe_date}.html"
    workbook_path = f"../output/DepositIQ_Workbook_{safe_date}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_body)
    print(f"  HTML email saved: {html_path}")
    with open(workbook_path, "w", encoding="utf-8") as f:
        f.write(workbook_html)
    print(f"  HTML workbook saved: {workbook_path}")

    to_email = config["client"]["report_email"]
    bcc_email = config["client"].get("report_bcc", "")
    print(f"  Sending email to {to_email}...")
    status = send_email(html_body, to_email, None, week_date,
                        html_path=html_path,
                        workbook_path=workbook_path,
                        bcc_email=bcc_email)
    print(f"  Email status: {status}")

    print("  Done.")

if __name__ == "__main__":
    run()
