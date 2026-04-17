# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Sales Target ──────────────────────────────────────────────────
    monthly_sales_target = fields.Float(
        related='company_id.monthly_sales_target',
        readonly=False,
        string='Monthly Sales Target'
    )

    # ── AI ────────────────────────────────────────────────────────────
    dashboard_ai_provider = fields.Selection(
        related='company_id.dashboard_ai_provider',
        readonly=False,
        string='AI Provider'
    )
    dashboard_ai_api_key = fields.Char(
        string='AI API Key',
        help='Your Google Gemini or OpenAI API key. Stored securely in system parameters.',
        config_parameter='advanced_sales_dashboard.ai_api_key'
    )

    # ── Dashboard Defaults ────────────────────────────────────────────
    dashboard_refresh_interval = fields.Integer(
        related='company_id.dashboard_refresh_interval',
        readonly=False,
        string='Default Auto-Refresh Interval (seconds)'
    )
    dashboard_number_system = fields.Selection(
        related='company_id.dashboard_number_system',
        readonly=False,
        string='Default Number Format'
    )
