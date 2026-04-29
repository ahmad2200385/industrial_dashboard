"""
Input validation utilities for common validation patterns.
"""
from typing import Any, Dict, List, Optional

from common.exceptions import ValidationException


class Validator:
    """Centralized validation utilities."""
    
    @staticmethod
    def validate_positive_int(value: Any, field_name: str) -> int:
        """
        Validate value is a positive integer.
        
        Args:
            value: Value to validate
            field_name: Name of field for error message
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationException: If validation fails
        """
        try:
            int_value = int(value)
            if int_value <= 0:
                raise ValidationException(
                    f"{field_name} must be positive",
                    {"field": field_name, "value": value}
                )
            return int_value
        except (TypeError, ValueError):
            raise ValidationException(
                f"{field_name} must be a valid integer",
                {"field": field_name, "value": value}
            )

    @staticmethod
    def validate_non_negative_int(value: Any, field_name: str) -> int:
        """
        Validate value is a non-negative integer.

        Args:
            value: Value to validate
            field_name: Name of field for error message

        Returns:
            Validated integer value

        Raises:
            ValidationException: If validation fails
        """
        try:
            int_value = int(value)
            if int_value < 0:
                raise ValidationException(
                    f"{field_name} must be non-negative",
                    {"field": field_name, "value": value}
                )
            return int_value
        except (TypeError, ValueError):
            raise ValidationException(
                f"{field_name} must be a valid integer",
                {"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, field_name: str) -> float:
        """
        Validate value is within range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of field for error message
            
        Raises:
            ValidationException: If validation fails
        """
        try:
            float_value = float(value)
            if not (min_val <= float_value <= max_val):
                raise ValidationException(
                    f"{field_name} must be between {min_val} and {max_val}",
                    {"field": field_name, "value": value, "min": min_val, "max": max_val}
                )
            return float_value
        except (TypeError, ValueError):
            raise ValidationException(
                f"{field_name} must be a valid number",
                {"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_string(value: Any, field_name: str, min_length: int = 1, max_length: Optional[int] = None) -> str:
        """
        Validate string value.
        
        Args:
            value: Value to validate
            field_name: Name of field for error message
            min_length: Minimum length
            max_length: Maximum length (None for unlimited)
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationException(
                f"{field_name} must be a string",
                {"field": field_name, "value": value}
            )
        
        value = value.strip()
        
        if len(value) < min_length:
            raise ValidationException(
                f"{field_name} must be at least {min_length} characters",
                {"field": field_name, "length": len(value), "min": min_length}
            )
        
        if max_length and len(value) > max_length:
            raise ValidationException(
                f"{field_name} must be at most {max_length} characters",
                {"field": field_name, "length": len(value), "max": max_length}
            )
        
        return value
    
    @staticmethod
    def validate_enum(value: Any, allowed_values: List[str], field_name: str) -> str:
        """
        Validate value is in allowed list.
        
        Args:
            value: Value to validate
            allowed_values: List of allowed values
            field_name: Name of field for error message
            
        Raises:
            ValidationException: If validation fails
        """
        if value not in allowed_values:
            raise ValidationException(
                f"{field_name} must be one of: {', '.join(allowed_values)}",
                {"field": field_name, "value": value, "allowed": allowed_values}
            )
        return value
    
    @staticmethod
    def validate_dict(value: Any, required_keys: List[str], field_name: str) -> Dict[str, Any]:
        """
        Validate dictionary has required keys.
        
        Args:
            value: Value to validate
            required_keys: List of required keys
            field_name: Name of field for error message
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(value, dict):
            raise ValidationException(
                f"{field_name} must be a dictionary",
                {"field": field_name}
            )
        
        missing_keys = [k for k in required_keys if k not in value]
        if missing_keys:
            raise ValidationException(
                f"{field_name} missing required keys: {', '.join(missing_keys)}",
                {"field": field_name, "missing_keys": missing_keys}
            )
        
        return value
