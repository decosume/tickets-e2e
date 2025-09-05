# Lightweight Grafana Instance for React Embedding
# This creates a minimal Grafana setup that can be embedded in the React frontend

# ECS Cluster for Grafana
resource "aws_ecs_cluster" "grafana" {
  name = "support-analytics-grafana-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "support-analytics-grafana-cluster"
  }
}

# ECS Task Definition for Grafana
resource "aws_ecs_task_definition" "grafana" {
  family                   = "support-analytics-grafana"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512

  container_definitions = jsonencode([
    {
      name  = "grafana"
      image = "grafana/grafana:latest"
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "GF_SECURITY_ADMIN_USER"
          value = "admin"
        },
        {
          name  = "GF_SECURITY_ADMIN_PASSWORD"
          value = "admin123"
        },
        {
          name  = "GF_INSTALL_PLUGINS"
          value = "grafana-dynamodb-datasource"
        },
        {
          name  = "GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS"
          value = "true"
        },
        {
          name  = "GF_SERVER_DOMAIN"
          value = "grafana.everyset.com"
        },
        {
          name  = "GF_SERVER_ROOT_URL"
          value = "https://grafana.everyset.com"
        },
        {
          name  = "GF_SECURITY_ALLOW_EMBEDDING"
          value = "true"
        },
        {
          name  = "GF_SECURITY_COOKIE_SAMESITE"
          value = "none"
        },
        {
          name  = "GF_SECURITY_COOKIE_SECURE"
          value = "true"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.grafana.name
          awslogs-region        = "us-west-2"
          awslogs-stream-prefix = "grafana"
        }
      }
    }
  ])

  tags = {
    Name = "support-analytics-grafana-task"
  }
}

# ECS Service for Grafana
resource "aws_ecs_service" "grafana" {
  name            = "support-analytics-grafana"
  cluster         = aws_ecs_cluster.grafana.id
  task_definition = aws_ecs_task_definition.grafana.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.grafana.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana.arn
    container_name   = "grafana"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.grafana]

  tags = {
    Name = "support-analytics-grafana-service"
  }
}

# Security Group for Grafana
resource "aws_security_group" "grafana" {
  name        = "support-analytics-grafana-sg"
  description = "Grafana Security Group"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 3000
    to_port         = 3000
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "support-analytics-grafana-sg"
  }
}

# ALB Target Group for Grafana
resource "aws_lb_target_group" "grafana" {
  name     = "support-analytics-grafana-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "support-analytics-grafana-tg"
  }
}

# ALB Listener for Grafana
resource "aws_lb_listener" "grafana" {
  load_balancer_arn = aws_lb.main.arn
  port              = "3000"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }
}

# CloudWatch Log Group for Grafana
resource "aws_cloudwatch_log_group" "grafana" {
  name              = "/ecs/support-analytics-grafana"
  retention_in_days = 7

  tags = {
    Name = "support-analytics-grafana-logs"
  }
}

# Output for Grafana URL
output "grafana_url" {
  description = "URL to access Grafana for embedding"
  value       = "http://${aws_lb.main.dns_name}:3000"
}

output "grafana_embed_url" {
  description = "URL for embedding Grafana in React app"
  value       = "http://${aws_lb.main.dns_name}:3000/d-solo"
}



