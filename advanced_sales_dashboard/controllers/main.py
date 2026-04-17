# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json


class DashboardController(http.Controller):

    # =========================================================================
    # Board endpoints
    # =========================================================================

    @http.route('/dashboard/boards', type='json', auth='user', methods=['POST'])
    def get_boards(self, **kw):
        return request.env['dashboard.board'].get_user_boards()

    @http.route('/dashboard/board/get', type='json', auth='user', methods=['POST'])
    def get_board(self, board_id, **kw):
        board = request.env['dashboard.board'].browse(int(board_id))
        if not board.exists():
            return {'error': 'Board not found'}
        return board.get_board_config()

    @http.route('/dashboard/board/create', type='json', auth='user', methods=['POST'])
    def create_board(self, name='New Dashboard', theme='default', **kw):
        board = request.env['dashboard.board'].create({
            'name': name,
            'theme': theme,
        })
        return {'id': board.id, 'name': board.name}

    @http.route('/dashboard/board/update', type='json', auth='user', methods=['POST'])
    def update_board(self, board_id, vals, **kw):
        board = request.env['dashboard.board'].browse(int(board_id))
        if not board.exists():
            return {'error': 'Board not found'}
        board.write(vals)
        return {'success': True}

    @http.route('/dashboard/board/delete', type='json', auth='user', methods=['POST'])
    def delete_board(self, board_id, **kw):
        board = request.env['dashboard.board'].browse(int(board_id))
        if board.exists():
            board.unlink()
        return {'success': True}

    @http.route('/dashboard/board/duplicate', type='json', auth='user', methods=['POST'])
    def duplicate_board(self, board_id, **kw):
        board = request.env['dashboard.board'].browse(int(board_id))
        if not board.exists():
            return {'error': 'Board not found'}
        new_board = board.copy()
        return {'id': new_board.id, 'name': new_board.name}

    # ── Export / Import ───────────────────────────────────────────────

    @http.route('/dashboard/board/export', type='json', auth='user', methods=['POST'])
    def export_board(self, board_id, **kw):
        board = request.env['dashboard.board'].browse(int(board_id))
        if not board.exists():
            return {'error': 'Board not found'}
        return {'json': board.export_to_json(), 'filename': f'{board.name}.json'}

    @http.route('/dashboard/board/import', type='json', auth='user', methods=['POST'])
    def import_board(self, json_str, name=None, **kw):
        try:
            new_board = request.env['dashboard.board'].import_from_json(json_str, name=name)
            return {'id': new_board.id, 'name': new_board.name}
        except Exception as e:
            return {'error': str(e)}

    # =========================================================================
    # Item endpoints
    # =========================================================================

    @http.route('/dashboard/item/data', type='json', auth='user', methods=['POST'])
    def get_item_data(self, item_id, params=None, **kw):
        return request.env['advanced.sales.dashboard'].get_item_data(
            int(item_id), params=params or {}
        )

    @http.route('/dashboard/item/create', type='json', auth='user', methods=['POST'])
    def create_item(self, board_id, vals, **kw):
        vals['board_id'] = int(board_id)
        item = request.env['dashboard.item'].create(vals)
        return item.get_item_config()

    @http.route('/dashboard/item/update', type='json', auth='user', methods=['POST'])
    def update_item(self, item_id, vals, **kw):
        item = request.env['dashboard.item'].browse(int(item_id))
        if not item.exists():
            return {'error': 'Item not found'}
        item.write(vals)
        return item.get_item_config()

    @http.route('/dashboard/item/delete', type='json', auth='user', methods=['POST'])
    def delete_item(self, item_id, **kw):
        item = request.env['dashboard.item'].browse(int(item_id))
        if item.exists():
            item.unlink()
        return {'success': True}

    @http.route('/dashboard/item/layout', type='json', auth='user', methods=['POST'])
    def save_layout(self, layout, **kw):
        """Save GridStack drag/resize positions.
        layout: [{'id': item_id, 'x': ..., 'y': ..., 'w': ..., 'h': ...}, ...]
        """
        Item = request.env['dashboard.item']
        for tile in (layout or []):
            item = Item.browse(int(tile['id']))
            if item.exists():
                item.write({
                    'grid_x': tile.get('x', 0),
                    'grid_y': tile.get('y', 0),
                    'grid_w': tile.get('w', 4),
                    'grid_h': tile.get('h', 3),
                })
        return {'success': True}

    # ── To-Do actions ─────────────────────────────────────────────────

    @http.route('/dashboard/item/todo/toggle', type='json', auth='user', methods=['POST'])
    def todo_toggle(self, item_id, todo_index, **kw):
        item = request.env['dashboard.item'].browse(int(item_id))
        return {'items': item.toggle_todo(int(todo_index))}

    @http.route('/dashboard/item/todo/add', type='json', auth='user', methods=['POST'])
    def todo_add(self, item_id, text, **kw):
        item = request.env['dashboard.item'].browse(int(item_id))
        return {'items': item.add_todo(text)}

    @http.route('/dashboard/item/todo/delete', type='json', auth='user', methods=['POST'])
    def todo_delete(self, item_id, todo_index, **kw):
        item = request.env['dashboard.item'].browse(int(item_id))
        return {'items': item.delete_todo(int(todo_index))}

    # =========================================================================
    # AI endpoints
    # =========================================================================

    @http.route('/dashboard/ai/generate_dashboard', type='json', auth='user', methods=['POST'])
    def ai_generate_dashboard(self, prompt, **kw):
        return request.env['advanced.sales.dashboard'].ai_generate_dashboard(prompt)

    @http.route('/dashboard/ai/generate_item', type='json', auth='user', methods=['POST'])
    def ai_generate_item(self, prompt, keywords='', **kw):
        return request.env['advanced.sales.dashboard'].ai_generate_item(prompt, keywords)

    @http.route('/dashboard/ai/chart_insights', type='json', auth='user', methods=['POST'])
    def ai_chart_insights(self, item_id, chart_data=None, **kw):
        return request.env['advanced.sales.dashboard'].ai_extract_chart_insights(
            int(item_id), chart_data or {}
        )

    # =========================================================================
    # Legacy endpoint (backward compat)
    # =========================================================================

    @http.route('/advanced_sales_dashboard/fetch_data', type='json', auth='user')
    def fetch_dashboard_data(self, **kw):
        return request.env['advanced.sales.dashboard'].get_dashboard_data(
            date_filter=kw.get('date_filter', 'month'),
            salesperson_id=kw.get('salesperson_id'),
            team_id=kw.get('team_id'),
        )

    # =========================================================================
    # Available filters / meta
    # =========================================================================
    @http.route('/dashboard/meta/filters', type='json', auth='user', methods=['POST'])
    def get_filters(self, **kw):
        return request.env['advanced.sales.dashboard']._get_available_filters()

    @http.route('/dashboard/meta/model_fields', type='json', auth='user', methods=['POST'])
    def get_model_fields(self, model_name, **kw):
        """Return field list for the model selector in item configurator."""
        return request.env['advanced.sales.dashboard'].get_model_fields(model_name)
