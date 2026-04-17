{
    'name': 'Advanced Sales Dashboard (AI Powered)',
    'version': '18.0.2.0.1',
    'category': 'Sales/Sales',
    'summary': 'Next-gen analytics: Real-time dynamic tiles, GridStack drag-and-drop layout, Gemini/OpenAI automated insights, and extensive export options.',
    'description': """
        Transform your Odoo 18 experience with the Advanced Sales Dashboard!
        
        This module introduces a highly interactive, real-time analytics interface designed to deliver extreme flexibility. Monitor your business with a premium, drag-and-drop dashboard powered by AI.

        🚀 **KEY FEATURES:**
        - **AI-Powered Insights:** Generate dashboards, configure widgets via keyword prompts, and extract textual executive summaries directly from your charts using Gemini/OpenAI.
        - **Real-Time Data Polling:** The background Auto-Refresh engine keeps your metrics instantly up to date with smooth animated transitions.
        - **Fluid Drag & Drop Grid:** Effortlessly drag, drop, and resize your widgets with GridStack.js. Save your perfect personalized layout instantly.
        - **Extensive Export Engine:** Download individual widget data as Excel (.xlsx), CSV, PDF (jsPDF), or snapshot charts as PNG directly from the UI.
        - **6 Beautiful UI Themes:** Instantly toggle between Default, Dark, Ocean, Sunset, Forest, and Corporate themes.
        - **Advanced Data Manipulation:** Set custom targets with progress ring gauges, utilize advanced date filters, drill-down/up on charts, and apply filter macros (%UID, %COMPANY).
        
        💡 **WIDGET TYPES INCLUDED:**
        - Animated KPI Metric Cards
        - Line / Bar / Pie / Doughnut Charts
        - Customizable Gauge meters
        - Interactive To-Do list tracking
        - Compact and Card style Data Tables
        
        From a high-level executive overview to localized team performance boards, experience a premium analytics ecosystem natively built for Odoo.
    """,
    'author': 'Ankit - DevsCodespace',
    'website': 'https://devscodespace.com',
    'license': 'OPL-1',
    'images': [
        'static/description/dashboard_main.png',
        'static/description/dashboard_edit.png',
        'static/description/dashboard_configurator.png'
    ],
    'depends': [
        'base',
        'sale_management',
        'web',
        'mail',
    ],
    'data': [
        # Security FIRST
        'security/groups.xml',
        'security/ir.model.access.csv',
        # Views
        'views/dashboard_views.xml',
        'views/dashboard_board_views.xml',
        'views/res_config_settings_views.xml',
        # Reports
        'reports/dashboard_report.xml',
        # Data
        'data/mail_template.xml',
        'data/cron.xml',
        'data/predefined_dashboards.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # ── External CDN libraries ────────────────────────────────
            # Chart.js
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
            # GridStack (drag-resize tile layout)
            'https://cdn.jsdelivr.net/npm/gridstack@10.3.1/dist/gridstack-all.min.js',
            'https://cdn.jsdelivr.net/npm/gridstack@10.3.1/dist/gridstack.min.css',
            # SheetJS (Excel export)
            'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js',
            # jsPDF + autoTable (PDF export)
            'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js',
            'https://cdn.jsdelivr.net/npm/jspdf-autotable@3.8.1/dist/jspdf.plugin.autotable.min.js',
            # ── Styles ───────────────────────────────────────────────
            'advanced_sales_dashboard/static/src/scss/dashboard.scss',
            # ── OWL Components (JS) ──────────────────────────────────
            'advanced_sales_dashboard/static/src/js/download_utils.js',
            'advanced_sales_dashboard/static/src/js/ai_features.js',
            'advanced_sales_dashboard/static/src/js/item_configurator.js',
            'advanced_sales_dashboard/static/src/js/dashboard_item.js',
            'advanced_sales_dashboard/static/src/js/dashboard_grid.js',
            'advanced_sales_dashboard/static/src/js/dashboard_app.js',
            # ── OWL Templates (XML) ──────────────────────────────────
            'advanced_sales_dashboard/static/src/xml/dashboard.xml',
            'advanced_sales_dashboard/static/src/xml/dashboard_item.xml',
            'advanced_sales_dashboard/static/src/xml/item_configurator.xml',
            'advanced_sales_dashboard/static/src/xml/ai_dialog.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
