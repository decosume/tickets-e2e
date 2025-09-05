# BugTracker DynamoDB Table with Unified Schema
# Based on the design shown in the images

resource "aws_dynamodb_table" "bug_tracker" {
  name           = "BugTracker"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "priority"
    type = "S"
  }

  attribute {
    name = "state"
    type = "S"
  }

  attribute {
    name = "sourceSystem"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  # GSI1: priority-index
  global_secondary_index {
    name            = "priority-index"
    hash_key        = "priority"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI2: state-index
  global_secondary_index {
    name            = "state-index"
    hash_key        = "state"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI3: source-index
  global_secondary_index {
    name            = "source-index"
    hash_key        = "sourceSystem"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  tags = {
    Name        = "BugTracker"
    Environment = "production"
    Purpose     = "unified-bug-tracking"
  }
}

# IAM Role for Lambda/ECS to access DynamoDB
resource "aws_iam_role" "bug_tracker_access" {
  name = "BugTrackerAccessRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "bug_tracker_dynamodb_policy" {
  name        = "BugTrackerDynamoDBPolicy"
  description = "Policy for accessing BugTracker DynamoDB table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.bug_tracker.arn,
          "${aws_dynamodb_table.bug_tracker.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:ListTables"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "bug_tracker_policy_attachment" {
  role       = aws_iam_role.bug_tracker_access.name
  policy_arn = aws_iam_policy.bug_tracker_dynamodb_policy.arn
}

# Output the table ARN and name
output "bug_tracker_table_arn" {
  description = "ARN of the BugTracker DynamoDB table"
  value       = aws_dynamodb_table.bug_tracker.arn
}

output "bug_tracker_table_name" {
  description = "Name of the BugTracker DynamoDB table"
  value       = aws_dynamodb_table.bug_tracker.name
}

output "bug_tracker_access_role_arn" {
  description = "ARN of the IAM role for accessing BugTracker"
  value       = aws_iam_role.bug_tracker_access.arn
}


