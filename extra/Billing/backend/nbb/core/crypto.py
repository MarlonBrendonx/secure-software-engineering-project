"""Criptografia de dados sensíveis em coluna (segredos TOTP)."""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class DataCipher:
    """AES-128-CBC + HMAC-SHA256 (Fernet). A primeira chave cifra; todas
    decifram, o que permite rotação: adicione a nova na frente, rode
    `nbb reencrypt` e depois remova a antiga."""

    def __init__(self, keys: list[str]):
        if not keys:
            raise ValueError("nenhuma chave de criptografia configurada")
        self._f = MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])

    def encrypt(self, plaintext: str) -> str:
        return self._f.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._f.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("dado cifrado inválido ou chave ausente") from exc

    def rotate(self, token: str) -> str:
        return self._f.rotate(token.encode()).decode()


def generate_key() -> str:
    return Fernet.generate_key().decode()
