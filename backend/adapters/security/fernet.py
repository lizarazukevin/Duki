from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from backend.adapters.security.base import CredentialCipher
from backend.errors import CredentialEncryptionError


class FernetCredentialCipher(CredentialCipher):
    """Encrypt with the primary key and decrypt with any configured rotation key."""

    def __init__(self, keys: tuple[str, ...]) -> None:
        if not keys:
            raise CredentialEncryptionError("Credential encryption is not configured")
        try:
            self._cipher = MultiFernet([Fernet(key.encode("ascii")) for key in keys])
        except (UnicodeEncodeError, ValueError) as error:
            raise CredentialEncryptionError(
                "Credential encryption configuration is invalid"
            ) from error

    def encrypt(self, plaintext: str) -> str:
        try:
            return self._cipher.encrypt(plaintext.encode("utf-8")).decode("ascii")
        except (TypeError, UnicodeError) as error:
            raise CredentialEncryptionError("Credential encryption failed") from error

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._cipher.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, TypeError, UnicodeError) as error:
            raise CredentialEncryptionError("Stored credential cannot be decrypted") from error
