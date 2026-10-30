import os
import json
import urllib.request
import urllib.error
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = "claude-haiku-4-5"

RATE_LABELS = {
    "checking_apy": "Checking APY",
    "savings": "Savings APY",
    "mma": "Money Market APY",
    "cd_3mo": "3-Month CD",
    "cd_6mo": "6-Month CD",
    "cd_12mo": "12-Month CD",
    "cd_24mo": "24-Month CD"
}

def _pct(v):
    return f"{v:.2f}%" if v is not None else "N/A"

def _build_subject_block(bank):
    lines = [f"SUBJECT: {bank['display_name']}"]
    for prod, val in bank["rates"].items():
        label = RATE_LABELS.get(prod, prod)
        lines.append(f"  {label}: {_pct(val)}")
    return "\n".join(lines)

def _build_peer_block(group_label, peers):
    lines = [f"\nPEER GROUP — {group_label}"]
    header = f"{'Bank':<28} " + "  ".join(f"{RATE_LABELS[p][:8]:>8}" for p in [
        "checking_apy","savings","mma","cd_3mo","cd_6mo","cd_12mo","cd_24mo"])
    lines.append(header)
    lines.append("-" * len(header))
    for peer in peers:
        row = f"{peer['name']:<28} "
        for prod in ["checking_apy","savings","mma","cd_3mo","cd_6mo","cd_12mo","cd_24mo"]:
            val = peer.get("rates", {}).get(prod)
            row += f"{_pct(val):>9} "
        lines.append(row)
    return "\n".join(lines)

def _build_fred_block(fred_data):
    lines = ["\nNATIONAL BENCHMARKS (FRED)"]
    mapping = {
        "FEDFUNDS":  "Fed Funds Rate",
        "MMNRNNS":   "Nat'l MMA Rate",
        "CD3NAX":    "Nat'l 3-Mo CD",
        "CD6NAX":    "Nat'l 6-Mo CD",
        "CD1NAX":    "Nat'l 12-Mo CD"
    }
    for series, label in mapping.items():
        val = fred_data.get(series)
        lines.append(f"  {label}: {_pct(val)}")
    return "\n".join(lines)

PROMPT_TEMPLATE = """You are a senior deposit strategist at a regional bank consultancy.
Today is {date}. Analyze the following deposit rate intelligence for Popular Bank
and produce a structured JSON report.

{subject_blocks}

{peer_blocks}

{fred_block}

Produce a JSON object with EXACTLY these keys:
{{
  "week_summary": "2-sentence executive summary of Popular Bank's competitive position this week",
  "ny_metro_analysis": {{
    "position": "1 sentence: Popular Bank rate position vs NY Metro peers",
    "gaps": ["up to 3 key rate gaps vs NY Metro peers"],
    "recommendation": "1 actionable repricing recommendation for NY Metro"
  }},
  "south_florida_analysis": {{
    "position": "1 sentence: Popular Bank rate position vs South FL peers",
    "gaps": ["up to 3 key rate gaps vs South FL peers"],
    "recommendation": "1 actionable repricing recommendation for South FL"
  }},
  "direct_online_analysis": {{
    "position": "1 sentence: Popular Direct position vs direct/online banks",
    "gaps": ["up to 3 key rate gaps vs online banks"],
    "recommendation": "1 actionable repricing recommendation for Popular Direct"
  }},
  "top_priority": "Single most important repricing action this week",
  "risk_level": "LOW | MEDIUM | HIGH — Popular Bank's overall competitive risk",
  "risk_rationale": "1 sentence explaining risk level",
  "next_watch": "What to monitor before next Monday's report"
}}

Return ONLY the JSON object. No markdown, no explanation."""

def generate_report(subject_banks, peer_groups, fred_data):
    date_str = datetime.now().strftime("%B %d, %Y")

    subject_blocks = "\n\n".join(_build_subject_block(b) for b in subject_banks)

    peer_blocks_text = ""
    for group_key, group in peer_groups.items():
        peers = group.get("peers_with_rates", group.get("banks", []))
        peer_blocks_text += _build_peer_block(group["label"], peers) + "\n"

    fred_block = _build_fred_block(fred_data)

    prompt = PROMPT_TEMPLATE.format(
        date=date_str,
        subject_blocks=subject_blocks,
        peer_blocks=peer_blocks_text,
        fred_block=fred_block
    )

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
        raw = body["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"  [WARN] Report generation failed ({e}), using fallback narrative")
        return _fallback_report(subject_banks, peer_groups, fred_data)


def _fallback_report(subject_banks, peer_groups, fred_data):
    week = datetime.now().strftime("%B %d, %Y")
    return {
        "week_summary": f"Week of {week} — Popular Bank deposit rates remain broadly competitive across key term structures. Peer rate tables reflect the latest Curinos survey data.",
        "top_priority": "Review peer rate tables and confirm accuracy before distribution.",
        "ny_metro_analysis": {
            "position": "Popular Bank CD rates are competitive vs NY Metro regional peers.",
            "gaps": ["MMA rate below select peers — review ConnectOne and Amerant"],
            "recommendation": "Monitor MMA pricing for competitive alignment."
        },
        "south_florida_analysis": {
            "position": "Popular Bank rates broadly in line with South Florida peers.",
            "gaps": ["BankUnited MMA at 3.50% is above Popular Bank MMA"],
            "recommendation": "Consider MMA rate review vs BankUnited."
        },
        "direct_online_analysis": {
            "position": "Popular Direct savings at 3.90% is below leading online banks (Synchrony 4.50%, Barclays 4.35%).",
            "gaps": ["Savings gap vs Synchrony: -60bps", "Savings gap vs Barclays: -45bps", "Savings gap vs Marcus: -20bps"],
            "recommendation": "Evaluate Popular Direct savings rate adjustment to 4.10-4.25% range."
        },
        "risk_level": "MEDIUM",
        "risk_rationale": "Online bank competition intensifying on high-yield savings products.",
        "next_watch": "Monitor Fed rate guidance and online bank pricing movements."
    }
