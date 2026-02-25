"""邮件发送服务"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """邮件发送服务"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email or settings.smtp_username
        self.from_name = settings.smtp_from_name
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured, email not sent")
            return False
        
        # 在线程池中运行同步代码，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._send_email_sync,
            to_email,
            subject,
            html_content,
            text_content
        )
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        同步发送邮件（在线程池中运行）- 带重试机制
        """
        import time
        
        max_retries = 3
        retry_delay = 2  # 初始延迟秒数
        
        for attempt in range(max_retries):
            try:
                # 创建邮件
                message = MIMEMultipart('alternative')
                message['From'] = f"{self.from_name} <{self.from_email}>"
                message['To'] = to_email
                message['Subject'] = subject
                
                # 添加纯文本版本
                if text_content:
                    text_part = MIMEText(text_content, 'plain', 'utf-8')
                    message.attach(text_part)
                
                # 添加 HTML 版本
                html_part = MIMEText(html_content, 'html', 'utf-8')
                message.attach(html_part)
                
                # 诊断日志
                if attempt == 0:
                    logger.info(f"=== SMTP Configuration ===")
                    logger.info(f"Host: {self.smtp_host}")
                    logger.info(f"Port: {self.smtp_port}")
                    logger.info(f"Username: {self.smtp_username}")
                    logger.info(f"==========================")
                else:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                
                # 使用同步 smtplib 发送
                server = None
                try:
                    # 587 端口使用 STARTTLS
                    if self.smtp_port == 587:
                        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                    # 465 端口使用 SSL
                    elif self.smtp_port == 465:
                        server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
                    else:
                        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                    
                    # 登录并发送
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
                    
                    logger.info(f"Email sent successfully to {to_email}")
                    return True
                    
                finally:
                    if server:
                        try:
                            server.quit()
                        except Exception:
                            pass  # 忽略关闭连接时的错误
                
            except smtplib.SMTPServerDisconnected as e:
                logger.warning(f"SMTP connection closed unexpectedly (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # 指数退避: 2, 4, 8 秒
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("All retry attempts failed for SMTP connection")
                    return False
                    
            except smtplib.SMTPException as e:
                logger.warning(f"SMTP error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning("Email sending failed after all retries. Please check the console for the OTP code.")
                    return False
                
            except (OSError, TimeoutError) as e:
                logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning("Email sending failed due to network issues after all retries.")
                    return False
                
            except Exception as e:
                logger.error(f"Unexpected error sending email to {to_email}: {e}")
                if settings.debug:
                    import traceback
                    traceback.print_exc()
                return False
        
        return False
    
    async def send_otp_email(
        self,
        to_email: str,
        otp_code: str,
        purpose: str = "login"
    ) -> bool:
        """
        发送 OTP 验证码邮件
        
        Args:
            to_email: 收件人邮箱
            otp_code: 验证码
            purpose: 用途（login, register, verify）
        
        Returns:
            True if sent successfully
        """
        purpose_text = {
            "login": "登入",
            "register": "註冊",
            "verify": "驗證"
        }.get(purpose, "驗證")
        
        subject = f"您的 {purpose_text} 驗證碼 - WysikHealth"
        
        # HTML 内容
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>驗證碼</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f7;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f7; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); padding: 40px 40px 30px; text-align: center;">
                            <div style="width: 60px; height: 60px; background-color: #ffffff; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: #1f2937; margin-bottom: 16px;">
                                W
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: bold;">WysikHealth</h1>
                            <p style="margin: 8px 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px;">智能營養建議平台</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 16px; color: #1f2937; font-size: 24px; font-weight: bold;">您的驗證碼</h2>
                            <p style="margin: 0 0 24px; color: #6b7280; font-size: 16px; line-height: 1.6;">
                                您正在進行 <strong>{purpose_text}</strong> 操作，請使用以下驗證碼完成驗證：
                            </p>
                            
                            <!-- OTP Code -->
                            <div style="background-color: #f9fafb; border: 2px dashed #e5e7eb; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
                                <div style="font-size: 48px; font-weight: bold; color: #1f2937; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                    {otp_code}
                                </div>
                            </div>
                            
                            <div style="background-color: #fef3c7; border-left: 4px solid #fbbf24; padding: 16px; border-radius: 8px; margin: 24px 0;">
                                <p style="margin: 0; color: #92400e; font-size: 14px; line-height: 1.6;">
                                    <strong>⏰ 重要提示：</strong><br>
                                    • 驗證碼有效期為 <strong>10 分鐘</strong><br>
                                    • 請勿將驗證碼分享給任何人<br>
                                    • 如非本人操作，請忽略此郵件
                                </p>
                            </div>
                            
                            <p style="margin: 24px 0 0; color: #9ca3af; font-size: 14px; line-height: 1.6;">
                                如果您沒有請求此驗證碼，請忽略此郵件。您的帳戶安全不會受到影響。
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 24px 40px; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 8px; color: #6b7280; font-size: 12px; text-align: center;">
                                此郵件由系統自動發送，請勿直接回覆
                            </p>
                            <p style="margin: 0; color: #9ca3af; font-size: 12px; text-align: center;">
                                © 2024 WysikHealth Inc. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        # 纯文本版本
        text_content = f"""
WysikHealth - 您的驗證碼

您正在進行 {purpose_text} 操作。

您的驗證碼是：{otp_code}

此驗證碼有效期為 10 分鐘，請勿分享給任何人。

如果您沒有請求此驗證碼，請忽略此郵件。

---
WysikHealth 智能營養建議平台
此郵件由系統自動發送，請勿直接回覆
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        发送欢迎邮件
        
        Args:
            to_email: 收件人邮箱
            user_name: 用户名（可选）
        
        Returns:
            True if sent successfully
        """
        greeting = f"您好 {user_name}" if user_name else "您好"
        
        subject = "歡迎加入 WysikHealth！"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>歡迎加入</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f7;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f7; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <tr>
                        <td style="padding: 40px; text-align: center;">
                            <div style="width: 80px; height: 80px; background-color: #fbbf24; border-radius: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: 40px; font-weight: bold; color: #1f2937; margin-bottom: 24px;">
                                W
                            </div>
                            <h1 style="margin: 0 0 16px; color: #1f2937; font-size: 32px; font-weight: bold;">歡迎加入 WysikHealth！</h1>
                            <p style="margin: 0 0 32px; color: #6b7280; font-size: 18px;">
                                {greeting}，感謝您註冊我們的智能營養建議平台
                            </p>
                            
                            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 32px; margin: 32px 0; text-align: left;">
                                <h2 style="margin: 0 0 16px; color: #92400e; font-size: 20px; font-weight: bold;">🎉 您可以開始：</h2>
                                <ul style="margin: 0; padding-left: 20px; color: #92400e; font-size: 16px; line-height: 1.8;">
                                    <li>完成 5 分鐘問卷，獲得個性化營養建議</li>
                                    <li>上傳體檢報告，讓 AI 為您深度分析</li>
                                    <li>查看推薦商品，輕鬆購買所需營養品</li>
                                    <li>追蹤您的健康歷程</li>
                                </ul>
                            </div>
                            
                            <a href="http://localhost:3100" style="display: inline-block; background-color: #1f2937; color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 9999px; font-size: 16px; font-weight: bold; margin: 16px 0;">
                                立即開始測評
                            </a>
                            
                            <p style="margin: 32px 0 0; color: #9ca3af; font-size: 14px;">
                                如有任何問題，歡迎隨時聯繫我們的客服團隊
                            </p>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="background-color: #f9fafb; padding: 24px; border-top: 1px solid #e5e7eb; text-align: center;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                © 2024 WysikHealth Inc. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        text_content = f"""
歡迎加入 WysikHealth！

{greeting}，感謝您註冊我們的智能營養建議平台。

您可以開始：
• 完成 5 分鐘問卷，獲得個性化營養建議
• 上傳體檢報告，讓 AI 為您深度分析
• 查看推薦商品，輕鬆購買所需營養品
• 追蹤您的健康歷程

立即訪問：http://localhost:3100

如有任何問題，歡迎隨時聯繫我們。

---
WysikHealth 智能營養建議平台
© 2024 WysikHealth Inc.
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# 全局实例
email_service = EmailService()
