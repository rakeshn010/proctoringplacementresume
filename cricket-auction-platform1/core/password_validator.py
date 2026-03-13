"""
Password strength validation for enhanced security.
"""
import re
from typing import List, Tuple
from fastapi import HTTPException, status


class PasswordValidator:
    """Validate password strength according to security best practices."""
    
    MIN_LENGTH = 8  # Reduced from 12 to 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = False  # Made optional instead of required
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @staticmethod
    def validate(password: str, raise_exception: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            raise_exception: If True, raise HTTPException on failure
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        
        Raises:
            HTTPException: If password is invalid and raise_exception=True
        """
        errors = []
        
        # Check length
        if len(password) < PasswordValidator.MIN_LENGTH:
            errors.append(f"Password must be at least {PasswordValidator.MIN_LENGTH} characters long")
        
        # Check uppercase
        if PasswordValidator.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check lowercase
        if PasswordValidator.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check digit
        if PasswordValidator.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one number")
        
        # Check special character
        if PasswordValidator.REQUIRE_SPECIAL:
            special_pattern = f"[{re.escape(PasswordValidator.SPECIAL_CHARS)}]"
            if not re.search(special_pattern, password):
                errors.append(f"Password must contain at least one special character ({PasswordValidator.SPECIAL_CHARS})")
        
        # Check for common patterns
        if PasswordValidator._has_common_patterns(password):
            errors.append("Password contains common patterns (e.g., '123', 'abc', 'password')")
        
        # Check for repeated characters
        if PasswordValidator._has_repeated_chars(password):
            errors.append("Password contains too many repeated characters")
        
        is_valid = len(errors) == 0
        
        if not is_valid and raise_exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Password does not meet security requirements", "errors": errors}
            )
        
        return is_valid, errors
    
    @staticmethod
    def _has_common_patterns(password: str) -> bool:
        """Check for common weak patterns."""
        password_lower = password.lower()
        
        # Only check for very common weak passwords
        common_passwords = [
            "password", "123456", "qwerty", "letmein",
            "admin", "welcome", "monkey", "dragon", "master",
            "111111", "123123", "000000", "password123", "admin123"
        ]
        
        for pattern in common_passwords:
            if pattern == password_lower:  # Exact match only
                return True
        
        return False
    
    @staticmethod
    def _has_repeated_chars(password: str, max_repeats: int = 4) -> bool:
        """Check for excessive character repetition (4+ same chars in a row)."""
        for i in range(len(password) - max_repeats + 1):
            if len(set(password[i:i+max_repeats])) == 1:
                return True
        return False
    
    @staticmethod
    def get_strength_score(password: str) -> int:
        """
        Calculate password strength score (0-100).
        
        Returns:
            Score from 0 (very weak) to 100 (very strong)
        """
        score = 0
        
        # Length score (up to 30 points)
        length = len(password)
        if length >= 12:
            score += min(30, (length - 12) * 2 + 20)
        else:
            score += length * 1.5
        
        # Character variety (up to 40 points)
        if re.search(r"[a-z]", password):
            score += 10
        if re.search(r"[A-Z]", password):
            score += 10
        if re.search(r"\d", password):
            score += 10
        if re.search(f"[{re.escape(PasswordValidator.SPECIAL_CHARS)}]", password):
            score += 10
        
        # Complexity bonus (up to 30 points)
        unique_chars = len(set(password))
        score += min(15, unique_chars)
        
        # Penalty for common patterns
        if PasswordValidator._has_common_patterns(password):
            score -= 20
        
        # Penalty for repeated characters
        if PasswordValidator._has_repeated_chars(password):
            score -= 10
        
        return max(0, min(100, int(score)))
    
    @staticmethod
    def get_strength_label(score: int) -> str:
        """Get human-readable strength label."""
        if score < 30:
            return "Very Weak"
        elif score < 50:
            return "Weak"
        elif score < 70:
            return "Moderate"
        elif score < 90:
            return "Strong"
        else:
            return "Very Strong"


# Convenience function
def validate_password(password: str) -> None:
    """
    Validate password and raise exception if invalid.
    Use this in your registration/password change endpoints.
    """
    PasswordValidator.validate(password, raise_exception=True)
