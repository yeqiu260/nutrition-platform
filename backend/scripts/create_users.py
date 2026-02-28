import asyncio
import sys
import os
from sqlalchemy import select

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.user import User
from app.api.auth import hash_password

async def create_special_users():
    admin_email = "admin@wysik.com"
    admin_username = "admin"  # The frontend might just pass email or username
    partner_email = "partner@wysik.com"
    default_password = "Password123!"

    async with async_session_maker() as session:
        # Check and create admin
        result = await session.execute(select(User).where(User.email == admin_email))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                email=admin_email,
                password_hash=hash_password(default_password),
                account_type="admin",
                is_verified=True,
                is_active=True,
                full_name="System Admin"
            )
            session.add(admin_user)
            print(f"Created admin account: {admin_email} | Password: {default_password}")
        else:
            admin_user.account_type = "admin"
            admin_user.password_hash = hash_password(default_password)
            print(f"Admin account updated: {admin_email} | Password reset to: {default_password}")

        # Check and create partner
        result = await session.execute(select(User).where(User.email == partner_email))
        partner_user = result.scalar_one_or_none()
        
        if not partner_user:
            partner_user = User(
                email=partner_email,
                password_hash=hash_password(default_password),
                account_type="partner",
                is_verified=True,
                is_active=True,
                full_name="Demo Partner"
            )
            session.add(partner_user)
            print(f"Created partner account: {partner_email} | Password: {default_password}")
        else:
            partner_user.account_type = "partner"
            partner_user.password_hash = hash_password(default_password)
            print(f"Partner account updated: {partner_email} | Password reset to: {default_password}")

        await session.commit()
        print("Done. You can now log in using these accounts with the default password.")

if __name__ == "__main__":
    asyncio.run(create_special_users())
