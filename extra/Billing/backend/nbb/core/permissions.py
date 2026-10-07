"""Catálogo de permissões.

Perfis são pacotes de permissões guardados no banco (tabelas role e
role_permission). Criar um perfil "Lançador" separado do Analyst, por
exemplo, é só mover `entries.write` de um perfil para outro, sem código.
"""


class P:
    ACCESS_REQUEST = "access.request"

    ENTRIES_READ = "entries.read"
    ENTRIES_WRITE = "entries.write"
    ENTRIES_APPROVE = "entries.approve"
    REPORTS_GENERATE = "reports.generate"

    ERP_GENERATE = "erp.generate"
    ERP_DOWNLOAD = "erp.download"

    PERIODS_CLOSE = "periods.close"
    PERIODS_REOPEN_REQUEST = "periods.reopen.request"
    PERIODS_REOPEN_APPROVE = "periods.reopen.approve"

    CONTRACTS_READ = "contracts.read"
    CONTRACTS_MANAGE = "contracts.manage"

    USERS_MANAGE = "users.manage"
    DELEGATIONS_MANAGE = "delegations.manage"
    SETTINGS_MANAGE = "settings.manage"

    AUDIT_READ = "audit.read"
