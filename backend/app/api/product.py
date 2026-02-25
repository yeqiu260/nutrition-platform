"""商品管理 API"""

import os
import uuid as uuid_module
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.product import Product
from app.models.admin import AdminUser, UserRole
from app.api.admin import get_current_admin, require_role
from app.services.security_compliance import av_scanner

router = APIRouter(prefix="/api/products", tags=["products"])

# 图片上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "products")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================================
# 请求/响应模型
# ============================================================================

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    currency: str = "TWD"
    supplement_id: str = Field(..., description="关联的补充品ID")
    purchase_url: str = Field(..., description="购买链接")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    supplement_id: Optional[str] = None
    purchase_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    image_url: Optional[str]
    price: Optional[float]
    currency: str
    supplement_id: str
    purchase_url: str
    partner_id: UUID
    partner_name: Optional[str]
    is_active: bool
    is_approved: bool
    created_at: datetime


class ProductPublicResponse(BaseModel):
    """公开的商品信息（用于推荐展示）"""
    id: UUID
    name: str
    description: Optional[str]
    image_url: Optional[str]
    price: Optional[float]
    currency: str
    purchase_url: str
    partner_name: Optional[str]


# ============================================================================
# 合作商 API - 管理自己的商品
# ============================================================================

@router.post("/my", response_model=ProductResponse)
async def create_product(
    request: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """合作商创建商品"""
    product = Product(
        name=request.name,
        description=request.description,
        image_url=request.image_url,
        price=request.price,
        currency=request.currency,
        supplement_id=request.supplement_id,
        purchase_url=request.purchase_url,
        partner_id=admin.id,
        partner_name=admin.username,
        is_approved=admin.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN],  # 管理员自动审核通过
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        price=product.price,
        currency=product.currency,
        supplement_id=product.supplement_id,
        purchase_url=product.purchase_url,
        partner_id=product.partner_id,
        partner_name=product.partner_name,
        is_active=product.is_active,
        is_approved=product.is_approved,
        created_at=product.created_at,
    )


@router.get("/my", response_model=List[ProductResponse])
async def list_my_products(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """获取自己的商品列表"""
    result = await db.execute(
        select(Product)
        .where(Product.partner_id == admin.id)
        .order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    
    return [ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        image_url=p.image_url,
        price=p.price,
        currency=p.currency,
        supplement_id=p.supplement_id,
        purchase_url=p.purchase_url,
        partner_id=p.partner_id,
        partner_name=p.partner_name,
        is_active=p.is_active,
        is_approved=p.is_approved,
        created_at=p.created_at,
    ) for p in products]


@router.put("/my/{product_id}", response_model=ProductResponse)
async def update_my_product(
    product_id: UUID,
    request: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """更新自己的商品"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.partner_id == admin.id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在或無權限")
    
    if request.name is not None:
        product.name = request.name
    if request.description is not None:
        product.description = request.description
    if request.image_url is not None:
        product.image_url = request.image_url
    if request.price is not None:
        product.price = request.price
    if request.currency is not None:
        product.currency = request.currency
    if request.supplement_id is not None:
        product.supplement_id = request.supplement_id
    if request.purchase_url is not None:
        product.purchase_url = request.purchase_url
    if request.is_active is not None:
        product.is_active = request.is_active
    
    # 合作商修改后需要重新审核
    if admin.role == UserRole.PARTNER:
        product.is_approved = False
    
    await db.commit()
    await db.refresh(product)
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        price=product.price,
        currency=product.currency,
        supplement_id=product.supplement_id,
        purchase_url=product.purchase_url,
        partner_id=product.partner_id,
        partner_name=product.partner_name,
        is_active=product.is_active,
        is_approved=product.is_approved,
        created_at=product.created_at,
    )


@router.delete("/my/{product_id}")
async def delete_my_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """删除自己的商品"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.partner_id == admin.id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在或無權限")
    
    await db.delete(product)
    await db.commit()
    return {"message": "商品已刪除"}


# ============================================================================
# 管理员 API - 审核商品
# ============================================================================

@router.get("/pending", response_model=List[ProductResponse])
async def list_pending_products(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """获取待审核商品列表"""
    result = await db.execute(
        select(Product)
        .where(Product.is_approved == False)
        .order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    
    return [ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        image_url=p.image_url,
        price=p.price,
        currency=p.currency,
        supplement_id=p.supplement_id,
        purchase_url=p.purchase_url,
        partner_id=p.partner_id,
        partner_name=p.partner_name,
        is_active=p.is_active,
        is_approved=p.is_approved,
        created_at=p.created_at,
    ) for p in products]


@router.post("/approve/{product_id}")
async def approve_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """审核通过商品"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    product.is_approved = True
    await db.commit()
    return {"message": "商品已審核通過"}


@router.post("/reject/{product_id}")
async def reject_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """拒绝商品"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    await db.delete(product)
    await db.commit()
    return {"message": "商品已拒絕並刪除"}


# ============================================================================
# 公开 API - 获取商品用于推荐展示
# ============================================================================

@router.get("/by-supplement/{supplement_id}", response_model=List[ProductPublicResponse])
async def get_products_by_supplement(
    supplement_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据补充品ID获取已审核的商品列表（公开接口）"""
    result = await db.execute(
        select(Product)
        .where(
            Product.supplement_id == supplement_id,
            Product.is_active == True,
            Product.is_approved == True
        )
        .order_by(Product.sort_order.desc(), Product.created_at.desc())
        .limit(5)
    )
    products = result.scalars().all()
    
    return [ProductPublicResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        image_url=p.image_url,
        price=p.price,
        currency=p.currency,
        purchase_url=p.purchase_url,
        partner_name=p.partner_name,
    ) for p in products]


# ============================================================================
# 图片上传 API
# ============================================================================

@router.post("/upload-image")
async def upload_product_image(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """上传商品图片"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、WebP、GIF 格式")
    
    # 验证文件大小 (最大 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="圖片大小不能超過 5MB")
    
    # 【安全合规】病毒扫描
    scan_result = av_scanner.scan_file(file.filename, content)
    if not scan_result["safe"]:
        raise HTTPException(
            status_code=400,
            detail=f"圖片被拒絕：{', '.join(scan_result['threats'])}"
        )
    
    # 生成唯一文件名
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid_module.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # 保存文件
    with open(filepath, "wb") as f:
        f.write(content)
    
    # 返回图片URL
    image_url = f"/api/products/images/{filename}"
    return {"url": image_url, "filename": filename}


@router.get("/images/{filename}")
async def get_product_image(filename: str):
    """获取商品图片"""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="圖片不存在")
    
    return FileResponse(filepath)
