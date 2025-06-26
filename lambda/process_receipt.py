import json, os, uuid, re
from decimal import Decimal
from datetime import datetime
import boto3

def extract_fields_and_lineitems(lines):
    # 1. Vendor extraction (find "Walmart" or first all-caps line)
    vendor = None
    for i, line in enumerate(lines[:10]):
        if re.search(r'walmart', line, re.I):
            vendor = "Walmart"
            break
    if not vendor:
        for line in lines[:10]:
            if line.strip().isupper() and len(line.strip()) > 4:
                vendor = line.strip().title()
                break
    if not vendor:
        vendor = "Unknown"

    # 2. Date extraction (MM/DD/YYYY, MM/DD/YY, or YYYY-MM-DD)
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
        date = datetime.utcnow().isoformat()

    # 3. Total extraction
    total = None
    total_pat = re.compile(r'(total|amount due|balance due)[^\d]{0,10}([\d,.]+)', re.I)
    for line in lines[::-1]:  # search from bottom up
        m = total_pat.search(line)
        if m:
            total = m.group(2)
            break
    if not total:
        # Fallback: find last number over $10
        for line in lines[::-1]:
            price_m = re.search(r'([\d]+\.[\d]{2})', line)
            if price_m:
                p = float(price_m.group(1))
                if p > 10:
                    total = price_m.group(1)
                    break
    try:
        total = Decimal(total.replace(',', '')) if total else Decimal('0')
    except Exception:
        total = Decimal('0')

    # 4. Line Items extraction: all lines with prices, skip totals/subtotals/tax/etc.
    lineitems = []
    for line in lines:
        if re.search(r'(total|subtotal|tax|amount due|balance due|change due|debit tend)', line, re.I):
            continue
        price_matches = re.findall(r'([\d]+\.[\d]{2})', line)
        if price_matches:
            for price in price_matches:
                desc = line.replace(price, '').strip(" -:.,X")
                # Avoid empty descriptions
                if desc and not desc.isdigit():
                    lineitems.append({'Description': desc, 'Amount': price})

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
            print("❌ Textract failed:", e)
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
            print(f"✅ Successfully wrote ExpenseId={expense_id} to DynamoDB")
        except Exception as e:
            print("❌ DynamoDB put_item failed:", e)

    return {
        'statusCode': 200,
        'body': json.dumps({'msg': 'Processed receipts.'})
    }
