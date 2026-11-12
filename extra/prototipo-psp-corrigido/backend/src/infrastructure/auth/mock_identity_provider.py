"""Provedor de identidade MOCK. Substitui o SSO apenas no protótipo.

Todos os usuários de demonstração compartilham a senha e o código OTP vindos do ambiente.
"""

from __future__ import annotations

import hmac


class MockIdentityProvider:
    def __init__(self, password: str, otp_code: str) -> None:
        self._password = password.encode()
        self._otp_code = otp_code.encode()

    def check_password(self, username: str, password: str) -> bool:
        # compare_digest evita vazar, pelo tempo de resposta, quantos caracteres batem.
        return hmac.compare_digest(password.encode(), self._password)

    def check_second_factor(self, username: str, code: str) -> bool:
        return hmac.compare_digest(code.encode(), self._otp_code)
