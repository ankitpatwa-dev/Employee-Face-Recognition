# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json


class DashboardBoard(models.Model):
    _name = 'dashboard.board'
    _description = 'Dashboard Board'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char('Dashboard Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text('Description')

    # Ownership & Sharing
    user_id = fields.Many2one(
        'res.users', string='Owner',
        default=lambda self: self.env.user,
        required=True, ondelete='cascade'
    )
    shared_user_ids = fields.Many2many(
        'res.users', 'dashboard_board_user_rel',
        'board_id', 'user_id',
        string='Shared With',
        domain="[('share', '=', False)]"
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )

    # Appearance
    theme = fields.Selection([
        ('default', 'Default'),
        ('dark', 'Dark Mode'),
        ('ocean', 'Ocean Blue'),
        ('sunset', 'Sunset'),
        ('forest', 'Forest Green'),
        ('corporate', 'Corporate'),
    ], string='Theme', default='default')

    # Layout
    layout_cols = fields.Integer('Grid Columns', default=12)

    # Real-time refresh
    auto_refresh = fields.Boolean('Auto Refresh', default=False)
    refresh_interval = fields.Integer('Refresh Interval (seconds)', default=30)

    # Flags
    is_predefined = fields.Boolean('Predefined Dashboard', default=False)
    is_favorite = fields.Boolean('Favorite', default=False)

    # Items
    item_ids = fields.One2many('dashboard.item', 'board_id', string='Dashboard Items')
    item_count = fields.Integer(compute='_compute_item_count', string='Items')

    @api.depends('item_ids')
    def _compute_item_count(self):
        for board in self:
            board.item_count = len(board.item_ids)

    # -----------------------------------------------------------------------
    # ORM Overrides
    # -----------------------------------------------------------------------
    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _('%s (Copy)') % self.name)
        default.setdefault('is_predefined', False)
        board = super().copy(default)
        for item in self.item_ids:
            item.copy({'board_id': board.id})
        return board

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------
    def action_open_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'advanced_sales_dashboard.action_dashboard',
            'params': {'board_id': self.id},
            'target': 'main',
        }

    def action_duplicate(self):
        self.ensure_one()
        new_board = self.copy()
        return new_board.action_open_dashboard()

    # -----------------------------------------------------------------------
    # Data Serialization
    # -----------------------------------------------------------------------
    def get_board_config(self):
        """Return serializable board configuration for the frontend."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'theme': self.theme,
            'layout_cols': self.layout_cols,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'is_predefined': self.is_predefined,
            'is_favorite': self.is_favorite,
            'item_ids': [item.get_item_config() for item in self.item_ids.sorted('sequence')],
        }

    # -----------------------------------------------------------------------
    # Export / Import
    # -----------------------------------------------------------------------
    def export_to_json(self):
        """Export full dashboard configuration as a portable JSON string."""
        self.ensure_one()
        export_data = {
            '_version': '1.0',
            'name': self.name,
            'theme': self.theme,
            'layout_cols': self.layout_cols,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'items': [],
        }
        for item in self.item_ids.sorted('sequence'):
            cfg = item.get_item_config()
            cfg.pop('id', None)      # Remove DB id for portability
            export_data['items'].append(cfg)
        return json.dumps(export_data, indent=2, default=str)

    @api.model
    def import_from_json(self, json_str, name=None):
        """Create a new board from a JSON string. Returns the new board."""
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, Exception) as e:
            raise UserError(_('Invalid dashboard JSON: %s') % str(e))

        board = self.create({
            'name': name or data.get('name', _('Imported Dashboard')),
            'theme': data.get('theme', 'default'),
            'layout_cols': data.get('layout_cols', 12),
            'auto_refresh': data.get('auto_refresh', False),
            'refresh_interval': data.get('refresh_interval', 30),
        })

        for item_data in data.get('items', []):
            item_data = dict(item_data)   # shallow copy
            item_data['board_id'] = board.id
            item_data.pop('id', None)
            # Restore currency by name
            currency_name = item_data.pop('currency_name', None)
            if currency_name:
                currency = self.env['res.currency'].search(
                    [('name', '=', currency_name)], limit=1
                )
                if currency:
                    item_data['currency_id'] = currency.id
            self.env['dashboard.item'].create(item_data)

        return board

    # -----------------------------------------------------------------------
    # Helpers for controller
    # -----------------------------------------------------------------------
    @api.model
    def get_user_boards(self):
        """Return all boards visible to the current user."""
        uid = self.env.uid
        boards = self.search([
            '|', '|',
            ('user_id', '=', uid),
            ('shared_user_ids', 'in', [uid]),
            ('is_predefined', '=', True),
        ])
        return [
            {
                'id': b.id,
                'name': b.name,
                'theme': b.theme,
                'is_predefined': b.is_predefined,
                'is_favorite': b.is_favorite,
                'item_count': b.item_count,
                'is_owner': b.user_id.id == uid,
            }
            for b in boards
        ]
