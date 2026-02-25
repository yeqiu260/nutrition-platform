"""管理员 API 路由"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import jwt
from app.core.config import get_settings

settings = get_settings()
from app.core.database import get_db, async_session_maker
from app.models.admin import AdminUser, SystemConfig, UserRole, Supplement, QuizQuestion
from app.middleware.endpoint_limit import rate_limit

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer()

# JWT 配置
JWT_SECRET = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRATION_HOURS = 24


# ============================================================================
# 请求/响应模型
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    username: str
    expires_at: datetime


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.ADMIN


class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UpdateRoleRequest(BaseModel):
    user_id: UUID
    new_role: UserRole


class SystemConfigUpdate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class SystemConfigResponse(BaseModel):
    key: str
    value: str
    description: Optional[str]
    updated_at: datetime


class SupplementCreate(BaseModel):
    supplement_id: str
    name: str
    group: str
    screening_threshold: int = 2
    sort_order: int = 0


class SupplementUpdate(BaseModel):
    name: Optional[str] = None
    group: Optional[str] = None
    screening_threshold: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SupplementResponse(BaseModel):
    id: UUID
    supplement_id: str
    name: str
    group: str
    screening_threshold: int
    sort_order: int
    is_active: bool


class QuestionCreate(BaseModel):
    supplement_id: str
    phase: str  # screening 或 detail
    subtitle: str
    question_text: str
    options: List[dict]  # [{label: "", score: 0}, ...]
    sort_order: int = 0


class QuestionUpdate(BaseModel):
    subtitle: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[dict]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    id: UUID
    supplement_id: str
    phase: str
    subtitle: str
    question_text: str
    options: List[dict]
    sort_order: int
    is_active: bool


# ============================================================================
# 工具函数
# ============================================================================

def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def create_token(user_id: str, username: str, role: str) -> tuple[str, datetime]:
    """创建 JWT token"""
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expires_at
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """验证并获取当前管理员"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        result = await db.execute(
            select(AdminUser).where(AdminUser.id == user_id, AdminUser.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles: UserRole):
    """角色权限装饰器"""
    async def role_checker(admin: AdminUser = Depends(get_current_admin)):
        if admin.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin
    return role_checker


# ============================================================================
# 认证 API
# ============================================================================

@router.post("/login", response_model=LoginResponse)
@rate_limit(max_requests=10, window=60)  # 每分钟最多 10 次登录尝试
async def admin_login(request: Request, login_request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """管理员登录"""
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.username == login_request.username,
            AdminUser.is_active == True
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token, expires_at = create_token(str(user.id), user.username, user.role.value)
    
    return LoginResponse(
        token=token,
        role=user.role.value,
        username=user.username,
        expires_at=expires_at
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_user(admin: AdminUser = Depends(get_current_admin)):
    """获取当前登录用户信息"""
    return AdminUserResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
        created_at=admin.created_at
    )


# ============================================================================
# 用户管理 API (仅超级管理员)
# ============================================================================

@router.post("/users", response_model=AdminUserResponse)
async def create_admin_user(
    request: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """创建管理员用户 (仅超级管理员)"""
    # 检查用户名是否已存在
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user = AdminUser(
        username=request.username,
        password_hash=hash_password(request.password),
        role=request.role,
        created_by=admin.id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """获取所有管理员用户"""
    result = await db.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))
    users = result.scalars().all()
    return [
        AdminUserResponse(
            id=u.id,
            username=u.username,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at
        ) for u in users
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """更新用户角色 (仅超级管理员)"""
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.role = request.new_role
    await db.commit()
    return {"message": "角色更新成功"}


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """删除管理员用户 (仅超级管理员)"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    await db.execute(delete(AdminUser).where(AdminUser.id == user_id))
    await db.commit()
    return {"message": "用户删除成功"}


# ============================================================================
# 系统配置 API (API Key 等)
# ============================================================================

@router.get("/config", response_model=List[SystemConfigResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """获取所有系统配置"""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return [
        SystemConfigResponse(
            key=c.key,
            value="***" if c.is_encrypted else c.value,  # 加密的值不显示
            description=c.description,
            updated_at=c.updated_at
        ) for c in configs
    ]


@router.put("/config")
async def update_config(
    request: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """更新系统配置 (仅超级管理员)"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == request.key))
    config = result.scalar_one_or_none()
    
    if config:
        config.value = request.value
        config.description = request.description
        config.updated_by = admin.id
    else:
        config = SystemConfig(
            key=request.key,
            value=request.value,
            description=request.description,
            is_encrypted=request.key.lower().endswith("_key"),  # API Key 自动标记为加密
            updated_by=admin.id
        )
        db.add(config)
    
    await db.commit()
    return {"message": f"配置 {request.key} 更新成功"}


@router.get("/config/{key}")
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """获取单个配置 (仅超级管理员可查看完整值)"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    return SystemConfigResponse(
        key=config.key,
        value=config.value,
        description=config.description,
        updated_at=config.updated_at
    )


@router.delete("/config/{key}")
async def delete_config(
    key: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """删除系统配置 (仅超级管理员)"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    await db.execute(delete(SystemConfig).where(SystemConfig.key == key))
    await db.commit()
    return {"message": f"配置 {key} 已删除"}



# ============================================================================
# 补充品管理 API
# ============================================================================

@router.get("/supplements", response_model=List[SupplementResponse])
async def list_supplements(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """获取所有补充品"""
    result = await db.execute(
        select(Supplement).order_by(Supplement.sort_order, Supplement.supplement_id)
    )
    supplements = result.scalars().all()
    return [
        SupplementResponse(
            id=s.id,
            supplement_id=s.supplement_id,
            name=s.name,
            group=s.group,
            screening_threshold=s.screening_threshold,
            sort_order=s.sort_order,
            is_active=s.is_active
        ) for s in supplements
    ]


@router.post("/supplements", response_model=SupplementResponse)
async def create_supplement(
    request: SupplementCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """创建补充品"""
    # 检查 ID 是否已存在
    result = await db.execute(
        select(Supplement).where(Supplement.supplement_id == request.supplement_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="补充品 ID 已存在")
    
    supplement = Supplement(
        supplement_id=request.supplement_id,
        name=request.name,
        group=request.group,
        screening_threshold=request.screening_threshold,
        sort_order=request.sort_order
    )
    db.add(supplement)
    await db.commit()
    await db.refresh(supplement)
    
    return SupplementResponse(
        id=supplement.id,
        supplement_id=supplement.supplement_id,
        name=supplement.name,
        group=supplement.group,
        screening_threshold=supplement.screening_threshold,
        sort_order=supplement.sort_order,
        is_active=supplement.is_active
    )


@router.put("/supplements/{supplement_id}", response_model=SupplementResponse)
async def update_supplement(
    supplement_id: str,
    request: SupplementUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """更新补充品"""
    result = await db.execute(
        select(Supplement).where(Supplement.supplement_id == supplement_id)
    )
    supplement = result.scalar_one_or_none()
    if not supplement:
        raise HTTPException(status_code=404, detail="补充品不存在")
    
    if request.name is not None:
        supplement.name = request.name
    if request.group is not None:
        supplement.group = request.group
    if request.screening_threshold is not None:
        supplement.screening_threshold = request.screening_threshold
    if request.sort_order is not None:
        supplement.sort_order = request.sort_order
    if request.is_active is not None:
        supplement.is_active = request.is_active
    
    await db.commit()
    await db.refresh(supplement)
    
    return SupplementResponse(
        id=supplement.id,
        supplement_id=supplement.supplement_id,
        name=supplement.name,
        group=supplement.group,
        screening_threshold=supplement.screening_threshold,
        sort_order=supplement.sort_order,
        is_active=supplement.is_active
    )


@router.delete("/supplements/{supplement_id}")
async def delete_supplement(
    supplement_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN))
):
    """删除补充品 (仅超级管理员)"""
    await db.execute(delete(Supplement).where(Supplement.supplement_id == supplement_id))
    await db.execute(delete(QuizQuestion).where(QuizQuestion.supplement_id == supplement_id))
    await db.commit()
    return {"message": "补充品及相关问题已删除"}


# ============================================================================
# 问题管理 API
# ============================================================================

@router.get("/questions", response_model=List[QuestionResponse])
async def list_questions(
    supplement_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """获取问题列表"""
    query = select(QuizQuestion).order_by(QuizQuestion.supplement_id, QuizQuestion.phase, QuizQuestion.sort_order)
    if supplement_id:
        query = query.where(QuizQuestion.supplement_id == supplement_id)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    return [
        QuestionResponse(
            id=q.id,
            supplement_id=q.supplement_id,
            phase=q.phase,
            subtitle=q.subtitle,
            question_text=q.question_text,
            options=q.options,
            sort_order=q.sort_order,
            is_active=q.is_active
        ) for q in questions
    ]


@router.post("/questions", response_model=QuestionResponse)
async def create_question(
    request: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """创建问题"""
    question = QuizQuestion(
        supplement_id=request.supplement_id,
        phase=request.phase,
        subtitle=request.subtitle,
        question_text=request.question_text,
        options=request.options,
        sort_order=request.sort_order
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return QuestionResponse(
        id=question.id,
        supplement_id=question.supplement_id,
        phase=question.phase,
        subtitle=question.subtitle,
        question_text=question.question_text,
        options=question.options,
        sort_order=question.sort_order,
        is_active=question.is_active
    )


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    request: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """更新问题"""
    result = await db.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="问题不存在")
    
    if request.subtitle is not None:
        question.subtitle = request.subtitle
    if request.question_text is not None:
        question.question_text = request.question_text
    if request.options is not None:
        question.options = request.options
    if request.sort_order is not None:
        question.sort_order = request.sort_order
    if request.is_active is not None:
        question.is_active = request.is_active
    
    await db.commit()
    await db.refresh(question)
    
    return QuestionResponse(
        id=question.id,
        supplement_id=question.supplement_id,
        phase=question.phase,
        subtitle=question.subtitle,
        question_text=question.question_text,
        options=question.options,
        sort_order=question.sort_order,
        is_active=question.is_active
    )


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """删除问题"""
    await db.execute(delete(QuizQuestion).where(QuizQuestion.id == question_id))
    await db.commit()
    return {"message": "问题已删除"}


# ============================================================================
# 初始化超级管理员 (首次部署使用)
# ============================================================================

@router.post("/init-super-admin")
async def init_super_admin(
    request: AdminUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """初始化超级管理员 (仅当没有任何管理员时可用)"""
    result = await db.execute(select(AdminUser))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已存在管理员，无法初始化")
    
    user = AdminUser(
        username=request.username,
        password_hash=hash_password(request.password),
        role=UserRole.SUPER_ADMIN
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {"message": f"超级管理员 {user.username} 创建成功"}
