"""
Utility helper functions.
Common utilities used across the application.
"""
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException


def validate_object_id(id_str: str, field_name: str = "ID") -> ObjectId:
    """
    Validate and convert string to ObjectId.
    
    Args:
        id_str: String representation of ObjectId
        field_name: Name of the field for error message
    
    Returns:
        ObjectId instance
    
    Raises:
        HTTPException: If ID is invalid
    """
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format"
        )


def serialize_doc(doc: dict) -> dict:
    """
    Convert MongoDB document to JSON-serializable format.
    
    Args:
        doc: MongoDB document
    
    Returns:
        Serialized document with _id as string
    """
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage safely.
    
    Args:
        part: Part value
        total: Total value
    
    Returns:
        Percentage value (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def format_currency(amount: float) -> str:
    """
    Format amount as currency.
    
    Args:
        amount: Amount to format
    
    Returns:
        Formatted currency string
    """
    return f"₹{amount:,.2f}"
