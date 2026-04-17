/** @odoo-module **/
/**
 * DashboardItem — renders any tile type and manages its own data lifecycle
 * Types: kpi, chart, list, gauge, todo, note
 */

import { Component, useState, onWillStart, onMounted, useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { downloadItem } from "./download_utils";

// ── Chart color palettes ───────────────────────────────────────────────────
const PALETTES = {
    default:    ['#6d28d9','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6'],
    blues:      ['#003f88','#00509d','#0077b6','#0096c7','#00b4d8','#48cae4','#90e0ef','#ade8f4'],
    greens:     ['#1b4332','#2d6a4f','#40916c','#52b788','#74c69d','#95d5b2','#b7e4c7','#d8f3dc'],
    warm:       ['#d62828','#f77f00','#fcbf49','#e76f51','#f4a261','#e9c46a','#264653','#2a9d8f'],
    cool:       ['#03045e','#023e8a','#0077b6','#0096c7','#48cae4','#ade8f4','#caf0f8','#90e0ef'],
    monochrome: ['#212529','#343a40','#495057','#6c757d','#adb5bd','#ced4da','#dee2e6','#e9ecef'],
    pastel:     ['#ffadad','#ffd6a5','#fdffb6','#caffbf','#9bf6ff','#a0c4ff','#bdb2ff','#ffc6ff'],
};

// ── Color theme CSS variable map ───────────────────────────────────────────
const COLOR_VARS = {
    primary: '#6d28d9', success: '#10b981', warning: '#f59e0b',
    danger: '#ef4444', info: '#3b82f6', purple: '#8b5cf6',
    pink: '#ec4899', indigo: '#4f46e5', teal: '#14b8a6', dark: '#1f2937',
};

export class DashboardItem extends Component {
    static template = "advanced_sales_dashboard.Item";
    static props    = ["config", "editMode", "globalDateFilter", "globalDateStart", "globalDateEnd",
                       "refreshTrigger", "onEdit", "onDelete"];

    setup() {
        this.orm           = useService("orm");
        this.actionService = useService("action");
        this.notification  = useService("notification");
        this.chartRef      = useRef("chartCanvas");
        this._chartInst    = null;

        this.state = useState({
            loading:    true,
            data:       null,
            error:      null,
            // drill-down breadcrumb
            drillStack: [],  // [{label, domain}]
            // ai insights display
            showAIInsights: false,
            aiLoading: false,
            aiText:    "",
            // list view style toggle
            listStyle: this.props.config.list_style || "compact",
        });

        onWillStart(() => this.fetchData());
        onMounted(() => {
            if (!this.state.loading && this.props.config.item_type === "chart") {
                this._renderChart();
            }
        });

        // ── useEffect: watch refreshTrigger + date filters ──────────────────
        // OWL 2's idiomatic way to react to prop changes. Runs after mount
        // AND after every render where any dependency value changes.
        // We skip the very first call because onWillStart already fetched data.
        this._effectMounted = false;
        useEffect(
            () => {
                if (!this._effectMounted) {
                    // First call = initial mount — onWillStart already handled it
                    this._effectMounted = true;
                    return;
                }
                console.log(
                    `[DashboardItem] refresh triggered — id=${this.props.config.id}`,
                    `trigger=${this.props.refreshTrigger}`
                );
                this.fetchData();
            },
            () => [
                this.props.refreshTrigger,
                this.props.globalDateFilter,
                this.props.globalDateStart,
                this.props.globalDateEnd,
            ]
        );
    }


    // =========================================================================
    // Data fetching
    // =========================================================================
    async fetchData(propsOverride) {
        const p = propsOverride || this.props;
        this.state.loading = true;
        this.state.error   = null;
        try {
            const drill = this.state.drillStack.length
                ? this.state.drillStack[this.state.drillStack.length - 1].domain
                : null;

            const params = {
                date_filter: p.globalDateFilter || undefined,
                date_start:  p.globalDateStart  || undefined,
                date_end:    p.globalDateEnd     || undefined,
                drill_domain: drill ? JSON.stringify(drill) : undefined,
            };
            const data = await this.orm.call(
                "advanced.sales.dashboard", "get_item_data",
                [this.props.config.id], params
            );
            this.state.data = data;
        } catch (e) {
            this.state.error = e?.data?.message || "Data load failed";
        } finally {
            this.state.loading = false;
            if (this.props.config.item_type === "chart") {
                setTimeout(() => this._renderChart(), 50);
            }
        }
    }

    // =========================================================================
    // Chart rendering
    // =========================================================================
    _renderChart() {
        if (typeof Chart === "undefined") return;
        const canvas = this.chartRef?.el;
        if (!canvas || !this.state.data) return;

        if (this._chartInst) { this._chartInst.destroy(); this._chartInst = null; }

        const cfg   = this.props.config;
        const d     = this.state.data;
        const type  = cfg.chart_type || "bar";
        const palette = PALETTES[cfg.chart_color_palette || "default"];
        const _n      = d.datasets?.[0]?.data?.length || 1;
        const colors  = d.datasets?.[0]?.backgroundColor ||
            Array.from({ length: _n }, (_, i) => palette[i % palette.length]);

        // Normalize chart type for Chart.js v3+
        const chartType = type === "horizontalBar" ? "bar" : type;
        const indexAxis = type === "horizontalBar" ? "y"  : "x";

        const datasets = (d.datasets || []).map(ds => ({
            label:           ds.label || cfg.name,
            data:            ds.data  || [],
            backgroundColor: ds.backgroundColor || colors,
            borderColor:     type === "line" ? (palette[0] || "#6d28d9") : undefined,
            borderWidth:     type === "line" ? 2 : 0,
            fill:            cfg.fill_area && type === "line",
            tension:         cfg.smooth_line ? 0.4 : 0,
            borderRadius:    type === "bar" ? 6 : undefined,
        }));

        this._chartInst = new Chart(canvas, {
            type: chartType,
            data: { labels: d.labels || [], datasets },
            options: {
                indexAxis,
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 600, easing: "easeInOutQuart" },
                plugins: {
                    legend: { display: cfg.show_legend },
                    datalabels: cfg.show_data_values ? {
                        display: true, color: "#fff", font: { weight: "bold", size: 11 }
                    } : { display: false },
                    tooltip: { mode: "index", intersect: false },
                },
                scales: (type === "doughnut" || type === "pie" || type === "polarArea") ? {} : {
                    y: { beginAtZero: true, grid: { color: "rgba(128,128,128,.08)" } },
                    x: { grid: { display: false } },
                },
                onClick: (evt, elements) => this._handleChartClick(elements, d),
            },
        });
    }

    _handleChartClick(elements, data) {
        if (!elements.length) return;
        const idx   = elements[0].index;
        const label = data.labels?.[idx];
        if (!label || !data.drill_field) return;

        const domain = [[data.drill_field, "=", label]];
        this.state.drillStack.push({ label, domain });
        this.fetchData();
    }

    drillUp() {
        if (!this.state.drillStack.length) return;
        this.state.drillStack.pop();
        this.fetchData();
    }

    // =========================================================================
    // Gauge SVG rendering (returns SVG attributes for template)
    // =========================================================================
    get gaugeAttrs() {
        const d       = this.state.data || {};
        const val     = d.value || 0;
        const target  = d.target || this.props.config.target_value || 1;
        const pct     = Math.min(val / target, 1);
        const radius  = 54;
        const circ    = 2 * Math.PI * radius;
        const dash    = pct * circ;
        return { pct: Math.round(pct * 100), dash: `${dash} ${circ}`, circ };
    }

    // =========================================================================
    // Number formatting
    // =========================================================================
    formatValue(val) {
        const ns  = this.props.config.number_system || "standard";
        const num = Number(val) || 0;
        if (ns === "abbreviated") {
            if (num >= 1e9)  return (num / 1e9).toFixed(2)  + "B";
            if (num >= 1e6)  return (num / 1e6).toFixed(2)  + "M";
            if (num >= 1e3)  return (num / 1e3).toFixed(2)  + "K";
            return num.toFixed(2);
        }
        if (ns === "indian") {
            return this._indianFormat(num);
        }
        return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    _indianFormat(num) {
        const s = Math.abs(num).toFixed(2).split(".");
        let int = s[0];
        if (int.length > 3) {
            const last3 = int.slice(-3);
            const rest  = int.slice(0, -3);
            int = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + last3;
        }
        return (num < 0 ? "-" : "") + int + "." + s[1];
    }

    formatDisplay(val) {
        const cfg     = this.props.config;
        const fmtd    = this.formatValue(val);
        if (cfg.unit_type === "monetary") return `${cfg.currency_symbol || ""}${fmtd}`;
        if (cfg.unit_type === "percentage") return `${fmtd}%`;
        if (cfg.unit_type === "custom") return `${fmtd} ${cfg.custom_unit || ""}`;
        return fmtd;
    }

    // =========================================================================
    // Actions
    // =========================================================================
    editItem()   { this.props.onEdit(this.props.config.id); }
    deleteItem() { this.props.onDelete(this.props.config.id); }

    openFullView() {
        // Navigate to sale.order list filtered by item domain
        const cfg = this.props.config;
        if (!cfg.model_name) return;
        this.actionService.doAction({
            type:      "ir.actions.act_window",
            name:      cfg.name,
            res_model: cfg.model_name,
            view_mode: "list,form",
            views:     [[false, "list"], [false, "form"]],
            target:    "current",
        });
    }

    // =========================================================================
    // Download helpers
    // =========================================================================
    downloadCSV()   { downloadItem(this.props.config, this.state.data, "csv"); }
    downloadExcel() { downloadItem(this.props.config, this.state.data, "excel"); }
    downloadPDF()   { downloadItem(this.props.config, this.state.data, "pdf"); }
    downloadPNG()   {
        const el = this.chartRef?.el;
        if (el) {
            const a    = document.createElement("a");
            a.href     = el.toDataURL("image/png");
            a.download = `${this.props.config.name || "chart"}.png`;
            a.click();
        }
    }

    // =========================================================================
    // AI Insights
    // =========================================================================
    async loadAIInsights() {
        if (this.state.aiLoading) return;
        this.state.showAIInsights = true;
        this.state.aiLoading      = true;
        this.state.aiText         = "";
        try {
            const res = await this.orm.call(
                "advanced.sales.dashboard", "ai_extract_chart_insights",
                [this.props.config.id, this.state.data || {}]
            );
            this.state.aiText = res.text || res.message || "No insights available.";
        } catch (e) {
            this.state.aiText = "AI insight failed: " + (e?.data?.message || e?.message || "Unknown error");
        } finally {
            this.state.aiLoading = false;
        }
    }

    // =========================================================================
    // To-Do
    // =========================================================================
    get todoItems() {
        try { return JSON.parse(this.props.config.todo_items || "[]"); }
        catch (_) { return []; }
    }

    get todoItemsState() {
        if (this.state.data?.todo_items !== undefined) return this.state.data.todo_items;
        return this.todoItems;
    }

    async toggleTodo(idx) {
        const res = await this.orm.call("dashboard.item", "toggle_todo", [[this.props.config.id], idx]);
        // Update local state
        if (this.state.data) this.state.data.todo_items = res;
    }

    async addTodo(evt) {
        const input = evt.target.previousElementSibling;
        const text  = input?.value?.trim();
        if (!text) return;
        const res   = await this.orm.call("dashboard.item", "add_todo", [[this.props.config.id], text]);
        if (this.state.data) this.state.data.todo_items = res;
        if (input) input.value = "";
    }

    async deleteTodo(idx) {
        const res = await this.orm.call("dashboard.item", "delete_todo", [[this.props.config.id], idx]);
        if (this.state.data) this.state.data.todo_items = res;
    }

    // =========================================================================
    // Note
    // =========================================================================
    async saveNote(evt) {
        const text = evt.target.value;
        await this.orm.call("dashboard.item", "write", [[this.props.config.id], { note_content: text }]);
    }

    // =========================================================================
    // List view style toggle
    // =========================================================================
    toggleListStyle() {
        this.state.listStyle = this.state.listStyle === "compact" ? "card" : "compact";
    }

    // =========================================================================
    // CSS helpers
    // =========================================================================
    get kpiColor()  { return COLOR_VARS[this.props.config.color_theme || "primary"] || "#6d28d9"; }
    get growthClass() {
        const g = this.state.data?.growth;
        if (g > 0) return "positive";
        if (g < 0) return "negative";
        return "neutral";
    }
}
