"""All MongoDB reads and writes for candidates. Nothing else touches the database."""

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.collection import Collection


def _to_object_id(candidate_id: str) -> ObjectId | None:
    try:
        return ObjectId(candidate_id)
    except (InvalidId, TypeError):
        return None


class CandidateRepository:
    def __init__(self, collection: Collection):
        self.collection = collection

    def insert(self, doc: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(doc)
        return {**doc, "_id": result.inserted_id}

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        oid = _to_object_id(candidate_id)
        return self.collection.find_one({"_id": oid}) if oid else None

    def find(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self.collection.find(query))

    def update_fields(self, candidate_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        oid = _to_object_id(candidate_id)
        if not oid:
            return None
        return self.collection.find_one_and_update(
            {"_id": oid}, {"$set": fields}, return_document=ReturnDocument.AFTER
        )

    def push_note(self, candidate_id: str, note: dict[str, Any], updated_at) -> dict[str, Any] | None:
        """$push only ever appends, so existing notes can't be altered by this path."""
        oid = _to_object_id(candidate_id)
        if not oid:
            return None
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$push": {"notes": note}, "$set": {"updated_at": updated_at}},
            return_document=ReturnDocument.AFTER,
        )

    def delete(self, candidate_id: str) -> bool:
        oid = _to_object_id(candidate_id)
        return bool(oid) and self.collection.delete_one({"_id": oid}).deleted_count == 1

    def distinct_roles(self) -> list[str]:
        return sorted(self.collection.distinct("role"))
