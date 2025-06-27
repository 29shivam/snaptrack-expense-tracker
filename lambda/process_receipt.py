import os
import json
import uuid
import re
from decimal import Decimal
from datetime import datetime
import boto3

def extract_fields_and_lineitems(lines):
    # 1. Vendor Extraction
    vendor = None
    for line in lines[:10]:
        if re.search(r'^[A-Z][A-Z0-9 &\.\-]{4,}$', line.strip()):
            vendor = line.strip().title()
            break
    if not vendor:
        vendor = "Unknown"

    # 2. Date Extraction (matches MM/DD/YY, MM/DD/YYYY, or YYYY-MM-DD)
    date = None
    date_pat = re.compile(r'(\d{2}/\d{2}/\d{2,4}|\d{4}-\d{2}-\d{2})')
    for line in lines:
        m = date_pat.search(line)
        if m:
            dstr = m.group(1)
            try:
                if len(dstr) == 10 and dstr.count('/') == 2:
                    date_obj = datetime.strptime(dstr, "%m/%d/%Y")
                elif len(dstr) == 8 and dstr.count('/') == 2:
                    date_obj = datetime.strptime(dstr, "%m/%d/%y")
                elif len(dstr) == 10 and dstr.count('-') == 2:
                    date_obj = datetime.strptime(dstr, "%Y-%m-%d")
                else:
                    raise ValueError()
                date = date_obj.strftime("%Y-%m-%d")
            except Exception:
                date = dstr
            break
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    # 3. Total Extraction (search from bottom up)
    total = None
    total_pat = re.compile(r'(total|amount due|balance due)[^\d]{0,10}([\d]+\.[\d]{2})', re.I)
    for line in lines[::-1]:
        m = total_pat.search(line)
        if m:
            total = m.group(2)
            break
    if not total:
        # Fallback: last number over $5
        for line in lines[::-1]:
            price_m = re.search(r'([\d]+\.[\d]{2})', line)
            if price_m:
                p = float(price_m.group(1))
                if p > 5:
                    total = price_m.group(1)
                    break
    try:
        total = Decimal(total.replace(',', '')) if total else Decimal('0')
    except Exception:
        total = Decimal('0')

    # 4. Line Items Extraction (universal logic)
    summary_skip = re.compile(
        r'(total|tax|change due|amount due|subtotal|balance|payment|tender|tend|visa|master|cash|debit|paid|refund|number of items|qty|quantity|item sold|approved|chip read|card|aid|resp|merchant|seq|app|thank you|date|time|balance|trans id|auth|op#|amount)',
        re.I
    )

    lineitems = []
    prev_desc = None
    for i, line in enumerate(lines):
        if summary_skip.search(line): continue

        # a. "desc    9.99"
        m = re.match(r'^(.*?)[ \t]+([\d]+\.[\d]{2})$', line.strip())
        if m and len(m.group(1).strip()) > 1:
            desc = m.group(1).strip(" .:-")
            price = m.group(2)
            lineitems.append({'Description': desc, 'Amount': price})
            prev_desc = None
            continue

        # b. "2 @ 6.99"
        m2 = re.match(r'^(\d+)\s*@\s*([\d]+\.[\d]{2})', line.strip())
        if m2:
            qty, price = m2.groups()
            desc = f"{qty} @ {price}"
            lineitems.append({'Description': desc, 'Amount': price})
            prev_desc = None
            continue

        # c. Standalone price line after a likely product line
        m3 = re.match(r'^([\d]+\.[\d]{2})$', line.strip())
        if m3 and prev_desc and len(prev_desc) > 2 and not summary_skip.search(prev_desc):
            price = m3.group(1)
            lineitems.append({'Description': prev_desc.strip(" .:-"), 'Amount': price})
            prev_desc = None
            continue

        # d. If not price, remember for next round
        prev_desc = line

    return {
        'vendor': vendor,
        'date': date,
        'total': str(total),
        'lineitems': lineitems
    }

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    textract = boto3.client('textract')
    dynamodb = boto3.resource('dynamodb')

    EXPENSES_TABLE = os.environ['EXPENSES_TABLE']
    table = dynamodb.Table(EXPENSES_TABLE)

    for r in event['Records']:
        bucket = r['s3']['bucket']['name']
        key = r['s3']['object']['key']
        print(f"🔍 Processing S3 object: s3://{bucket}/{key}")

        try:
            resp = textract.detect_document_text(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}}
            )
            lines = [b['Text'] for b in resp['Blocks'] if b['BlockType'] == 'LINE']
            print("🔍 OCR lines:", lines)
        except Exception as e:
            print(" Textract failed:", e)
            continue

        fields = extract_fields_and_lineitems(lines)
        print("🔍 Extracted fields:", fields)

        vendor = fields.get('vendor', 'Unknown')
        date_s = fields.get('date', datetime.utcnow().isoformat())
        total = Decimal(fields.get('total', '0'))
        lineitems = fields.get('lineitems', [])

        expense_id = str(uuid.uuid4())
        item = {
            'ExpenseId': expense_id,
            'Vendor': vendor,
            'Date': date_s,
            'Total': total,
            'Category': 'General',
            'ReceiptS3Path': f"s3://{bucket}/{key}",
            'LineItems': lineitems,
            'CreatedAt': datetime.utcnow().isoformat()
        }

        try:
            table.put_item(Item=item)
            print(f" Successfully wrote ExpenseId={expense_id} to DynamoDB")
        except Exception as e:
            print("❌ DynamoDB put_item failed:", e)

    return {
        'statusCode': 200,
        'body': json.dumps({'msg': 'Processed receipts.'})
    }
