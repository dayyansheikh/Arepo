import pytest


@pytest.fixture(autouse=True)
def _reset_recipient_email_caps():
    """Per-recipient auth-email caps are process-global; isolate every test from the others."""
    from astrolabe.accounts import email

    email.reset_recipient_caps()
    yield
    email.reset_recipient_caps()
