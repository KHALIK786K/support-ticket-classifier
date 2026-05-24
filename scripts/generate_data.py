"""
Generate a realistic synthetic support-ticket dataset.

Produces 5 balanced classes (Finance / Billing / Technical / HR / Account)
with surface-form variation (templates + slot fills) so a TF-IDF model
sees real n-gram diversity. Writes to data/raw/tickets.csv.

Usage:
    python scripts/generate_data.py --rows 8000 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Templates per class. Slots {name}, {amount}, etc. are filled at generation.
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, list[str]] = {
    "Finance": [
        "I need a copy of invoice {invoice} for tax filing purposes.",
        "Tax invoice for order {order} is showing the wrong GST number, please correct it.",
        "Please share the financial statement for Q{quarter} {year}.",
        "Refund of {amount} has been processed but I haven't received any tax receipt.",
        "Need clarification on the TDS deduction shown in the last payout statement.",
        "The annual financial summary report is not loading on my dashboard.",
        "Requesting expense reimbursement of {amount} for client travel last week.",
        "I want to update the billing address on all my future invoices.",
        "Could you send the consolidated statement of accounts for FY{year}?",
        "Invoice {invoice} shows currency in USD instead of INR.",
    ],
    "Billing": [
        "I was charged twice for the same subscription on {date}, please refund the duplicate.",
        "My credit card was billed {amount} but the order shows failed status.",
        "Refund of {amount} not received even though it was promised 7 days ago.",
        "Why has my plan price increased from {amount} to a higher amount this month?",
        "I cancelled subscription on {date} but I am still being billed.",
        "Auto-renewal happened without my consent — please reverse the charge.",
        "Payment failed at checkout but the amount got deducted from my bank account.",
        "Need a refund — wrong item was charged on order {order}.",
        "Coupon code {code} is not getting applied at checkout.",
        "I see an unfamiliar charge of {amount} from your company — please clarify.",
    ],
    "Technical": [
        "Unable to login to the portal since this morning, getting a 500 server error.",
        "The mobile app crashes every time I open the dashboard on Android.",
        "Two-factor authentication SMS is not being delivered to my registered number.",
        "API endpoint /v1/orders is returning 503 since 9 AM IST.",
        "Page is stuck on loading spinner whenever I try to export data to CSV.",
        "Getting SSL certificate error when accessing the admin console.",
        "File upload feature is broken — keeps showing 'Network error' for any size.",
        "Search functionality is not returning any results even for exact match queries.",
        "Reports section shows blank chart, JavaScript console has multiple errors.",
        "Webhook events are not being delivered to my configured endpoint URL.",
    ],
    "HR": [
        "My salary slip for {month} is missing on the HR portal.",
        "Please update my emergency contact details and PAN information.",
        "I want to apply for paternity leave from {date} for two weeks.",
        "Provident fund balance has not been updated for the last quarter.",
        "Need help with reimbursement claim submission process for medical bills.",
        "My probation period was supposed to end on {date}, can you confirm status?",
        "Form 16 for the financial year {year} has not been issued yet.",
        "Requesting a change in my reporting manager due to team restructuring.",
        "I'd like to enrol in the company group health insurance for my dependents.",
        "Annual appraisal letter has discrepancies in the variable pay calculation.",
    ],
    "Account": [
        "I forgot the password for my account and the reset email never arrives.",
        "How do I delete my account permanently from your platform?",
        "Need to merge two duplicate accounts under the same email address.",
        "Cannot update my profile picture — error says 'unsupported format'.",
        "My account was suspended without any notification, please reinstate it.",
        "I want to change my registered email address from old to new one.",
        "Two-step verification is locked out — recovery codes don't work either.",
        "Profile shows incorrect name despite multiple update attempts.",
        "Need to transfer ownership of my account to another team member.",
        "How can I downgrade my account from premium to free tier?",
    ],
}

SLOTS = {
    "invoice": lambda r: f"INV-{r.randint(10000, 99999)}",
    "order":   lambda r: f"A-{r.randint(1000, 9999)}",
    "amount":  lambda r: f"Rs.{r.choice([499, 999, 1499, 2999, 4999, 9999])}",
    "quarter": lambda r: str(r.randint(1, 4)),
    "year":    lambda r: str(r.choice([2023, 2024, 2025])),
    "date":    lambda r: f"{r.randint(1, 28)} {r.choice(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}",
    "month":   lambda r: r.choice(["January","February","March","April","May","June","July","August","September","October","November","December"]),
    "code":    lambda r: r.choice(["SAVE20", "WELCOME10", "FLAT100", "FREESHIP", "VIP30"]),
}

PREFIXES = [
    "Hi team, ", "Hello, ", "Hi, ", "", "Dear support, ", "",
    "Regards, ", "", "", "",
]

SUFFIXES = [
    " Please help me resolve this asap.",
    " Looking forward to your response.",
    " This is quite urgent.",
    " Thanks in advance.",
    "",
    " Let me know what details are needed.",
    " Awaiting your reply.",
    "",
    "",
    "",
]


def fill(template: str, r: random.Random) -> str:
    out = template
    for slot, gen in SLOTS.items():
        token = "{" + slot + "}"
        while token in out:
            out = out.replace(token, gen(r), 1)
    return out


def make_subject(body: str, r: random.Random) -> str:
    # 5-9 word subject derived from the body
    words = [w.strip(".,") for w in body.split() if w.isalpha()]
    if len(words) < 6:
        return body[:60]
    n = r.randint(5, 9)
    return " ".join(words[:n]).capitalize()


def generate(rows: int, seed: int, out_path: Path) -> None:
    r = random.Random(seed)
    classes = list(TEMPLATES)
    per_class = rows // len(classes)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "body", "text", "category"])

        for cls in classes:
            templates = TEMPLATES[cls]
            for _ in range(per_class):
                t = r.choice(templates)
                body = r.choice(PREFIXES) + fill(t, r) + r.choice(SUFFIXES)
                subject = make_subject(body, r)
                text = f"{subject}. {body}"
                writer.writerow([subject, body, text, cls])

    print(f"✓ Wrote {per_class * len(classes)} tickets across {len(classes)} classes → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic support tickets")
    parser.add_argument("--rows", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/raw/tickets.csv"))
    args = parser.parse_args()
    generate(args.rows, args.seed, args.out)
