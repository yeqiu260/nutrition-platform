import asyncio
import sys
import os
from sqlalchemy import select

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.user import User

async def create_special_users():
    admin_email = "admin@wysik.com"
    partner_email = "partner@wysik.com"

    async with async_session_maker() as session:
        # Check and create admin
        result = await session.execute(select(User).where(User.email == admin_email))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                email=admin_email,
                account_type="admin",
                is_verified=True,
                is_active=True,
                full_name="System Admin"
            )
            session.add(admin_user)
            print(f"Created admin account: {admin_email}")
        else:
            admin_user.account_type = "admin"
            print(f"Admin account already exists: {admin_email}")

        # Check and create partner
        result = await session.execute(select(User).where(User.email == partner_email))
        partner_user = result.scalar_one_or_none()
        
        if not partner_user:
            partner_user = User(
                email=partner_email,
                account_type="partner",
                is_verified=True,
                is_active=True,
                full_name="Demo Partner"
            )
            session.add(partner_user)
            print(f"Created partner account: {partner_email}")
        else:
            partner_user.account_type = "partner"
            print(f"Partner account already exists: {partner_email}")

        await session.commit()
        print("Done. You can now log in using these accounts with OTP.")

if __name__ == "__main__":
    asyncio.run(create_special_users())
