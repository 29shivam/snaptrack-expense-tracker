import os, json, csv, io
from datetime import datetime, timedelta
from decimal import Decimal
import boto3

dynamodb = boto3.resource('dynamodb')
s3       = boto3.client('s3')
ses      = boto3.client('ses')

EXPENSES_TABLE  = os.environ['EXPENSES_TABLE']
REPORTS_BUCKET  = os.environ['REPORTS_BUCKET']
REPORT_RECIPIENT= os.environ['REPORT_RECIPIENT']

table = dynamodb.Table(EXPENSES_TABLE)

def lambda_handler(event, context):
    # Get last 30 days
    now   = datetime.utcnow()
    start = (now - timedelta(days=30)).isoformat()
    end   = now.isoformat()

    # Scan expenses table for last 30 days
    fe = boto3.dynamodb.conditions.Attr('Date').between(start, end)
    try:
        resp = table.scan(FilterExpression=fe)
        items = resp.get('Items', [])
    except Exception as e:
        print("DynamoDB scan failed:", e)
        return {'statusCode':500, 'body':json.dumps({'error':str(e)})}

    # Build CSV
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['ExpenseId','Vendor','Date','Category','Total','ReceiptURL'])
    for it in items:
        writer.writerow([
            it.get('ExpenseId',''),
            it.get('Vendor',''),
            it.get('Date',''),
            it.get('Category',''),
            float(it.get('Total',0)),
            it.get('ReceiptS3Path','')
        ])
    csv_data = csv_buffer.getvalue().encode('utf-8')

    # Upload CSV to S3
    key = f"monthly_report_{now.strftime('%Y-%m')}.csv"
    try:
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=key,
            Body=csv_data,
            ContentType='text/csv'
        )
    except Exception as e:
        print("S3 put_object failed:", e)
        return {'statusCode':500, 'body':json.dumps({'error':str(e)})}

    url = f"https://{REPORTS_BUCKET}.s3.amazonaws.com/{key}"

    # Send email via SES
    subject = f"Expense Report for {now.strftime('%B %Y')}"
    body    = (f"Your monthly expense report is here:\n{url}\n\n"
               "Regards,\nExpense Tracker")
    try:
        ses.send_email(
            Source=REPORT_RECIPIENT,
            Destination={'ToAddresses':[REPORT_RECIPIENT]},
            Message={
                'Subject':{'Data':subject},
                'Body':{'Text':{'Data':body}}
            }
        )
    except Exception as e:
        print("SES send_email failed:", e)
        return {'statusCode':500, 'body':json.dumps({'error':str(e)})}

    return {
        'statusCode': 200,
        'body': json.dumps({'message':'Report sent', 'url':url})
    }
