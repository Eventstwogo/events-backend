import re


class UsernameValidator:
    """
    Validates usernames based on customizable constraints.
    Allows letters, digits, spaces, hyphens (-), underscores (_), and periods (.).
    """

    DEFAULT_MIN_LENGTH = 4
    DEFAULT_MAX_LENGTH = 32

    def __init__(self, min_length=None, max_length=None, max_spaces=2):
        self.min_length = min_length or self.DEFAULT_MIN_LENGTH
        self.max_length = max_length or self.DEFAULT_MAX_LENGTH
        self.max_spaces = max_spaces

        allowed_chars = r"a-zA-Z0-9 ._\-"
        self.pattern = re.compile(rf"^[{allowed_chars}]+$")

    def validate(self, username: str) -> str:
        """
        Validates a username.

        Args:
            username (str): The username to validate.

        Returns:
            str: The normalized username if valid.

        Raises:
            ValueError: If validation fails.
        """
        if username is None:
            raise ValueError("Username cannot be None.")

        # Normalize whitespace
        username = self._normalize_whitespace(username)

        if not username:
            raise ValueError("Username cannot be empty.")

        # Allowed character set check
        if not self.pattern.match(username):
            raise ValueError(
                "Username can only contain letters, numbers, spaces, hyphens (-), "
                "underscores (_), and periods (.), first three characters must be letters."
            )

        # Length check
        if not (self.min_length <= len(username) <= self.max_length):
            raise ValueError(
                f"Username must be between {self.min_length} and {self.max_length} characters."
            )

        # First three characters must be letters
        if not username[:3].isalpha():
            raise ValueError("The first three characters must be letters.")

        # Cannot start or end with special characters
        if username[0] in "-_ .":
            raise ValueError("Username cannot start with a special character.")
        if username[-1] in "-_ .":
            raise ValueError("Username cannot end with a special character.")

        # Cannot start with digit
        if username[0].isdigit():
            raise ValueError("Username cannot start with a digit.")

        # No consecutive special characters
        if re.search(r"[-_. ]{2,}", username):
            raise ValueError(
                "Username cannot contain consecutive special characters."
            )

        # Limit whitespace count
        if username.count(" ") > self.max_spaces:
            raise ValueError(
                f"Username cannot contain more than {self.max_spaces} spaces."
            )

        # Repetition check
        if self._has_excessive_repetition(username, max_repeats=3):
            raise ValueError("Username contains excessive repeated characters.")

        # XSS prevention check
        if self._contains_xss(username):
            raise ValueError("Username contains potentially malicious content.")

        return username.lower()

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        """Replace multiple spaces with a single space and strip leading/trailing spaces."""
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _has_excessive_repetition(value: str, max_repeats: int) -> bool:
        """Check if any character is repeated more than max_repeats consecutively."""
        return bool(re.search(rf"(.)\1{{{max_repeats},}}", value))

    @staticmethod
    def _contains_xss(value: str) -> bool:
        """Basic check for XSS patterns in a string."""
        # Lowercase for easier matching
        val = value.lower()

        # Common dangerous patterns
        xss_patterns = [
            r"<script.*?>.*?</script>",
            r"on\w+\s*=",  # onload=, onclick=, etc.
            r"javascript:",
            r"expression\(",
            r"vbscript:",
        ]
        return any(re.search(pat, val) for pat in xss_patterns)


# Example usage
if __name__ == "__main__":
    validator = UsernameValidator(min_length=4, max_length=32, max_spaces=2)
    test_usernames = [
        "John_Doe-123",
        "Jo",
        "  BadStart",
        "Good Name",
        "Too  Many  Spaces",
        "Bad..Name",
        "12StartWithDigits",
        "Good-Name",
    ]

    for name in test_usernames:
        try:
            print(f"Validating: {name} -> {validator.validate(name)} ✅")
        except ValueError as e:
            print(f"Validating: {name} ❌ {e}")
