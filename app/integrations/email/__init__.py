"""Transactional email adapter."""

from app.integrations.email.client import AzureEmailSender, EmailError, UnconfiguredMailer

__all__ = ["AzureEmailSender", "EmailError", "UnconfiguredMailer"]
