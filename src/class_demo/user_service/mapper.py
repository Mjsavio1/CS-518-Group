from typing import Dict, Any
from .models import User


def dict_to_model(data: Dict[str, Any]) -> User:
    """Validate input dict and return a `User` model."""
    return User(**data)


def model_to_dict(user: User) -> Dict[str, Any]:
    """Convert a `User` model to a plain dict for controller use."""
    return user.dict(exclude_none=True)


def model_to_db(user: User) -> Dict[str, Any]:
    """Convert a `User` model to a pymongo-style document.

    Maps `id` -> `_id` for database storage.
    """
    doc = user.dict(exclude_none=True)
    if "id" in doc:
        doc["_id"] = doc.pop("id")
    return doc


def db_to_model(doc: Dict[str, Any]) -> User:
    """Convert a pymongo document to a `User` model.

    Maps `_id` -> `id` for the model.
    Converts ObjectId to string.
    """
    from bson.objectid import ObjectId
    
    d = dict(doc)
    if "_id" in d:
        obj_id = d.pop("_id")
        # Convert ObjectId to string if necessary
        d["id"] = str(obj_id) if isinstance(obj_id, ObjectId) else obj_id
    return User(**d)
