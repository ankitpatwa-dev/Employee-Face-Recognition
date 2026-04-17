# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Sales Dashboard ──────────────────────────────────────────────
    monthly_sales_target = fields.Float(
        'Monthly Sales Target', default=0.0
    )

    # ── AI Integration ───────────────────────────────────────────────
    dashboard_ai_provider = fields.Selection([
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI ChatGPT'),
    ], string='AI Provider', default='gemini')

    # NOTE: API key is stored in ir.config_parameter for security.
    # These fields are just for UI binding via res.config.settings.

    # ── Dashboard Defaults ───────────────────────────────────────────
    dashboard_refresh_interval = fields.Integer(
        'Default Auto-Refresh Interval (seconds)', default=30
    )
    dashboard_number_system = fields.Selection([
        ('standard',    'Standard  (1,000,000)'),
        ('indian',      'Indian    (10,00,000)'),
        ('abbreviated', 'Short     (1M / 1K)'),
    ], string='Default Number Format', default='standard')
