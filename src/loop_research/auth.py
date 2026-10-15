"""HTTP Basic authentication for the single-user deployment."""

import base64
import binascii
import secrets

from loop_research.config import Settings


def authenticated(header: str, settings: Settings) -> bool:
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic":
        return False
    try:
        username, separator, password = base64.b64decode(encoded, validate=True).partition(b":")
    except (ValueError, binascii.Error):
        return False
    # Compare both fields even when the first comparison fails.
    valid_user = secrets.compare_digest(username, settings.auth_username.encode("utf-8"))
    valid_password = secrets.compare_digest(
        password, settings.auth_password.get_secret_value().encode("utf-8")
    )
    return bool(separator and valid_user and valid_password)
