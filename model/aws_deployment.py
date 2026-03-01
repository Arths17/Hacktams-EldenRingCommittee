"""
AWS deployment configuration for HealthOS API.
Supports ECS Fargate, CloudFormation, and Lambda deployment.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AWSDeploymentConfig:
    """AWS deployment configuration generator."""
    
    def __init__(self, env: str = "production", region: str = "us-east-1"):
        """Initialize deployment config.
        
        Args:
            env: Environment name (development, staging, production)
            region: AWS region
        """
        self.env = env
        self.region = region
    
    def get_ecs_task_definition(self) -> Dict[str, Any]:
        """Generate ECS Fargate task definition.
        
        Returns:
            ECS task definition JSON
        """
        return {
            "family": f"healthos-api-{self.env}",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "512",  # 0.5 vCPU
            "memory": "1024",  # 1 GB
            "containerDefinitions": [
                {
                    "name": "healthos-api",
                    "image": f"{{ACCOUNT_ID}}.dkr.ecr.{self.region}.amazonaws.com/healthos:latest",
                    "portMappings": [
                        {
                            "containerPort": 8000,
                            "hostPort": 8000,
                            "protocol": "tcp",
                        }
                    ],
                    "essential": True,
                    "environment": [
                        {"name": "ENV", "value": self.env},
                        {"name": "REDIS_URL", "value": f"redis://healthos-redis-{self.env}:6379"},
                    ],
                    "secrets": [
                        {"name": "SECRET_KEY", "valueFrom": f"arn:aws:secretsmanager:{self.region}:{{ACCOUNT_ID}}:secret:healthos/SECRET_KEY"},
                        {"name": "SUPABASE_URL", "valueFrom": f"arn:aws:secretsmanager:{self.region}:{{ACCOUNT_ID}}:secret:healthos/SUPABASE_URL"},
                        {"name": "SUPABASE_KEY", "valueFrom": f"arn:aws:secretsmanager:{self.region}:{{ACCOUNT_ID}}:secret:healthos/SUPABASE_KEY"},
                        {"name": "SENTRY_DSN", "valueFrom": f"arn:aws:secretsmanager:{self.region}:{{ACCOUNT_ID}}:secret:healthos/SENTRY_DSN"},
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/ecs/healthos-{self.env}",
                            "awslogs-region": self.region,
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                    "healthCheck": {
                        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                        "interval": 30,
                        "timeout": 10,
                        "retries": 3,
                        "startPeriod": 10,
                    },
                }
            ],
            "executionRoleArn": f"arn:aws:iam::{{ACCOUNT_ID}}:role/ecsTaskExecutionRole",
            "taskRoleArn": f"arn:aws:iam::{{ACCOUNT_ID}}:role/healthosTaskRole",
            "tags": [
                {"key": "Environment", "value": self.env},
                {"key": "Application", "value": "healthos"},
            ],
        }
    
    def get_ecs_service_config(self) -> Dict[str, Any]:
        """Generate ECS service configuration.
        
        Returns:
            ECS service config JSON
        """
        return {
            "serviceName": f"healthos-api-{self.env}",
            "cluster": f"healthos-{self.env}",
            "taskDefinition": f"healthos-api-{self.env}",
            "desiredCount": 2 if self.env == "production" else 1,
            "launchType": "FARGATE",
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-12345678",  # Replace with actual subnet IDs
                        "subnet-87654321",
                    ],
                    "securityGroups": ["sg-12345678"],  # Replace with actual security group
                    "assignPublicIp": "ENABLED",
                }
            },
            "loadBalancers": [
                {
                    "targetGroupArn": f"arn:aws:elasticloadbalancing:{self.region}:{{ACCOUNT_ID}}:targetgroup/healthos-{self.env}/abcd1234",
                    "containerName": "healthos-api",
                    "containerPort": 8000,
                }
            ],
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": f"arn:aws:autoscaling:{self.region}:{{ACCOUNT_ID}}:autoScalingGroup:12345678-1234-1234-1234-123456789012:autoScalingGroupName/healthos-{self.env}",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": 75,
                    "minimumScalingStepSize": 1,
                    "maximumScalingStepSize": 10,
                },
            },
            "tags": [
                {"key": "Environment", "value": self.env},
            ],
        }
    
    def get_autoscaling_policy(self) -> Dict[str, Any]:
        """Generate auto-scaling policy for ECS service.
        
        Returns:
            AutoScaling policy configuration
        """
        return {
            "PolicyName": f"healthos-{self.env}-cpu-autoscaling",
            "ServiceNamespace": "ecs",
            "ResourceId": f"service/healthos-{self.env}/healthos-api-{self.env}",
            "ScalableDimension": "ecs:service:DesiredCount",
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingScalingPolicyConfiguration": {
                "TargetValue": 70.0,  # Target CPU utilization
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "ECSServiceAverageCPUUtilization",
                },
                "ScaleOutCooldown": 60,
                "ScaleInCooldown": 300,
            },
        }
    
    def get_cloudwatch_alarms(self) -> list[Dict[str, Any]]:
        """Generate CloudWatch alarms for monitoring.
        
        Returns:
            List of CloudWatch alarm configurations
        """
        return [
            {
                "AlarmName": f"healthos-{self.env}-high-cpu",
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/ECS",
                "Statistic": "Average",
                "Period": 300,
                "EvaluationPeriods": 2,
                "Threshold": 80,
                "ComparisonOperator": "GreaterThanThreshold",
                "AlarmActions": ["arn:aws:sns:{self.region}:{{ACCOUNT_ID}}:healthos-alerts"],
            },
            {
                "AlarmName": f"healthos-{self.env}-high-memory",
                "MetricName": "MemoryUtilization",
                "Namespace": "AWS/ECS",
                "Statistic": "Average",
                "Period": 300,
                "EvaluationPeriods": 2,
                "Threshold": 85,
                "ComparisonOperator": "GreaterThanThreshold",
                "AlarmActions": ["arn:aws:sns:{self.region}:{{ACCOUNT_ID}}:healthos-alerts"],
            },
            {
                "AlarmName": f"healthos-{self.env}-unhealthy-tasks",
                "MetricName": "TaskCount",
                "Namespace": "AWS/ApplicationELB",
                "Statistic": "Average",
                "Period": 60,
                "EvaluationPeriods": 1,
                "Threshold": 0,
                "ComparisonOperator": "LessThanOrEqualToThreshold",
                "AlarmActions": ["arn:aws:sns:{self.region}:{{ACCOUNT_ID}}:healthos-critical"],
            },
        ]


def generate_deployment_configs(env: str = "production", region: str = "us-east-1"):
    """Generate all AWS deployment configurations.
    
    Args:
        env: Environment name
        region: AWS region
    """
    config = AWSDeploymentConfig(env, region)
    
    configs = {
        "ecs_task_definition": config.get_ecs_task_definition(),
        "ecs_service": config.get_ecs_service_config(),
        "autoscaling_policy": config.get_autoscaling_policy(),
        "cloudwatch_alarms": config.get_cloudwatch_alarms(),
    }
    
    # Write to files
    for name, config_dict in configs.items():
        with open(f"aws_{name}.json", "w") as f:
            json.dump(config_dict, f, indent=2)
        logger.info(f"✓ Generated aws_{name}.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_deployment_configs(env="production", region="us-east-1")
