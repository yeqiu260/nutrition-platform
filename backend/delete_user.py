"""删除用户脚本 - 简化版"""
import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def delete_user_by_email(email: str):
    async with async_session_maker() as db:
        try:
            # 查找用户
            result = await db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            )
            user = result.fetchone()
            
            if not user:
                print(f"User not found: {email}")
                return
            
            user_id = str(user[0])
            print(f"Found user: {user_id}")
            
            # 使用 CASCADE 删除或逐个处理外键
            # 首先获取所有引用 users 的表
            fk_query = """
            SELECT DISTINCT tc.table_name 
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu 
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND ccu.table_name = 'users'
            """
            fk_result = await db.execute(text(fk_query))
            tables = [row[0] for row in fk_result.fetchall()]
            print(f"Tables with foreign keys to users: {tables}")
            
            # 对每个有外键的表执行删除
            for table in tables:
                try:
                    await db.execute(text(f"DELETE FROM {table} WHERE user_id = :uid"), {"uid": user_id})
                    print(f"  Deleted from {table}")
                except Exception as e:
                    print(f"  Error in {table}: {e}")
            
            # 删除用户
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
            await db.commit()
            print(f"User {email} deleted!")
            
        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(delete_user_by_email("juechengj@gmail.com"))
