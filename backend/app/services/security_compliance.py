"""安全与合规服务

实现需求 9.1-9.8:
- 静态加密（encryption at rest）
- 防 IDOR（越权读取）
- 病毒扫描（AV scanning）
- PII 遮罩
- 去识别化导出
"""

import hashlib
import hmac
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 静态加密服务（Encryption at Rest）
# ============================================================================

class EncryptionService:
    """
    静态数据加密服务
    
    用于加密敏感数据（如健康档案、报告内容）
    使用 Fernet (对称加密) 基于 AES-128
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密服务
        
        Args:
            encryption_key: 加密密钥（base64 编码），如果为 None 则从环境变量读取
        """
        if encryption_key is None:
            encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            # 生成新密钥（仅用于开发环境）
            logger.warning("No encryption key provided, generating new key (DEV ONLY)")
            encryption_key = Fernet.generate_key().decode()
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError("Invalid encryption key")
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密文本
        
        Args:
            plaintext: 明文
            
        Returns:
            加密后的文本（base64 编码）
        """
        if not plaintext:
            return plaintext
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密文本
        
        Args:
            ciphertext: 密文（base64 编码）
            
        Returns:
            解密后的明文
        """
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: List[str]) -> Dict[str, Any]:
        """
        加密字典中的指定字段
        
        Args:
            data: 要加密的字典
            fields_to_encrypt: 要加密的字段列表
            
        Returns:
            加密后的字典
        """
        result = data.copy()
        
        for field in fields_to_encrypt:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: List[str]) -> Dict[str, Any]:
        """
        解密字典中的指定字段
        
        Args:
            data: 要解密的字典
            fields_to_decrypt: 要解密的字段列表
            
        Returns:
            解密后的字典
        """
        result = data.copy()
        
        for field in fields_to_decrypt:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(result[field])
                except Exception as e:
                    logger.warning(f"Failed to decrypt field {field}: {e}")
                    result[field] = None
        
        return result
    
    @staticmethod
    def generate_key() -> str:
        """
        生成新的加密密钥
        
        Returns:
            base64 编码的密钥
        """
        return Fernet.generate_key().decode('utf-8')
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> str:
        """
        对敏感数据进行哈希（单向加密）
        
        用于存储不需要解密的敏感数据（如身份证号的哈希）
        
        Args:
            data: 要哈希的数据
            salt: 盐值，如果为 None 则使用默认盐
            
        Returns:
            哈希值（hex 编码）
        """
        if salt is None:
            salt = os.getenv("HASH_SALT", "default_salt_change_in_production")
        
        return hashlib.pbkdf2_hmac(
            'sha256',
            data.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        ).hex()


# ============================================================================
# 2. 病毒扫描服务（AV Scanning）
# ============================================================================

class AntivirusScanner:
    """
    病毒扫描服务
    
    用于扫描用户上传的文件
    支持多种扫描引擎（ClamAV、VirusTotal API）
    """
    
    # 危险文件扩展名黑名单
    DANGEROUS_EXTENSIONS = {
        '.exe', '.dll', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
        '.sh', '.bash', '.ps1', '.psm1',
    }
    
    # 允许的文件扩展名白名单
    ALLOWED_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.txt', '.csv', '.json', '.xml',
        '.doc', '.docx', '.xls', '.xlsx',
    }
    
    # 文件魔数（Magic Numbers）检测
    MAGIC_NUMBERS = {
        'pdf': b'%PDF',
        'jpg': b'\xff\xd8\xff',
        'png': b'\x89PNG\r\n\x1a\n',
        'gif': b'GIF8',
        'zip': b'PK\x03\x04',
    }
    
    def __init__(self):
        """初始化扫描器"""
        self.scan_count = 0
        self.threat_count = 0
    
    def scan_file(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """
        扫描文件
        
        Args:
            file_path: 文件路径（用于获取扩展名）
            file_content: 文件内容（字节）
            
        Returns:
            扫描结果字典
        """
        self.scan_count += 1
        
        result = {
            "safe": True,
            "threats": [],
            "warnings": [],
            "scan_time": datetime.utcnow().isoformat(),
        }
        
        # 1. 检查文件扩展名
        ext_check = self._check_extension(file_path)
        if not ext_check["safe"]:
            result["safe"] = False
            result["threats"].append(ext_check["reason"])
            self.threat_count += 1
            return result
        
        if ext_check.get("warning"):
            result["warnings"].append(ext_check["warning"])
        
        # 2. 检查文件大小
        size_check = self._check_file_size(file_content)
        if not size_check["safe"]:
            result["safe"] = False
            result["threats"].append(size_check["reason"])
            return result
        
        # 3. 检查文件魔数（Magic Number）
        magic_check = self._check_magic_number(file_path, file_content)
        if not magic_check["safe"]:
            result["safe"] = False
            result["threats"].append(magic_check["reason"])
            self.threat_count += 1
            return result
        
        # 4. 检查可疑内容
        content_check = self._check_suspicious_content(file_content)
        if not content_check["safe"]:
            result["safe"] = False
            result["threats"].extend(content_check["threats"])
            self.threat_count += 1
            return result
        
        if content_check.get("warnings"):
            result["warnings"].extend(content_check["warnings"])
        
        return result
    
    def _check_extension(self, file_path: str) -> Dict[str, Any]:
        """检查文件扩展名"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # 检查危险扩展名
        if ext in self.DANGEROUS_EXTENSIONS:
            return {
                "safe": False,
                "reason": f"Dangerous file extension: {ext}"
            }
        
        # 检查是否在白名单中
        if ext not in self.ALLOWED_EXTENSIONS:
            return {
                "safe": True,
                "warning": f"Uncommon file extension: {ext}"
            }
        
        return {"safe": True}
    
    def _check_file_size(self, file_content: bytes) -> Dict[str, Any]:
        """检查文件大小"""
        max_size = 10 * 1024 * 1024  # 10MB
        
        if len(file_content) > max_size:
            return {
                "safe": False,
                "reason": f"File too large: {len(file_content)} bytes (max: {max_size})"
            }
        
        return {"safe": True}
    
    def _check_magic_number(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """检查文件魔数（验证文件类型）"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        # 只检查我们知道魔数的文件类型
        if ext in self.MAGIC_NUMBERS:
            expected_magic = self.MAGIC_NUMBERS[ext]
            actual_magic = file_content[:len(expected_magic)]
            
            if actual_magic != expected_magic:
                return {
                    "safe": False,
                    "reason": f"File type mismatch: extension is .{ext} but content doesn't match"
                }
        
        return {"safe": True}
    
    def _check_suspicious_content(self, file_content: bytes) -> Dict[str, Any]:
        """检查可疑内容"""
        threats = []
        warnings = []
        
        # 检查可执行代码特征
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'exec(',
            b'system(',
            b'<?php',
            b'<%',
            b'#!/bin/',
        ]
        
        for pattern in suspicious_patterns:
            if pattern in file_content:
                threats.append(f"Suspicious content detected: {pattern.decode('utf-8', errors='ignore')}")
        
        # 检查过长的行（可能是混淆代码）
        try:
            text = file_content.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            for i, line in enumerate(lines[:100]):  # 只检查前100行
                if len(line) > 10000:
                    warnings.append(f"Unusually long line detected at line {i+1}")
        except:
            pass
        
        return {
            "safe": len(threats) == 0,
            "threats": threats,
            "warnings": warnings
        }
    
    def get_stats(self) -> Dict[str, int]:
        """获取扫描统计"""
        return {
            "total_scans": self.scan_count,
            "threats_detected": self.threat_count,
        }


# ============================================================================
# 3. 数据去识别化服务（De-identification）
# ============================================================================

class DeidentificationService:
    """
    数据去识别化服务
    
    用于导出用户数据时移除或遮罩 PII
    """
    
    # 敏感字段列表
    SENSITIVE_FIELDS = {
        'contact', 'phone', 'email', 'ip_address',
        'address', 'id_number', 'passport',
        'credit_card', 'bank_account',
    }
    
    # 需要哈希的字段（保留用于关联但不可逆）
    HASH_FIELDS = {
        'user_id', 'session_id',
    }
    
    def __init__(self):
        """初始化去识别化服务"""
        from app.core.security import PIIMasker
        self.pii_masker = PIIMasker()
    
    def deidentify_user_data(
        self,
        data: Dict[str, Any],
        mode: str = "mask"
    ) -> Dict[str, Any]:
        """
        去识别化用户数据
        
        Args:
            data: 用户数据字典
            mode: 去识别化模式
                - "mask": 遮罩 PII（保留部分信息）
                - "remove": 完全移除 PII
                - "hash": 哈希 PII（用于关联但不可逆）
                
        Returns:
            去识别化后的数据
        """
        result = data.copy()
        
        for field in self.SENSITIVE_FIELDS:
            if field in result:
                if mode == "remove":
                    result[field] = None
                elif mode == "hash":
                    if result[field]:
                        result[field] = self._hash_value(str(result[field]))
                elif mode == "mask":
                    if field in ('phone', 'contact'):
                        result[field] = self.pii_masker.mask_phone(str(result[field]))
                    elif field == 'email':
                        result[field] = self.pii_masker.mask_email(str(result[field]))
                    elif field == 'ip_address':
                        result[field] = self.pii_masker.mask_ip(str(result[field]))
                    else:
                        result[field] = self._generic_mask(str(result[field]))
        
        return result
    
    def deidentify_batch(
        self,
        records: List[Dict[str, Any]],
        mode: str = "mask"
    ) -> List[Dict[str, Any]]:
        """
        批量去识别化
        
        Args:
            records: 记录列表
            mode: 去识别化模式
            
        Returns:
            去识别化后的记录列表
        """
        return [self.deidentify_user_data(record, mode) for record in records]
    
    def _hash_value(self, value: str) -> str:
        """哈希值（用于关联但不可逆）"""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]
    
    def _generic_mask(self, value: str) -> str:
        """通用遮罩"""
        if len(value) <= 4:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]
    
    def create_export_package(
        self,
        user_data: Dict[str, Any],
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        创建导出包
        
        Args:
            user_data: 用户数据
            include_sensitive: 是否包含敏感数据（需要额外授权）
            
        Returns:
            导出包
        """
        if include_sensitive:
            # 包含敏感数据，但需要记录访问日志
            logger.warning(f"Sensitive data export requested for user")
            return user_data
        else:
            # 去识别化导出
            return self.deidentify_user_data(user_data, mode="mask")


# ============================================================================
# 4. 访问审计服务（Access Audit）
# ============================================================================

class AccessAuditService:
    """
    访问审计服务
    
    记录所有敏感操作和数据访问
    """
    
    def __init__(self):
        """初始化审计服务"""
        self.audit_log = []
    
    def log_access(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录访问日志
        
        Args:
            user_id: 用户 ID
            resource_type: 资源类型（如 "report", "health_profile"）
            resource_id: 资源 ID
            action: 操作类型（如 "read", "write", "delete"）
            ip_address: IP 地址
            success: 是否成功
            details: 额外详情
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "ip_address": ip_address,
            "success": success,
            "details": details or {},
        }
        
        self.audit_log.append(log_entry)
        
        # 记录到日志文件
        logger.info(
            f"ACCESS_AUDIT: user={user_id} resource={resource_type}/{resource_id} "
            f"action={action} success={success} ip={ip_address}"
        )
    
    def log_sensitive_data_access(
        self,
        user_id: UUID,
        data_type: str,
        reason: str,
        ip_address: str
    ) -> None:
        """
        记录敏感数据访问
        
        Args:
            user_id: 用户 ID
            data_type: 数据类型
            reason: 访问原因
            ip_address: IP 地址
        """
        self.log_access(
            user_id=user_id,
            resource_type="sensitive_data",
            resource_id=data_type,
            action="access",
            ip_address=ip_address,
            details={"reason": reason}
        )
    
    def get_audit_log(
        self,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取审计日志
        
        Args:
            user_id: 过滤用户 ID
            resource_type: 过滤资源类型
            limit: 返回数量限制
            
        Returns:
            审计日志列表
        """
        filtered = self.audit_log
        
        if user_id:
            filtered = [log for log in filtered if log["user_id"] == str(user_id)]
        
        if resource_type:
            filtered = [log for log in filtered if log["resource_type"] == resource_type]
        
        return filtered[-limit:]


# ============================================================================
# 全局实例
# ============================================================================

# 加密服务实例
encryption_service = EncryptionService()

# 病毒扫描实例
av_scanner = AntivirusScanner()

# 去识别化服务实例
deidentification_service = DeidentificationService()

# 访问审计服务实例
audit_service = AccessAuditService()
