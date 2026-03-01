"""
Secrets management system for HealthOS API.
Securely handles API keys, database credentials, and sensitive configuration.
Supports environment variables and AWS Secrets Manager.
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# AWS Secrets Manager support (optional)
SECRETS_MANAGER_ENABLED = False

try:
    import boto3
    from botocore.exceptions import ClientError
    
    SECRETS_MANAGER_ENABLED = True
    secrets_client = boto3.client('secretsmanager')
    logger.info("✓ AWS Secrets Manager available")
except ImportError:
    logger.info("✗ AWS SDK not installed (Secrets Manager disabled)")
except Exception as e:
    logger.warning(f"✗ AWS Secrets Manager unavailable: {e}")


class SecretsManager:
    """Centralized secrets management with environment and AWS support."""
    
    def __init__(self):
        """Initialize secrets manager."""
        self.local_cache: Dict[str, Any] = {}
        self.load_from_env()
    
    def load_from_env(self):
        """Load secrets from environment variables."""
        required_secrets = [
            "SECRET_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "SENTRY_DSN",
        ]
        
        for secret in required_secrets:
            value = os.environ.get(secret)
            if value:
                self.local_cache[secret] = value
            else:
                logger.warning(f"Secret {secret} not found in environment")
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from local cache, environment, or AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret (e.g., 'SUPABASE_KEY')
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        # 1. Try local cache first (fastest)
        if secret_name in self.local_cache:
            return self.local_cache[secret_name]
        
        # 2. Try environment variable
        env_value = os.environ.get(secret_name)
        if env_value:
            self.local_cache[secret_name] = env_value
            return env_value
        
        # 3. Try AWS Secrets Manager (slower, use sparingly)
        if SECRETS_MANAGER_ENABLED:
            aws_value = self._get_from_aws_secrets(secret_name)
            if aws_value:
                self.local_cache[secret_name] = aws_value
                return aws_value
        
        # 4. Return default
        return default
    
    def _get_from_aws_secrets(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from AWS Secrets Manager.
        
        Args:
            secret_name: Name of secret in AWS
            
        Returns:
            Secret value or None
        """
        if not SECRETS_MANAGER_ENABLED:
            return None
        
        try:
            response = secrets_client.get_secret_value(SecretId=secret_name)  # type: ignore
            
            if 'SecretString' in response:
                return response['SecretString']
            else:
                logger.warning(f"Secret {secret_name} is not a string")
                return None
        
        except ClientError as e:  # type: ignore
            error_code = e.response['Error']['Code']
            
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Secret {secret_name} not found in AWS Secrets Manager")
            elif error_code == 'InvalidRequestException':
                logger.error(f"Invalid request for secret {secret_name}")
            elif error_code == 'InvalidParameterException':
                logger.error(f"Invalid parameter for secret {secret_name}")
            elif error_code == 'DecryptionFailure':
                logger.error(f"Decryption failed for secret {secret_name}")
            elif error_code == 'InternalServiceError':
                logger.error(f"AWS service error retrieving {secret_name}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
            return None
    
    def rotate_secret(self, secret_name: str, new_value: str):
        """Rotate a secret (update environment variable).
        
        Args:
            secret_name: Name of secret to rotate
            new_value: New value for the secret
        """
        # Update local cache
        self.local_cache[secret_name] = new_value
        
        # Update environment variable
        os.environ[secret_name] = new_value
        
        logger.info(f"✓ Secret {secret_name} rotated (local only)")
        
        # Note: In production, also update AWS Secrets Manager:
        # if SECRETS_MANAGER_ENABLED:
        #     secrets_client.put_secret_value(
        #         SecretId=secret_name,
        #         SecretString=new_value
        #     )
    
    def validate_required_secrets(self) -> bool:
        """Validate all required secrets are available.
        
        Returns:
            True if all required secrets present, False otherwise
        """
        required = [
            "SECRET_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]
        
        missing = []
        for secret in required:
            if not self.get_secret(secret):
                missing.append(secret)
        
        if missing:
            logger.error(f"Missing required secrets: {', '.join(missing)}")
            return False
        
        logger.info(f"✓ All {len(required)} required secrets validated")
        return True


# Global secrets manager instance
secrets_manager = SecretsManager()


# Utility functions for common secrets
def get_secret_key() -> str:
    """Get JWT secret key."""
    return secrets_manager.get_secret("SECRET_KEY", "elden_ring_default")

def get_supabase_url() -> str:
    """Get Supabase project URL."""
    return secrets_manager.get_secret("SUPABASE_URL", "")

def get_supabase_key() -> str:
    """Get Supabase API key."""
    return secrets_manager.get_secret("SUPABASE_KEY", "")

def get_database_url() -> str:
    """Get database connection URL."""
    return secrets_manager.get_secret("DATABASE_URL", "")

def get_redis_url() -> str:
    """Get Redis connection URL."""
    return secrets_manager.get_secret("REDIS_URL", "redis://localhost:6379")

def get_sentry_dsn() -> Optional[str]:
    """Get Sentry error tracking DSN."""
    return secrets_manager.get_secret("SENTRY_DSN")

def get_openai_key() -> Optional[str]:
    """Get OpenAI API key (if using)."""
    return secrets_manager.get_secret("OPENAI_API_KEY")

def get_smtp_config() -> Dict[str, str]:
    """Get email (SMTP) configuration."""
    return {
        "host": secrets_manager.get_secret("SMTP_HOST", "smtp.gmail.com"),
        "port": secrets_manager.get_secret("SMTP_PORT", "587"),
        "user": secrets_manager.get_secret("SMTP_USER", ""),
        "password": secrets_manager.get_secret("SMTP_PASSWORD", ""),
        "from": secrets_manager.get_secret("SMTP_FROM", "noreply@healthos.ai"),
    }


def validate_secrets() -> bool:
    """Validate all required secrets at startup."""
    return secrets_manager.validate_required_secrets()
