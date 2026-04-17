/** @odoo-module **/
/**
 * DashboardGrid — GridStack-based layout manager
 * Handles drag/resize of tiles and saves positions to backend
 */

import { Component, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DashboardItem } from "./dashboard_item";

export class DashboardGrid extends Component {
    static template = "advanced_sales_dashboard.Grid";
    static components = { DashboardItem };
    static props = ["board", "editMode", "globalDateFilter", "globalDateStart", "globalDateEnd",
        "refreshTrigger", "onEdit", "onDelete"];

    setup() {
        this.orm = useService("orm");
        this.gridRef = useRef("gridContainer");
        this.gsInstance = null;
        this._pendingBoardChange = false;

        onMounted(() => this._initGrid());

        // onPatched fires AFTER OWL has finished updating the DOM.
        // This is the correct place to tell GridStack about DOM changes.
        onPatched(() => this._onAfterPatch());

        onWillUnmount(() => this._destroyGrid());
    }

    // =========================================================================
    // GridStack lifecycle
    // =========================================================================
    _initGrid() {
        if (typeof GridStack === "undefined") {
            console.warn("GridStack not loaded yet — retrying in 300ms");
            setTimeout(() => this._initGrid(), 300);
            return;
        }
        const el = this.gridRef.el;
        if (!el) return;

        this.gsInstance = GridStack.init({
            column: this.props.board.layout_cols || 12,
            cellHeight: 80,
            margin: 6,
            animate: true,
            handle: '.drag-handle',          // dedicated handle — avoids conflicting with card buttons
            draggable: { cancel: 'button, input, textarea, select, .card-action-btn' },
            resizable: { handles: 'e,se,s,sw,w' },
            staticGrid: !this.props.editMode,
        }, el);

        this.gsInstance.on("dragstop resizestop", () => this._saveLayout());
    }

    _destroyGrid() {
        if (this.gsInstance) {
            this.gsInstance.destroy(false);
            this.gsInstance = null;
        }
    }

    // =========================================================================
    // Sync GridStack AFTER OWL patches the DOM
    // =========================================================================
    _onAfterPatch() {
        if (!this.gsInstance) return;

        // If the board switched, fully re-initialise
        if (this._pendingBoardChange) {
            this._pendingBoardChange = false;
            this._destroyGrid();
            this._initGrid();
            return;
        }

        // Toggle static / interactive mode
        this.gsInstance.setStatic(!this.props.editMode);

        // Re-register any items OWL may have re-created during patching
        const el = this.gridRef.el;
        if (el) {
            el.querySelectorAll('.grid-stack-item').forEach(itemEl => {
                if (!itemEl.gridstackNode) {
                    this.gsInstance.makeWidget(itemEl);
                }
            });
        }
    }

    // =========================================================================
    // Detect board change BEFORE OWL patches (flag only — no DOM work here)
    // =========================================================================
    onWillUpdateProps(nextProps) {
        if (nextProps.board?.id !== this.props.board?.id) {
            this._pendingBoardChange = true;
        }
    }

    // =========================================================================
    // Layout persistence
    // =========================================================================
    async _saveLayout() {
        if (!this.gsInstance) return;
        const nodes = this.gsInstance.engine.nodes;
        const layout = nodes
            .map(n => ({
                id: parseInt(n.el?.dataset?.itemId || 0),
                x: n.x, y: n.y, w: n.w, h: n.h,
            }))
            .filter(l => l.id);
        if (!layout.length) return;
        try {
            await this.orm.call(
                "advanced.sales.dashboard", "save_layout",
                [layout]
            );
        } catch (_) { }
    }

    // =========================================================================
    // Item edit / delete forwarded from child
    // =========================================================================
    onEditItem(itemId) { this.props.onEdit(itemId); }
    onDeleteItem(itemId) { this.props.onDelete(itemId); }
}
