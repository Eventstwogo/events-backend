from typing import Any, Dict

from faker import Faker

fake = Faker()


class AsyncTestDataFactory:
    @staticmethod
    def create_role_data(**kwargs: Any) -> Dict[str, Any]:
        return {
            "role_id": fake.unique.lexify(text="ROL???"),
            "role_name": fake.job(),
            "role_status": fake.boolean(),
            **kwargs,
        }

    @staticmethod
    def create_permission_data(**kwargs: Any) -> Dict[str, Any]:
        return {
            "permission_id": fake.unique.lexify(text="PRM???"),
            "permission_name": fake.sentence(nb_words=3),
            "permission_status": fake.boolean(),
            **kwargs,
        }

    @staticmethod
    def create_admin_user_data(**kwargs: Any) -> Dict[str, Any]:
        return {
            "user_id": fake.unique.lexify(text="USR???"),
            "username": fake.user_name(),
            "email": fake.email(),
            "password_hash": fake.sha256(),
            "is_active": fake.boolean(),
            **kwargs,
        }

    @staticmethod
    def create_category_data(**kwargs: Any) -> Dict[str, Any]:
        name = fake.word().title()
        return {
            "category_id": fake.unique.lexify(text="CAT???"),
            "category_name": name,
            "category_description": fake.text(max_nb_chars=200),
            "category_slug": name.lower().replace(" ", "-"),
            "category_meta_title": f"{name} - Events",
            "category_meta_description": fake.text(max_nb_chars=160),
            "featured_category": fake.boolean(),
            "show_in_menu": fake.boolean(),
            "category_status": fake.boolean(),
            **kwargs,
        }

    @staticmethod
    def create_subcategory_data(**kwargs: Any) -> Dict[str, Any]:
        name = fake.word().title()
        return {
            "subcategory_id": fake.unique.lexify(text="SUB???"),
            "subcategory_name": name,
            "subcategory_description": fake.text(max_nb_chars=200),
            "subcategory_slug": name.lower().replace(" ", "-"),
            "subcategory_meta_title": f"{name} - Events",
            "subcategory_meta_description": fake.text(max_nb_chars=160),
            "featured_subcategory": fake.boolean(),
            "show_in_menu": fake.boolean(),
            "subcategory_status": fake.boolean(),
            **kwargs,
        }
