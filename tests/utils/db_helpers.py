from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import (
    AdminUser,
    Category,
    Permission,
    Role,
    RolePermission,
    SubCategory,
)

from .factories import AsyncTestDataFactory


class AsyncDatabaseTestHelper:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_role(self, **kwargs: Any) -> Role:
        role = Role(**AsyncTestDataFactory.create_role_data(**kwargs))
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def create_permission(self, **kwargs: Any) -> Permission:
        permission = Permission(
            **AsyncTestDataFactory.create_permission_data(**kwargs)
        )
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        return permission

    async def create_role_permission(
        self, role_id: str, permission_id: str, **kwargs: Any
    ) -> RolePermission:
        rp = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
            rp_status=kwargs.get("rp_status", True),
        )
        self.session.add(rp)
        await self.session.commit()
        await self.session.refresh(rp)
        return rp

    async def create_admin_user(self, role_id: str, **kwargs: Any) -> AdminUser:
        user = AdminUser(
            **AsyncTestDataFactory.create_admin_user_data(
                role_id=role_id, **kwargs
            )
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def create_category(self, **kwargs: Any) -> Category:
        category = Category(
            **AsyncTestDataFactory.create_category_data(**kwargs)
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def create_subcategory(
        self, category_id: str, **kwargs: Any
    ) -> SubCategory:
        subcat = SubCategory(
            **AsyncTestDataFactory.create_subcategory_data(
                category_id=category_id, **kwargs
            )
        )
        self.session.add(subcat)
        await self.session.commit()
        await self.session.refresh(subcat)
        return subcat

    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        return (
            await self.session.execute(
                select(Role).where(Role.role_id == role_id)
            )
        ).scalar_one_or_none()

    async def cleanup_all_data(self) -> None:
        from shared.db.models.base import EventsBase

        for table in reversed(EventsBase.metadata.sorted_tables):
            await self.session.execute(table.delete())
        await self.session.commit()
