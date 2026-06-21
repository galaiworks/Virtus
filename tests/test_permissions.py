"""ゼロトラスト権限スコープ(要件定義 §6.1)。"""

from __future__ import annotations

import pytest

from src.officina.governance.permissions import (
    SCOPES,
    PermissionDenied,
    check_permission,
    enforce_permission,
)


def test_outreach_can_send_but_not_write_prod():
    assert check_permission("outreach", "send_email")
    assert not check_permission("outreach", "write_prod_db")


def test_builder_cannot_deploy_or_write_prod_db():
    assert check_permission("builder", "write_code")
    assert not check_permission("builder", "deploy_prod")
    assert not check_permission("builder", "write_prod_db")


def test_human_only_actions_denied_for_all_agents():
    for agent in SCOPES:
        assert not check_permission(agent, "sign_contract")
        assert not check_permission(agent, "approve_delivery")


def test_enforce_raises_for_unknown_action():
    with pytest.raises(PermissionDenied):
        enforce_permission("scout", "send_email")


def test_enforce_human_only_message():
    with pytest.raises(PermissionDenied, match="人間専用"):
        enforce_permission("closer", "sign_contract")
