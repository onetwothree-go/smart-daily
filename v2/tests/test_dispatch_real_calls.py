"""测试实际调用 dispatch 中的私有函数以改进覆盖率"""

from unittest.mock import MagicMock, patch

from smart_daily_v2.notifiers import dispatch


def test_send_personal_with_recipients():
    """测试 _send_personal 函数在有收件人时的情况"""
    mock_email = MagicMock()
    mock_email.send.return_value = True

    with patch("smart_daily_v2.notifiers.dispatch.EmailNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_email
        with patch("smart_daily_v2.notifiers.dispatch.load_member_emails") as mock_load:
            mock_load.return_value = {"testuser": ["test@example.com"]}

            result = dispatch._send_personal("testuser", "test body")
            assert result is True
            mock_email.send.assert_called_once_with(
                "testuser日报", "test body", ["test@example.com"]
            )


def test_send_personal_no_recipients():
    """测试 _send_personal 函数在无收件人时的情况"""
    with patch("smart_daily_v2.notifiers.dispatch.load_member_emails") as mock_load:
        mock_load.return_value = {"testuser": []}

        result = dispatch._send_personal("testuser", "test body")
        assert result is False


def test_send_personal_exception():
    """测试 _send_personal 函数在异常时返回 False"""
    mock_email = MagicMock()
    mock_email.send.side_effect = Exception("Send failed")

    with patch("smart_daily_v2.notifiers.dispatch.EmailNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_email
        with patch("smart_daily_v2.notifiers.dispatch.load_member_emails") as mock_load:
            mock_load.return_value = {"testuser": ["test@example.com"]}

            result = dispatch._send_personal("testuser", "test body")
            assert result is False


def test_send_team_group_success():
    """测试 _send_team_group 函数成功发送"""
    mock_webhook = MagicMock()
    mock_webhook.send.return_value = True

    with patch("smart_daily_v2.notifiers.dispatch.FeishuWebhookNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_webhook

        result = dispatch._send_team_group("test body")
        assert result is True
        mock_webhook.send.assert_called_once_with("团队日报", "test body", [])


def test_send_team_group_exception():
    """测试 _send_team_group 函数在异常时返回 False"""
    mock_webhook = MagicMock()
    mock_webhook.send.side_effect = Exception("Webhook failed")

    with patch("smart_daily_v2.notifiers.dispatch.FeishuWebhookNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_webhook

        result = dispatch._send_team_group("test body")
        assert result is False


def test_send_team_external_success():
    """测试 _send_team_external 函数成功发送"""
    mock_email = MagicMock()
    mock_email.send.return_value = True

    with patch("smart_daily_v2.notifiers.dispatch.EmailNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_email

        result = dispatch._send_team_external("test body", ["ext@example.com"])
        assert result is True
        mock_email.send.assert_called_once_with("团队日报", "test body", ["ext@example.com"])


def test_send_team_external_exception():
    """测试 _send_team_external 函数在异常时返回 False"""
    mock_email = MagicMock()
    mock_email.send.side_effect = Exception("Send failed")

    with patch("smart_daily_v2.notifiers.dispatch.EmailNotifier") as mock_notifier_class:
        mock_notifier_class.from_env.return_value = mock_email

        result = dispatch._send_team_external("test body", ["ext@example.com"])
        assert result is False
