# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from fastapi import Depends

from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.app.ports.input.google_login_use_case import GoogleLoginUseCase
from admin_auth.app.ports.input.logout_use_case import LogoutUseCase
from admin_auth.app.ports.input.refresh_use_case import RefreshUseCase
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.google_identity_port import GoogleIdentityPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort
from admin_auth.app.use_cases.current_admin_interactor import CurrentAdminInteractor
from admin_auth.app.use_cases.google_login_interactor import GoogleLoginInteractor
from admin_auth.app.use_cases.logout_interactor import LogoutInteractor
from admin_auth.app.use_cases.refresh_interactor import RefreshInteractor
from admin_auth.dependencies.providers import (
    get_access_token_issuer_port,
    get_admin_account_port,
    get_google_identity_port,
    get_refresh_token_port,
)


def get_google_login_use_case(
    identity: GoogleIdentityPort = Depends(get_google_identity_port),
    accounts: AdminAccountPort = Depends(get_admin_account_port),
    access_issuer: AccessTokenIssuerPort = Depends(get_access_token_issuer_port),
    refresh_tokens: RefreshTokenPort = Depends(get_refresh_token_port),
) -> GoogleLoginUseCase:
    return GoogleLoginInteractor(identity, accounts, access_issuer, refresh_tokens)


def get_refresh_use_case(
    refresh_tokens: RefreshTokenPort = Depends(get_refresh_token_port),
    accounts: AdminAccountPort = Depends(get_admin_account_port),
    access_issuer: AccessTokenIssuerPort = Depends(get_access_token_issuer_port),
) -> RefreshUseCase:
    return RefreshInteractor(refresh_tokens, accounts, access_issuer)


def get_logout_use_case(
    access_issuer: AccessTokenIssuerPort = Depends(get_access_token_issuer_port),
    refresh_tokens: RefreshTokenPort = Depends(get_refresh_token_port),
) -> LogoutUseCase:
    return LogoutInteractor(access_issuer, refresh_tokens)


def get_current_admin_use_case(
    access_issuer: AccessTokenIssuerPort = Depends(get_access_token_issuer_port),
    accounts: AdminAccountPort = Depends(get_admin_account_port),
) -> CurrentAdminUseCase:
    return CurrentAdminInteractor(access_issuer, accounts)
