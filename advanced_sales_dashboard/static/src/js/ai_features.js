/** @odoo-module **/
/**
 * AI Features — dialog for AI dashboard generation, item generation, and chart insights
 */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AIDialog extends Component {
    static template = "advanced_sales_dashboard.AIDialog";
    static props    = ["open", "mode", "boardId", "onClose", "onApply"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            prompt:   "",
            keywords: "",
            loading:  false,
            result:   null,
            error:    null,
        });
    }

    async sendPrompt() {
        const prompt = this.state.prompt.trim();
        if (!prompt) return;
        this.state.loading = true;
        this.state.result  = null;
        this.state.error   = null;
        try {
            let res;
            if (this.props.mode === "dashboard") {
                res = await this.orm.call("advanced.sales.dashboard", "ai_generate_dashboard", [prompt]);
            } else {
                res = await this.orm.call("advanced.sales.dashboard", "ai_generate_item", [prompt, this.state.keywords]);
            }
            if (res.error) {
                this.state.error = res.message || "AI error";
            } else {
                this.state.result = res.text || "No response";
            }
        } catch (e) {
            this.state.error = e?.data?.message || e?.message || "Request failed";
        } finally {
            this.state.loading = false;
        }
    }

    apply() {
        this.props.onApply(this.state.result, this.props.mode);
        this.close();
    }

    close() {
        this.state.prompt   = "";
        this.state.keywords = "";
        this.state.result   = null;
        this.state.error    = null;
        this.state.loading  = false;
        this.props.onClose();
    }

    get modeLabel() {
        return this.props.mode === "dashboard"
            ? "Generate Complete Dashboard with AI"
            : "Generate Dashboard Item with AI";
    }

    get modeSubtitle() {
        return this.props.mode === "dashboard"
            ? "Describe the dashboard you want. AI will suggest tiles and layout."
            : "Describe the metric or insight you want to visualise.";
    }

    get promptPlaceholder() {
        return this.props.mode === "dashboard"
            ? 'e.g. "Sales executive dashboard with monthly revenue, top 5 products, and regional breakdown"'
            : 'e.g. "Bar chart showing top 10 customers by revenue this quarter"';
    }
}

/**
 * DateRangeFilter — date picker bar for the dashboard header
 */
export class DateRangeFilter extends Component {
    static template = "advanced_sales_dashboard.DateRangeFilter";
    static props    = ["value", "dateStart", "dateEnd", "onChange"];

    setup() {
        this.state = useState({
            filter: this.props.value || "",
            start:  this.props.dateStart || "",
            end:    this.props.dateEnd   || "",
        });
        this.options = [
            { value: "",        label: "Per-Item" },
            { value: "today",   label: "Today" },
            { value: "week",    label: "This Week" },
            { value: "month",   label: "This Month" },
            { value: "quarter", label: "This Quarter" },
            { value: "year",    label: "This Year" },
            { value: "custom",  label: "Custom..." },
        ];
    }

    onFilterChange(evt) {
        this.state.filter = evt.target.value;
        if (this.state.filter !== "custom") {
            this._emit();
        }
    }

    onStartChange(evt) {
        this.state.start = evt.target.value;
        this._emit();
    }

    onEndChange(evt) {
        this.state.end = evt.target.value;
        this._emit();
    }

    _emit() {
        this.props.onChange(this.state.filter, this.state.start, this.state.end);
    }

    get isCustom() { return this.state.filter === "custom"; }
}
