# 29shivam
# SnapTrack: Your Receipts, Instantly Organized

SnapTrack is a serverless expense tracker that automates receipt entry for small businesses. Upload a receipt photo to S3 and get structured expense data in DynamoDB—no manual entry!

## How to Deploy

1. Create AWS resources (S3, DynamoDB, SES, Lambda)
2. Set environment variables for each Lambda function
3. Attach necessary IAM roles
4. Wire up S3 trigger, API Gateway, and (optional) EventBridge
5. Test by uploading a receipt and checking DynamoDB

## Built With

- AWS Lambda, S3, Textract, DynamoDB, SES, API Gateway, Python, Regex, Boto3
