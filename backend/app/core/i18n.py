from typing import Dict, Any

TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "zh-TW": {
        "disclaimer": "【健康免責聲明】本測驗是根據你自填的生活與症狀資訊進行分析，結果僅供參考。任何健康建議都不能替代專業醫療意見。如有任何健康疑慮，請諮詢醫療專業人士。",
        "errors": {
            "invalid_otp": "驗證碼錯誤，請重試",
            "otp_expired": "驗證碼已過期，請重新發送",
            "rate_limit": "請求過於頻繁，請稍後再試",
            "invalid_email": "電子郵件格式不正確",
            "user_not_found": "找不到用戶",
            "unauthorized": "未授權訪問",
            "internal_error": "系統錯誤，請稍後再試"
        },
        "success": {
            "otp_sent": "驗證碼已發送到您的郵箱",
            "login_success": "登入成功",
            "quiz_submitted": "問卷已提交"
        },
        "email": {
            "otp_subject": "您的 WysikHealth 驗證碼",
            "otp_body": "您的驗證碼是：{code}，有效期10分鐘。",
            "welcome_subject": "歡迎來到 WysikHealth",
            "welcome_body": "感謝您註冊 WysikHealth..."
        }
    },
    "en": {
        "disclaimer": "[Health Disclaimer] This assessment is based on your self-reported lifestyle and symptom information and is for reference only. Any health advice cannot replace professional medical advice. If you have any health concerns, please consult a healthcare professional.",
        "errors": {
            "invalid_otp": "Invalid verification code, please try again",
            "otp_expired": "Verification code has expired, please request a new one",
            "rate_limit": "Too many requests, please try again later",
            "invalid_email": "Invalid email format",
            "user_not_found": "User not found",
            "unauthorized": "Unauthorized access",
            "internal_error": "System error, please try again later"
        },
        "success": {
            "otp_sent": "Verification code sent to your email",
            "login_success": "Login successful",
            "quiz_submitted": "Questionnaire submitted"
        },
        "email": {
            "otp_subject": "Your WysikHealth Verification Code",
            "otp_body": "Your verification code is: {code}, valid for 10 minutes.",
            "welcome_subject": "Welcome to WysikHealth",
            "welcome_body": "Thank you for registering with WysikHealth..."
        }
    }
}


def t(key: str, locale: str = "zh-TW", **kwargs) -> str:
    """
    Get translated text for the given key and locale.
    
    Args:
        key: Dot-notation key (e.g., "errors.invalid_otp")
        locale: Language code (zh-TW or en)
        **kwargs: Format parameters for string interpolation
    
    Returns:
        Translated text, or the key itself if not found
    """
    keys = key.split(".")
    value = TRANSLATIONS.get(locale, TRANSLATIONS["zh-TW"])
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k, key)
        else:
            return key
    
    # Handle string interpolation
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    return value if isinstance(value, str) else key


def get_locale_from_header(accept_language: str | None) -> str:
    """
    Extract locale from Accept-Language header.
    
    Args:
        accept_language: Accept-Language header value
    
    Returns:
        Locale code (zh-TW or en), defaults to zh-TW
    """
    if not accept_language:
        return "zh-TW"
    
    # Parse Accept-Language header (e.g., "en,zh-TW;q=0.9")
    languages = accept_language.split(",")
    for lang in languages:
        locale = lang.split(";")[0].strip()
        if locale in ["zh-TW", "en"]:
            return locale
    
    return "zh-TW"
