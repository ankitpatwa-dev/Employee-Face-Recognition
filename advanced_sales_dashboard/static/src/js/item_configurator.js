/** @odoo-module **/
/**
 * ItemConfigurator — slide-in panel for creating/editing dashboard tiles
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const ITEM_TYPES  = [
    { value: "kpi",   label: "KPI Card" },
    { value: "chart", label: "Chart" },
    { value: "list",  label: "List View" },
    { value: "gauge", label: "Gauge / Target" },
    { value: "todo",  label: "To-Do List" },
    { value: "note",  label: "Note" },
];

const CHART_TYPES = [
    { value: "line",          label: "Line" },
    { value: "bar",           label: "Bar" },
    { value: "doughnut",      label: "Doughnut" },
    { value: "pie",           label: "Pie" },
    { value: "radar",         label: "Radar" },
    { value: "polarArea",     label: "Polar Area" },
    { value: "horizontalBar", label: "Horizontal Bar" },
];

const DATE_FILTERS = [
    { value: "none",    label: "No Date Filter" },
    { value: "today",   label: "Today" },
    { value: "week",    label: "This Week" },
    { value: "month",   label: "This Month" },
    { value: "quarter", label: "This Quarter" },
    { value: "year",    label: "This Year" },
    { value: "custom",  label: "Custom Range" },
];

const MEASURE_OPS = [
    { value: "sum",   label: "Sum" },
    { value: "count", label: "Count" },
    { value: "avg",   label: "Average" },
    { value: "min",   label: "Minimum" },
    { value: "max",   label: "Maximum" },
];

const COLORS = [
    { value: "primary",  hex: "#6d28d9" },
    { value: "success",  hex: "#10b981" },
    { value: "warning",  hex: "#f59e0b" },
    { value: "danger",   hex: "#ef4444" },
    { value: "info",     hex: "#3b82f6" },
    { value: "purple",   hex: "#8b5cf6" },
    { value: "pink",     hex: "#ec4899" },
    { value: "teal",     hex: "#14b8a6" },
    { value: "indigo",   hex: "#4f46e5" },
    { value: "dark",     hex: "#1f2937" },
];

const PALETTES = [
    { value: "default",    label: "Default" },
    { value: "blues",      label: "Blues" },
    { value: "greens",     label: "Greens" },
    { value: "warm",       label: "Warm" },
    { value: "cool",       label: "Cool" },
    { value: "monochrome", label: "Monochrome" },
    { value: "pastel",     label: "Pastel" },
];

const NUMBER_SYSTEMS = [
    { value: "standard",    label: "Standard (1,000,000)" },
    { value: "indian",      label: "Indian (10,00,000)" },
    { value: "abbreviated", label: "Short (1M / 1K)" },
];

const UNIT_TYPES = [
    { value: "number",     label: "Number" },
    { value: "monetary",   label: "Monetary" },
    { value: "percentage", label: "Percentage (%)" },
    { value: "custom",     label: "Custom" },
];

const DEFAULT_ITEM = {
    name:             "New Tile",
    item_type:        "kpi",
    model_name:       "sale.order",
    domain:           "[]",
    filter_date_field:"date_order",
    date_filter:      "month",
    date_start:       "",
    date_end:         "",
    measure_field:    "amount_untaxed",
    measure_operator: "sum",
    group_by_field:   "",
    sort_by:          "",
    sort_order:       "desc",
    record_limit:     10,
    compare_period:   false,
    chart_type:       "bar",
    chart_color_palette: "default",
    show_data_values: false,
    show_legend:      true,
    fill_area:        true,
    smooth_line:      true,
    color_theme:      "primary",
    icon:             "fa-bar-chart",
    unit_type:        "number",
    custom_unit:      "",
    currency_id:      false,
    has_target:       false,
    target_value:     0,
    target_label:     "Target",
    number_system:    "standard",
    list_style:       "compact",
    list_fields:      "[]",
    todo_items:       "[]",
    note_content:     "",
    note_bg_color:    "#fff9c4",
    grid_w:           4,
    grid_h:           3,
    ai_keywords:      "",
};

export class ItemConfigurator extends Component {
    static template  = "advanced_sales_dashboard.ItemConfigurator";
    static props     = ["open", "boardId", "itemId", "onSave", "onClose", "onDelete"];

    setup() {
        this.orm       = useService("orm");
        this.notification = useService("notification");

        this.itemTypes    = ITEM_TYPES;
        this.chartTypes   = CHART_TYPES;
        this.dateFilters  = DATE_FILTERS;
        this.measureOps   = MEASURE_OPS;
        this.colors       = COLORS;
        this.palettes     = PALETTES;
        this.numberSystems = NUMBER_SYSTEMS;
        this.unitTypes    = UNIT_TYPES;

        this.state = useState({
            form:     { ...DEFAULT_ITEM },
            saving:   false,
            modelFields: [],
            currencies:  [],
        });

        onWillStart(async () => {
            await this._loadMeta();
            if (this.props.itemId) {
                await this._loadItem();
            }
        });
    }

    async onWillUpdateProps(nextProps) {
        if (nextProps.itemId !== this.props.itemId) {
            if (nextProps.itemId) {
                await this._loadItem(nextProps.itemId);
            } else {
                this.state.form = { ...DEFAULT_ITEM };
            }
        }
    }

    async _loadMeta() {
        try {
            const filters = await this.orm.call(
                "advanced.sales.dashboard", "get_available_filters", []
            );
            this.state.currencies = filters.currencies || [];
        } catch (_) {}
    }

    async _loadItem(idOverride) {
        const id = idOverride || this.props.itemId;
        if (!id) return;
        try {
            const item = await this.orm.read("dashboard.item", [id], Object.keys(DEFAULT_ITEM));
            if (item?.[0]) {
                const rec = item[0];
                // Flatten many2one
                if (Array.isArray(rec.currency_id)) rec.currency_id = rec.currency_id[0];
                this.state.form = { ...DEFAULT_ITEM, ...rec };
            }
        } catch (_) {}
    }

    async _loadModelFields() {
        const model = this.state.form.model_name;
        if (!model) return;
        try {
            const res = await this.orm.call(
                "advanced.sales.dashboard", "get_model_fields",
                [model]
            );
            this.state.modelFields = Array.isArray(res) ? res : [];
        } catch (_) {}
    }

    onModelChange(evt) {
        this.state.form.model_name = evt.target.value;
        this._loadModelFields();
    }

    // =========================================================================
    // Save / Delete
    // =========================================================================
    async save() {
        this.state.saving = true;
        try {
            const form  = this.state.form;
            const vals  = { ...form };
            if (vals.currency_id === "") vals.currency_id = false;
            if (vals.date_start === "") vals.date_start = false;
            if (vals.date_end === "") vals.date_end = false;

            if (this.props.itemId) {
                await this.orm.call("dashboard.item", "write", [[this.props.itemId], vals]);
            } else {
                vals.board_id = this.props.boardId;
                await this.orm.call("dashboard.item", "create", [vals]);
            }
            this.notification.add("Tile saved!", { type: "success" });
            this.props.onSave();
        } catch (e) {
            this.notification.add(e?.data?.message || "Save failed", { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async deleteItem() {
        if (!this.props.itemId) return;
        if (!window.confirm("Delete this tile?")) return;
        await this.orm.call("dashboard.item", "unlink", [[this.props.itemId]]);
        this.notification.add("Tile deleted", { type: "info" });
        this.props.onDelete();
    }

    set(key, evt)     { this.state.form[key] = evt.target.value; }
    setCheck(key, evt){ this.state.form[key] = evt.target.checked; }
    setNum(key, evt)  { this.state.form[key] = Number(evt.target.value); }
    setColor(val)     { this.state.form.color_theme = val; }
    close()           { this.props.onClose(); }

    get isNew() { return !this.props.itemId; }
    get itemType() { return this.state.form.item_type; }
    get isChart()  { return this.itemType === "chart"; }
    get isKPIOrGauge() { return ["kpi","gauge"].includes(this.itemType); }
    get isData()   { return !["todo","note"].includes(this.itemType); }
    get isCustomDate() { return this.state.form.date_filter === "custom"; }
    get isCustomUnit() { return this.state.form.unit_type === "custom"; }
    get isMonetary()   { return this.state.form.unit_type === "monetary"; }
}
