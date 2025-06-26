import os, json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
EXPENSES_TABLE = os.environ['EXPENSES_TABLE']
table = dynamodb.Table(EXPENSES_TABLE)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    # For demo, just return all expenses; add date filters later if needed.
    try:
        resp = table.scan()
        items = resp.get('Items', [])
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(items, default=decimal_default)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
