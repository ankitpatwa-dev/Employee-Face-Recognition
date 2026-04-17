# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
import json
import logging
import urllib.request
import urllib.error

_logger = logging.getLogger(__name__)

# ── Color palettes for charts ─────────────────────────────────────────────────
PALETTES = {
    'default':    ['#875a7b','#00a09d','#e2808a','#1f77b4','#ff7f0e','#2ca02c','#9467bd','#8c564b'],
    'blues':      ['#003f88','#00509d','#0077b6','#0096c7','#00b4d8','#48cae4','#90e0ef','#ade8f4'],
    'greens':     ['#1b4332','#2d6a4f','#40916c','#52b788','#74c69d','#95d5b2','#b7e4c7','#d8f3dc'],
    'warm':       ['#d62828','#f77f00','#fcbf49','#eae2b7','#e76f51','#f4a261','#e9c46a','#264653'],
    'cool':       ['#03045e','#023e8a','#0077b6','#0096c7','#48cae4','#ade8f4','#caf0f8','#90e0ef'],
    'monochrome': ['#212529','#343a40','#495057','#6c757d','#adb5bd','#ced4da','#dee2e6','#e9ecef'],
    'pastel':     ['#ffadad','#ffd6a5','#fdffb6','#caffbf','#9bf6ff','#a0c4ff','#bdb2ff','#ffc6ff'],
}


class SalesDashboard(models.AbstractModel):
    _name = 'advanced.sales.dashboard'
    _description = 'Advanced Sales Dashboard'

    # =========================================================================
    # Public: legacy single-dashboard (kept for backward compat)
    # =========================================================================
    @api.model
    def get_dashboard_data(self, date_filter='month', salesperson_id=False,
                           team_id=False, company_id=False):
        domain = [('state', 'in', ['sale', 'done'])]
        if salesperson_id:
            domain.append(('user_id', '=', int(salesperson_id)))
        if team_id:
            domain.append(('team_id', '=', int(team_id)))
        if company_id:
            domain.append(('company_id', '=', int(company_id)))
        else:
            domain.append(('company_id', 'in', self.env.companies.ids))

        today = fields.Date.context_today(self)
        start_date = prev_start = prev_end = False

        if date_filter == 'today':
            start_date = today
            prev_start = today - relativedelta(days=1)
            prev_end   = today - relativedelta(days=1)
        elif date_filter == 'week':
            start_date = today - relativedelta(weeks=1)
            prev_start = start_date - relativedelta(weeks=1)
            prev_end   = start_date - relativedelta(days=1)
        elif date_filter == 'month':
            start_date = today.replace(day=1)
            prev_start = start_date - relativedelta(months=1)
            prev_end   = start_date - relativedelta(days=1)
        elif date_filter == 'quarter':
            q_month    = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=q_month, day=1)
            prev_start = start_date - relativedelta(months=3)
            prev_end   = start_date - relativedelta(days=1)
        elif date_filter == 'year':
            start_date = today.replace(month=1, day=1)
            prev_start = start_date - relativedelta(years=1)
            prev_end   = start_date - relativedelta(days=1)

        domain_cur = list(domain)
        domain_prev = list(domain)
        if start_date:
            domain_cur  += [('date_order', '>=', start_date), ('date_order', '<=', today)]
            domain_prev += [('date_order', '>=', prev_start), ('date_order', '<=', prev_end)]

        kpi          = self._get_kpi_data(domain_cur, domain_prev)
        chart        = self._get_chart_data(domain_cur, date_filter)
        performers   = self._get_top_performers(domain_cur)
        orders       = self._get_recent_orders(domain_cur)
        insight      = self._generate_insights(kpi, performers)
        filters      = self._get_available_filters()

        return {
            'kpi': kpi, 'charts': chart, 'top_performers': performers,
            'recent_orders': orders, 'insight_message': insight,
            'available_filters': filters,
        }

    # =========================================================================
    # Public: per-item data engine (new)
    # =========================================================================
    @api.model
    def get_item_data(self, item_id, params=None):
        """Compute and return data for a single dashboard.item."""
        params = params or {}
        item = self.env['dashboard.item'].browse(item_id)
        if not item.exists():
            return {'error': 'Item not found'}

        try:
            domain = self._expand_domain(item.domain or '[]', item)
            domain += self._get_date_domain(item, params)
            # drill-down extra filter
            drill = params.get('drill_domain')
            if drill:
                domain += safe_eval(drill) if isinstance(drill, str) else drill

            if item.item_type == 'kpi':
                return self._item_kpi(item, domain, params)
            elif item.item_type == 'chart':
                return self._item_chart(item, domain)
            elif item.item_type == 'list':
                return self._item_list(item, domain)
            elif item.item_type == 'gauge':
                return self._item_gauge(item, domain, params)
            elif item.item_type == 'todo':
                return {'todo_items': json.loads(item.todo_items or '[]')}
            elif item.item_type == 'note':
                return {'note_content': item.note_content or '', 'note_bg_color': item.note_bg_color}
            else:
                return {}
        except Exception as e:
            _logger.error("Dashboard item %s error: %s", item_id, e, exc_info=True)
            return {'error': str(e)}

    @api.model
    def save_layout(self, layout):
        """Persist GridStack drag/resize positions.
        layout: [{'id': item_id, 'x': ..., 'y': ..., 'w': ..., 'h': ...}, ...]
        """
        Item = self.env['dashboard.item']
        for tile in (layout or []):
            try:
                item = Item.browse(int(tile['id']))
                if item.exists():
                    item.write({
                        'grid_x': tile.get('x', 0),
                        'grid_y': tile.get('y', 0),
                        'grid_w': tile.get('w', 4),
                        'grid_h': tile.get('h', 3),
                    })
            except Exception as e:
                _logger.warning("Layout save error for tile %s: %s", tile, e)
        return {'success': True}

    @api.model
    def get_model_fields(self, model_name):
        """Return field list for the given model (used by item configurator)."""
        try:
            Model = self.env[model_name]
        except KeyError:
            return {'error': f'Unknown model: {model_name}'}
        result = []
        for fname, field in Model._fields.items():
            if field.type in ('integer', 'float', 'monetary', 'char', 'many2one', 'date', 'datetime'):
                result.append({
                    'name': fname,
                    'string': field.string,
                    'type': field.type,
                })
        return sorted(result, key=lambda x: x['string'])

    # =========================================================================
    # Domain helpers
    # =========================================================================
    def _expand_domain(self, domain_str, item=None):
        """Replace %UID, %MYCOMPANY macros and safe-eval the domain string."""
        uid  = str(self.env.uid)
        cids = ','.join(str(c) for c in self.env.companies.ids)
        domain_str = domain_str.replace('%UID', uid)
        domain_str = domain_str.replace('%MYCOMPANY', str(self.env.company.id))
        try:
            return safe_eval(domain_str) or []
        except Exception:
            return []

    def _get_date_domain(self, item, params=None):
        """Return a date filter domain list for a dashboard.item."""
        params = params or {}
        date_filter = params.get('date_filter') or item.date_filter
        date_field  = item.filter_date_field or 'date_order'
        today       = fields.Date.context_today(self)

        if date_filter == 'none':
            return []
        if date_filter == 'custom':
            ds = params.get('date_start') or (str(item.date_start) if item.date_start else None)
            de = params.get('date_end')   or (str(item.date_end)   if item.date_end   else None)
            d = []
            if ds: d.append((date_field, '>=', ds))
            if de: d.append((date_field, '<=', de))
            return d

        start = False
        if date_filter == 'today':
            start = today
        elif date_filter == 'week':
            start = today - relativedelta(weeks=1)
        elif date_filter == 'month':
            start = today.replace(day=1)
        elif date_filter == 'quarter':
            q_month = ((today.month - 1) // 3) * 3 + 1
            start   = today.replace(month=q_month, day=1)
        elif date_filter == 'year':
            start = today.replace(month=1, day=1)

        if start:
            return [(date_field, '>=', start), (date_field, '<=', today)]
        return []

    def _prev_period_domain(self, item, params=None):
        """Return domain for previous period (for compare_period)."""
        params = params or {}
        date_filter = params.get('date_filter') or item.date_filter
        date_field  = item.filter_date_field or 'date_order'
        today       = fields.Date.context_today(self)

        if date_filter in ('none', 'custom'):
            return []

        start = end = False
        if date_filter == 'today':
            start = today - relativedelta(days=1)
            end   = start
        elif date_filter == 'week':
            cur_start = today - relativedelta(weeks=1)
            start     = cur_start - relativedelta(weeks=1)
            end       = cur_start - relativedelta(days=1)
        elif date_filter == 'month':
            cur_start = today.replace(day=1)
            start     = cur_start - relativedelta(months=1)
            end       = cur_start - relativedelta(days=1)
        elif date_filter == 'quarter':
            q_month   = ((today.month - 1) // 3) * 3 + 1
            cur_start = today.replace(month=q_month, day=1)
            start     = cur_start - relativedelta(months=3)
            end       = cur_start - relativedelta(days=1)
        elif date_filter == 'year':
            cur_start = today.replace(month=1, day=1)
            start     = cur_start - relativedelta(years=1)
            end       = cur_start - relativedelta(days=1)

        if start and end:
            return [(date_field, '>=', start), (date_field, '<=', end)]
        return []

    # =========================================================================
    # Item-type data methods
    # =========================================================================
    def _item_kpi(self, item, domain, params):
        Model = self.env[item.model_name]
        value = self._aggregate(Model, domain, item.measure_field, item.measure_operator)

        prev_value = 0
        growth     = 0
        if item.compare_period:
            prev_domain = self._expand_domain(item.domain or '[]', item) \
                          + self._prev_period_domain(item, params)
            prev_value  = self._aggregate(Model, prev_domain, item.measure_field, item.measure_operator)
            if prev_value:
                growth = round((value - prev_value) / prev_value * 100, 2)
            elif value:
                growth = 100.0

        target_progress = 0
        if item.has_target and item.target_value:
            target_progress = min(round(value / item.target_value * 100, 1), 100)

        return {
            'value':           value,
            'prev_value':      prev_value,
            'growth':          growth,
            'target_progress': target_progress,
            'formatted':       self._format_number(value, item),
        }

    def _item_chart(self, item, domain):
        if not item.group_by_field:
            return {'labels': [], 'datasets': []}

        Model    = self.env[item.model_name]
        measure  = item.measure_field or 'id'
        operator = item.measure_operator or 'sum'
        groupby  = item.group_by_field
        order    = f'{measure}:{operator} {"DESC" if item.sort_order == "desc" else "ASC"}'
        limit    = item.record_limit or 10

        try:
            rows = Model._read_group(
                domain, [groupby], [f'{measure}:{operator}'],
                order=order, limit=limit
            )
        except Exception as e:
            _logger.warning("Chart read_group error: %s", e)
            return {'labels': [], 'datasets': []}

        labels  = []
        dataset = []
        for row in rows:
            grp  = row[0]
            val  = row[1]
            lbl  = grp.display_name if hasattr(grp, 'display_name') else str(grp) if grp else 'Unknown'
            labels.append(lbl)
            dataset.append(val)

        palette = PALETTES.get(item.chart_color_palette, PALETTES['default'])
        colors  = (palette * ((len(dataset) // len(palette)) + 1))[:len(dataset)]

        return {
            'labels':       labels,
            'datasets':     [{'label': item.name, 'data': dataset, 'backgroundColor': colors}],
            'chart_type':   item.chart_type,
            'drill_model':  item.model_name,
            'drill_field':  item.group_by_field,
        }

    def _item_list(self, item, domain):
        Model = self.env[item.model_name]
        try:
            fields_list = json.loads(item.list_fields or '[]')
        except Exception:
            fields_list = []

        # Ensure at least some useful fields
        if not fields_list:
            all_fields = list(Model._fields.keys())
            fields_list = [f for f in ['name', 'display_name'] if f in all_fields][:2]

        sort_field = item.sort_by or 'id'
        sort_dir   = item.sort_order or 'desc'
        order_str  = f'{sort_field} {sort_dir}'

        try:
            records = Model.search_read(
                domain, fields_list,
                limit=item.record_limit or 20,
                order=order_str
            )
            # Flatten many2one tuples
            for rec in records:
                for k, v in rec.items():
                    if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int):
                        rec[k] = v[1]
        except Exception as e:
            _logger.warning("List query error: %s", e)
            records = []

        return {'records': records, 'fields': fields_list}

    def _item_gauge(self, item, domain, params):
        kpi = self._item_kpi(item, domain, params)
        return {**kpi, 'target': item.target_value, 'target_label': item.target_label}

    # =========================================================================
    # Aggregation helper
    # =========================================================================
    def _aggregate(self, Model, domain, field, operator):
        if operator == 'count':
            return Model.search_count(domain)
        elif operator in ('sum', 'avg', 'min', 'max'):
            field = field or 'id'
            try:
                rows = Model._read_group(domain, [], [f'{field}:{operator}'])
                return rows[0][0] if rows else 0
            except Exception:
                return 0
        return 0

    # =========================================================================
    # AI Methods
    # =========================================================================
    @api.model
    def ai_generate_dashboard(self, prompt):
        """Use the configured AI provider to auto-create a dashboard layout."""
        api_key  = self.env['ir.config_parameter'].sudo().get_param(
            'advanced_sales_dashboard.ai_api_key', ''
        )
        provider = self.env.company.dashboard_ai_provider or 'gemini'
        if not api_key:
            return {
                'error': True,
                'message': _('No AI API key configured. Please set it in Settings → Advanced Dashboard.')
            }
        return self._call_ai(provider, api_key, self._build_dashboard_prompt(prompt))

    @api.model
    def ai_generate_item(self, prompt, keywords=''):
        """Ask AI to suggest item configuration based on keywords."""
        api_key  = self.env['ir.config_parameter'].sudo().get_param(
            'advanced_sales_dashboard.ai_api_key', ''
        )
        provider = self.env.company.dashboard_ai_provider or 'gemini'
        if not api_key:
            return {'error': True, 'message': _('No AI API key configured.')}
        full_prompt = f"Keywords: {keywords}\n\n{prompt}"
        return self._call_ai(provider, api_key, self._build_item_prompt(full_prompt))

    @api.model
    def ai_extract_chart_insights(self, item_id, chart_data):
        """Ask AI to analyse chart data and return plain-text insights."""
        api_key  = self.env['ir.config_parameter'].sudo().get_param(
            'advanced_sales_dashboard.ai_api_key', ''
        )
        provider = self.env.company.dashboard_ai_provider or 'gemini'
        if not api_key:
            return {'error': True, 'message': _('No AI API key configured.')}

        item   = self.env['dashboard.item'].browse(item_id)
        prompt = (
            f"You are a business data analyst. Analyse the following dashboard chart data "
            f"for the metric '{item.name}' and provide 3 concise bullet-point insights. "
            f"Data: {json.dumps(chart_data, default=str)}"
        )
        result = self._call_ai(provider, api_key, prompt)
        if not result.get('error') and result.get('text'):
            item.sudo().ai_insights = result['text']
        return result

    def _build_dashboard_prompt(self, user_prompt):
        return (
            "You are an Odoo business analyst. A user wants to create a sales analytics dashboard. "
            "Based on their request below, describe 4-6 dashboard tiles in plain English. "
            "For each tile specify: type (kpi/chart/list/gauge/todo/note), title, metric, and chart type if applicable. "
            "Be concise. Format as a numbered list.\n\n"
            f"User request: {user_prompt}"
        )

    def _build_item_prompt(self, user_prompt):
        return (
            "You are an Odoo business analyst. Suggest a single dashboard tile configuration. "
            "Specify: title, item type (kpi/chart/list/gauge), Odoo model name, "
            "measure field, group-by field if chart, and chart type. "
            "Be concise.\n\n"
            f"User request: {user_prompt}"
        )

    def _call_ai(self, provider, api_key, prompt):
        """Make an HTTP request to the AI provider. Returns {'text': ...} or {'error': True, 'message': ...}."""
        try:
            if provider == 'gemini':
                return self._call_gemini(api_key, prompt)
            else:
                return self._call_openai(api_key, prompt)
        except Exception as e:
            _logger.error("AI call failed: %s", e)
            return {'error': True, 'message': str(e)}

    def _call_gemini(self, api_key, prompt):
        url  = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash-latest:generateContent?key={api_key}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode('utf-8')
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data    = json.loads(resp.read())
            text    = data['candidates'][0]['content']['parts'][0]['text']
        return {'text': text}

    def _call_openai(self, api_key, prompt):
        url     = "https://api.openai.com/v1/chat/completions"
        payload = json.dumps({
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
        }).encode('utf-8')
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data['choices'][0]['message']['content']
        return {'text': text}

    # =========================================================================
    # Number formatting helpers (called from frontend via controller)
    # =========================================================================
    @api.model
    def _format_number(self, value, item=None):
        ns = (item.number_system if item else None) or \
             self.env.company.dashboard_number_system or 'standard'
        if ns == 'abbreviated':
            if value >= 1_000_000_000:
                return f'{value/1_000_000_000:.2f}B'
            if value >= 1_000_000:
                return f'{value/1_000_000:.2f}M'
            if value >= 1_000:
                return f'{value/1_000:.2f}K'
            return f'{value:.2f}'
        if ns == 'indian':
            # Indian number system formatting
            s = f'{value:,.2f}'
            # simple approximation, actual Indian formatting done in JS
            return s
        return f'{value:,.2f}'

    # =========================================================================
    # Public wrappers for JS orm.call (private methods are RPC-blocked in Odoo 17+)
    # =========================================================================
    @api.model
    def get_available_filters(self):
        """Public alias — JS cannot call underscore-prefixed methods via orm.call."""
        return self._get_available_filters()

    # =========================================================================
    # Legacy helper methods (kept for backward compat)
    # =========================================================================
    def _generate_insights(self, kpi, top_performers):
        growth = kpi.get('revenue_growth', 0)
        top_sp = (
            top_performers['salespersons'][0]['name']
            if top_performers.get('salespersons') else 'the team'
        )
        if growth > 0:
            return (f"Great job! Revenue is up {growth}% compared to the previous "
                    f"period. {top_sp} is currently leading sales.")
        elif growth < 0:
            return (f"Notice: Revenue has dropped by {abs(growth)}% compared to "
                    f"the previous period. Consider checking in with {top_sp} for "
                    f"potential opportunities.")
        return f"Revenue is holding steady. {top_sp} is putting in solid effort this period."

    def _get_available_filters(self):
        users = self.env['res.users'].search_read([('share', '=', False)], ['id', 'name'])
        teams = self.env['crm.team'].search_read([], ['id', 'name']) \
            if 'crm.team' in self.env else []
        companies = self.env['res.company'].search_read([], ['id', 'name'])
        currencies = self.env['res.currency'].search_read(
            [('active', '=', True)], ['id', 'name', 'symbol']
        )
        return {
            'users': users, 'teams': teams,
            'companies': companies, 'currencies': currencies,
        }

    def _get_kpi_data(self, domain_current, domain_previous):
        SaleOrder = self.env['sale.order']
        current_orders  = SaleOrder.search(domain_current)
        current_revenue = sum(current_orders.mapped('amount_untaxed'))
        current_count   = len(current_orders)
        current_aov     = current_revenue / current_count if current_count else 0

        prev_orders  = SaleOrder.search(domain_previous)
        prev_revenue = sum(prev_orders.mapped('amount_untaxed'))
        prev_count   = len(prev_orders)

        revenue_growth = (
            round((current_revenue - prev_revenue) / prev_revenue * 100, 2)
            if prev_revenue else (100.0 if current_revenue else 0)
        )
        order_growth = (
            round((current_count - prev_count) / prev_count * 100, 2)
            if prev_count else (100.0 if current_count else 0)
        )

        all_quotes    = SaleOrder.search([])
        confirmed     = SaleOrder.search([('state', 'in', ['sale', 'done'])])
        conversion    = round(len(confirmed) / len(all_quotes) * 100, 2) if all_quotes else 0

        target          = self.env.company.monthly_sales_target or 1
        target_progress = min(round(current_revenue / target * 100, 1), 100) if target else 0

        return {
            'revenue': current_revenue, 'revenue_growth': revenue_growth,
            'orders': current_count, 'orders_growth': order_growth,
            'aov': round(current_aov, 2), 'conversion_rate': conversion,
            'currency_symbol': self.env.company.currency_id.symbol,
            'target': target, 'target_progress': target_progress,
        }

    def _get_chart_data(self, domain, date_filter):
        SaleOrder = self.env['sale.order']
        OrderLine = self.env['sale.order.line']

        groupby = 'date_order:day' if date_filter in ('today', 'week') else 'date_order:month'
        revenue_trend_data = SaleOrder._read_group(domain, [groupby], ['amount_untaxed:sum'])
        revenue_labels     = [str(r[0]) for r in revenue_trend_data]
        revenue_dataset    = [r[1] for r in revenue_trend_data]

        line_domain = []
        for d in domain:
            if isinstance(d, tuple) and len(d) == 3:
                f = d[0]
                line_domain.append((f'order_id.{f}' if not f.startswith('order_id.') else f, d[1], d[2]))
            else:
                line_domain.append(d)

        product_sales   = OrderLine._read_group(
            line_domain, ['product_id'], ['price_subtotal:sum'],
            order='price_subtotal:sum DESC', limit=10
        )
        product_labels  = [r[0].display_name if r[0] else 'Unknown' for r in product_sales]
        product_dataset = [r[1] for r in product_sales]

        partner_sales   = SaleOrder._read_group(domain, ['partner_id'], ['amount_untaxed:sum'])
        country_totals  = {}
        for partner, total in partner_sales:
            cname = partner.country_id.name if partner and partner.country_id else 'Unknown'
            country_totals[cname] = country_totals.get(cname, 0) + total
        sorted_c      = sorted(country_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        country_labels  = [c[0] for c in sorted_c]
        country_dataset = [c[1] for c in sorted_c]

        return {
            'revenue_trend': {'labels': revenue_labels, 'data': revenue_dataset},
            'products':      {'labels': product_labels, 'data': product_dataset},
            'regions':       {'labels': country_labels, 'data': country_dataset},
        }

    def _get_top_performers(self, domain):
        SaleOrder   = self.env['sale.order']
        salespersons = SaleOrder._read_group(
            domain, ['user_id'], ['amount_untaxed:sum'],
            order='amount_untaxed:sum DESC', limit=5
        )
        customers    = SaleOrder._read_group(
            domain, ['partner_id'], ['amount_untaxed:sum'],
            order='amount_untaxed:sum DESC', limit=5
        )
        return {
            'salespersons': [{'name': r[0].name if r[0] else 'None', 'revenue': r[1]} for r in salespersons],
            'customers':    [{'name': r[0].name if r[0] else 'None', 'revenue': r[1]} for r in customers],
        }

    def _get_recent_orders(self, domain):
        orders = self.env['sale.order'].search_read(
            domain, ['name', 'partner_id', 'user_id', 'amount_total', 'state', 'date_order'],
            limit=20, order='date_order DESC'
        )
        for o in orders:
            o['partner_id'] = o['partner_id'][1] if o['partner_id'] else ''
            o['user_id']    = o['user_id'][1]    if o['user_id']    else ''
            if o.get('date_order'):
                o['date_order'] = str(o['date_order'])
        return orders

    @api.model
    def _cron_send_weekly_report(self):
        data       = self.get_dashboard_data(date_filter='week')
        date_range = f"Previous 7 Days ({fields.Date.context_today(self)})"
        template   = self.env.ref(
            'advanced_sales_dashboard.email_template_advanced_sales_dashboard_weekly',
            raise_if_not_found=False
        )
        if not template:
            return False
        group_manager = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
        if not group_manager:
            return False
        emails = ",".join(u.email for u in group_manager.users if u.email)
        if not emails:
            return False
        template.with_context(data=data, date_range=date_range).send_mail(
            self.env.company.id, force_send=True, email_values={'email_to': emails}
        )
        return True
