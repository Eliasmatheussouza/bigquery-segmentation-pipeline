# -*- coding: utf-8 -*-
"""
CDP Attribute Push — BigQuery to Marketing Platform
====================================================
Reads segmented customer data from BigQuery and pushes custom attributes
to a CDP (Customer Data Platform) via REST API upsert endpoint.

Flow:
  BigQuery (segmentation table)  ──►  CDP API (user attribute upsert)

Attributes pushed per user:
  - qtd_itens_comprados : total items purchased in most recent order
  - valor_compra        : total purchase value in most recent order
"""

import json
import time
import datetime
import pandas as pd
import requests

from decimal import Decimal
from google.cloud import bigquery
from dotenv import load_dotenv
import os

# ── Environment ────────────────────────────────────────────────────────────────
load_dotenv()

CDP_API_URL       = os.getenv("CDP_API_URL")
PARTNER_NAME      = os.getenv("CDP_PARTNER_NAME")
REQUEST_TOKEN     = os.getenv("CDP_REQUEST_TOKEN")
GCP_PROJECT_ID    = os.getenv("GCP_PROJECT_ID")

API_PAYLOAD_LIMIT = 1000

client = bigquery.Client(project=GCP_PROJECT_ID)

# ── 1. Extract — Read segmented customers from BigQuery ───────────────────────
QUERY = """
WITH cleaned AS (
  SELECT
    email,
    itens_pedido,
    valor_compra
  FROM `your_project.your_dataset.segmentation_table`
  WHERE
    DATE(updatedAt) = CURRENT_DATE()
    AND REGEXP_CONTAINS(TRIM(email), r'@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+')
    AND LENGTH(TRIM(email)) - LENGTH(REPLACE(TRIM(email), '@', '')) = 1
    AND TRIM(email) NOT LIKE '% %'
)
SELECT * FROM cleaned
"""

df = client.query(QUERY).to_dataframe()

# ── 2. Transform — Normalize numeric types ────────────────────────────────────
def fix_decimal(x):
    """Converts Decimal and edge cases to float, returns None for empty values."""
    if isinstance(x, Decimal):
        return float(x)
    if x in ["", None]:
        return None
    try:
        return float(x)
    except Exception:
        return None

for col in ["itens_pedido", "valor_compra"]:
    df[col] = df[col].apply(fix_decimal)

df = df.replace({"<NA>": None, "NaT": None, "nan": None, "NaN": None})
df.astype(object).where(pd.notna(df), None)

print(f"Records loaded: {len(df)}")

# ── 3. Load — Push attributes to CDP in batches ───────────────────────────────
headers = {
    "X-PARTNER-NAME": PARTNER_NAME,
    "X-REQUEST-TOKEN": REQUEST_TOKEN,
    "Content-Type": "application/json"
}

if df.empty:
    print("No records found. Exiting.")
else:
    users_batch = []
    count_rows  = 0

    for _, row in df.iterrows():
        users_batch.append({
            "identifiers": {
                "email": row["email"]
            },
            "attributes": {
                "custom": {
                    "qtd_itens_comprados": row["itens_pedido"],
                    "valor_compra":        row["valor_compra"]
                }
            }
        })
        count_rows += 1

        # Send batch when limit is reached
        if count_rows == API_PAYLOAD_LIMIT:
            try:
                response = requests.post(
                    CDP_API_URL,
                    headers=headers,
                    data=json.dumps({"users": users_batch})
                )
                print("|", end="", flush=True)
            except Exception as e:
                print(f"\nBatch error: {e} ({len(users_batch)} records affected)")

            users_batch = []
            count_rows  = 0

    # Send remaining records
    if users_batch:
        response = requests.post(
            CDP_API_URL,
            headers=headers,
            data=json.dumps({"users": users_batch})
        )
        print("|", end="", flush=True)

    # Final response log
    if "response" in dir():
        try:
            echo_response = response.json()
        except Exception:
            echo_response = response.text

        print(f"\nAPI response: {echo_response}")
        print(f"Total records pushed: {len(df)}")
