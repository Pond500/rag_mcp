"""
Langfuse Configuration for Self-Hosted Instance

ทีม Observe: กรอกข้อมูลด้านล่างเพื่อเชื่อมต่อ Langfuse
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class LangfuseConfig:
    """Configuration สำหรับเชื่อมต่อ Langfuse Self-Hosted"""
    
    # Langfuse Server URL (รองรับทั้ง LANGFUSE_HOST และ LANGFUSE_BASE_URL)
    host: str = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000")
    
    # API Keys (ได้จาก Langfuse Dashboard → Settings → API Keys)
    public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    
    # Project name
    project_name: str = os.getenv("LANGFUSE_PROJECT", "mcp-rag-v2")
    
    # Environment (development, staging, production)
    environment: str = os.getenv("LANGFUSE_ENVIRONMENT", "development")
    
    # Enable/Disable tracing
    enabled: bool = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
    
    # Debug mode
    debug: bool = os.getenv("LANGFUSE_DEBUG", "false").lower() == "true"
    
    def validate(self) -> Tuple[bool, str]:
        """ตรวจสอบว่า config ครบถ้วนหรือไม่"""
        if not self.host:
            return False, "❌ LANGFUSE_HOST ไม่ได้ตั้งค่า"
        if not self.public_key:
            return False, "❌ LANGFUSE_PUBLIC_KEY ไม่ได้ตั้งค่า"
        if not self.secret_key:
            return False, "❌ LANGFUSE_SECRET_KEY ไม่ได้ตั้งค่า"
        return True, "✅ Langfuse config พร้อมใช้งาน"


# Singleton instance
_config: Optional[LangfuseConfig] = None


def get_langfuse_config() -> LangfuseConfig:
    """Get Langfuse configuration"""
    global _config
    if _config is None:
        _config = LangfuseConfig()
    return _config


def print_connection_info():
    """แสดงข้อมูล connection สำหรับ debugging"""
    config = get_langfuse_config()
    valid, message = config.validate()
    
    print("=" * 50)
    print("🔗 Langfuse Connection Info")
    print("=" * 50)
    print(f"Host:        {config.host}")
    print(f"Public Key:  {config.public_key[:15]}..." if config.public_key else "Public Key:  ❌ Not set")
    print(f"Secret Key:  {config.secret_key[:15]}..." if config.secret_key else "Secret Key:  ❌ Not set")
    print(f"Project:     {config.project_name}")
    print(f"Environment: {config.environment}")
    print(f"Enabled:     {config.enabled}")
    print(f"Status:      {message}")
    print("=" * 50)
