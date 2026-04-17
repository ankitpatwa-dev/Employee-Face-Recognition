# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json


class DashboardItem(models.Model):
    _name = 'dashboard.item'
    _description = 'Dashboard Item'
    _order = 'sequence, id'

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    board_id = fields.Many2one(
        'dashboard.board', string='Dashboard',
        required=True, ondelete='cascade'
    )
    name = fields.Char('Title', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    item_type = fields.Selection([
        ('kpi',    'KPI Card'),
        ('chart',  'Chart'),
        ('list',   'List View'),
        ('gauge',  'Gauge / Target Ring'),
        ('todo',   'To-Do List'),
        ('note',   'Note / Text'),
    ], string='Item Type', default='kpi', required=True)

    # ------------------------------------------------------------------
    # Data Source
    # ------------------------------------------------------------------
    model_name = fields.Char(
        'Data Model', default='sale.order',
        help='Technical name of the Odoo model, e.g., sale.order'
    )
    domain = fields.Char(
        'Filter Domain', default='[]',
        help='JSON domain. Use %UID for current user ID, %MYCOMPANY for current company ID.'
    )
    filter_date_field = fields.Char(
        'Date Field', default='date_order',
        help='Field name used for date-range filtering'
    )

    # ------------------------------------------------------------------
    # Date Filter (per item)
    # ------------------------------------------------------------------
    date_filter = fields.Selection([
        ('none',    'No Date Filter'),
        ('today',   'Today'),
        ('week',    'This Week'),
        ('month',   'This Month'),
        ('quarter', 'This Quarter'),
        ('year',    'This Year'),
        ('custom',  'Custom Range'),
    ], string='Date Filter', default='month')
    date_start = fields.Date('Date From')
    date_end   = fields.Date('Date To')

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    measure_field    = fields.Char('Measure Field', default='amount_untaxed')
    measure_operator = fields.Selection([
        ('sum',   'Sum'),
        ('count', 'Count'),
        ('avg',   'Average'),
        ('min',   'Minimum'),
        ('max',   'Maximum'),
    ], string='Aggregate Function', default='sum')

    group_by_field  = fields.Char('Group By')
    sort_by         = fields.Char('Sort By Field')
    sort_order      = fields.Selection([('desc','Descending'),('asc','Ascending')], default='desc')
    record_limit    = fields.Integer('Record Limit', default=10)

    compare_period  = fields.Boolean('Compare with Previous Period', default=False)

    # ------------------------------------------------------------------
    # Chart Settings
    # ------------------------------------------------------------------
    chart_type = fields.Selection([
        ('line',          'Line'),
        ('bar',           'Bar'),
        ('doughnut',      'Doughnut'),
        ('pie',           'Pie'),
        ('radar',         'Radar'),
        ('polarArea',     'Polar Area'),
        ('horizontalBar', 'Horizontal Bar'),
    ], string='Chart Type', default='bar')

    chart_color_palette = fields.Selection([
        ('default',     'Default'),
        ('blues',       'Blues'),
        ('greens',      'Greens'),
        ('warm',        'Warm'),
        ('cool',        'Cool'),
        ('monochrome',  'Monochrome'),
        ('pastel',      'Pastel'),
    ], string='Color Palette', default='default')

    show_data_values = fields.Boolean('Show Data Labels', default=False)
    show_legend      = fields.Boolean('Show Legend', default=True)
    fill_area        = fields.Boolean('Fill Area (Line)', default=True)
    smooth_line      = fields.Boolean('Smooth Line', default=True)

    # ------------------------------------------------------------------
    # KPI / Visual Settings
    # ------------------------------------------------------------------
    color_theme = fields.Selection([
        ('primary',  'Blue'),
        ('success',  'Green'),
        ('warning',  'Orange'),
        ('danger',   'Red'),
        ('info',     'Cyan'),
        ('purple',   'Purple'),
        ('pink',     'Pink'),
        ('indigo',   'Indigo'),
        ('teal',     'Teal'),
        ('dark',     'Dark'),
    ], string='Accent Color', default='primary')

    icon = fields.Char(
        'Icon (FA class)', default='fa-bar-chart',
        help='Font Awesome 4 icon class, e.g. fa-dollar, fa-shopping-cart'
    )

    # ------------------------------------------------------------------
    # Units & Currency
    # ------------------------------------------------------------------
    unit_type = fields.Selection([
        ('monetary',   'Monetary (Currency)'),
        ('percentage', 'Percentage (%)'),
        ('number',     'Number'),
        ('custom',     'Custom'),
    ], string='Unit Type', default='number')
    custom_unit = fields.Char('Custom Unit Label')
    currency_id = fields.Many2one(
        'res.currency', string='Display Currency',
        default=lambda self: self.env.company.currency_id
    )

    # ------------------------------------------------------------------
    # Target / Gauge
    # ------------------------------------------------------------------
    has_target   = fields.Boolean('Enable Target', default=False)
    target_value = fields.Float('Target Value', default=0.0)
    target_label = fields.Char('Target Label', default='Target')

    # ------------------------------------------------------------------
    # Number Format
    # ------------------------------------------------------------------
    number_system = fields.Selection([
        ('standard',    'Standard  (1,000,000)'),
        ('indian',      'Indian    (10,00,000)'),
        ('abbreviated', 'Short     (1M / 1K)'),
    ], string='Number Format', default='standard')

    # ------------------------------------------------------------------
    # List View
    # ------------------------------------------------------------------
    list_style  = fields.Selection([
        ('compact', 'Compact Table'),
        ('card',    'Card List'),
    ], string='List Style', default='compact')
    list_fields = fields.Char(
        'Visible Fields (JSON)', default='[]',
        help='JSON array of field names to display in list, e.g. ["name","partner_id","amount_total"]'
    )

    # ------------------------------------------------------------------
    # To-Do
    # ------------------------------------------------------------------
    todo_items = fields.Text('To-Do Items (JSON)', default='[]')

    # ------------------------------------------------------------------
    # Note
    # ------------------------------------------------------------------
    note_content  = fields.Text('Note Content')
    note_bg_color = fields.Char('Note Background Color', default='#fff9c4')

    # ------------------------------------------------------------------
    # GridStack Layout
    # ------------------------------------------------------------------
    grid_x = fields.Integer('Grid Column Start', default=0)
    grid_y = fields.Integer('Grid Row Start', default=0)
    grid_w = fields.Integer('Grid Width', default=4)
    grid_h = fields.Integer('Grid Height', default=3)

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------
    ai_insights  = fields.Text('AI Insights (cached)')
    ai_keywords  = fields.Char('AI Keywords')

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def get_item_config(self):
        """Return a JSON-serialisable dict of this item's full configuration."""
        self.ensure_one()
        return {
            'id':                  self.id,
            'name':                self.name,
            'sequence':            self.sequence,
            'item_type':           self.item_type,
            # data source
            'model_name':          self.model_name or '',
            'domain':              self.domain or '[]',
            'filter_date_field':   self.filter_date_field or '',
            # date
            'date_filter':         self.date_filter,
            'date_start':          str(self.date_start)  if self.date_start  else None,
            'date_end':            str(self.date_end)    if self.date_end    else None,
            # aggregation
            'measure_field':       self.measure_field or '',
            'measure_operator':    self.measure_operator,
            'group_by_field':      self.group_by_field or '',
            'sort_by':             self.sort_by or '',
            'sort_order':          self.sort_order,
            'record_limit':        self.record_limit,
            'compare_period':      self.compare_period,
            # chart
            'chart_type':          self.chart_type,
            'chart_color_palette': self.chart_color_palette,
            'show_data_values':    self.show_data_values,
            'show_legend':         self.show_legend,
            'fill_area':           self.fill_area,
            'smooth_line':         self.smooth_line,
            # visual
            'color_theme':         self.color_theme,
            'icon':                self.icon or 'fa-bar-chart',
            # units
            'unit_type':           self.unit_type,
            'custom_unit':         self.custom_unit or '',
            'currency_symbol':     self.currency_id.symbol if self.currency_id else '',
            'currency_name':       self.currency_id.name   if self.currency_id else '',
            # target
            'has_target':          self.has_target,
            'target_value':        self.target_value,
            'target_label':        self.target_label or 'Target',
            # number format
            'number_system':       self.number_system,
            # list
            'list_style':          self.list_style,
            'list_fields':         self.list_fields or '[]',
            # todo / note
            'todo_items':          self.todo_items or '[]',
            'note_content':        self.note_content or '',
            'note_bg_color':       self.note_bg_color or '#fff9c4',
            # layout
            'grid_x':              self.grid_x,
            'grid_y':              self.grid_y,
            'grid_w':              self.grid_w,
            'grid_h':              self.grid_h,
            # ai
            'ai_insights':         self.ai_insights or '',
            'ai_keywords':         self.ai_keywords or '',
        }

    # ------------------------------------------------------------------
    # To-Do helpers
    # ------------------------------------------------------------------
    def toggle_todo(self, todo_index):
        self.ensure_one()
        try:
            items = json.loads(self.todo_items or '[]')
        except Exception:
            items = []
        if 0 <= todo_index < len(items):
            items[todo_index]['done'] = not items[todo_index].get('done', False)
            self.todo_items = json.dumps(items)
        return items

    def add_todo(self, text):
        self.ensure_one()
        try:
            items = json.loads(self.todo_items or '[]')
        except Exception:
            items = []
        items.append({'text': text, 'done': False})
        self.todo_items = json.dumps(items)
        return items

    def delete_todo(self, todo_index):
        self.ensure_one()
        try:
            items = json.loads(self.todo_items or '[]')
        except Exception:
            items = []
        if 0 <= todo_index < len(items):
            items.pop(todo_index)
            self.todo_items = json.dumps(items)
        return items
