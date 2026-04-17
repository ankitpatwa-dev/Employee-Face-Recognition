/** @odoo-module **/
/**
 * Advanced Sales Dashboard — Root Application
 * Handles: board management, theme switching, real-time polling, edit mode, sidebar
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// ── Sub-component imports ──────────────────────────────────────────────────
import { DashboardGrid } from "./dashboard_grid";
import { ItemConfigurator } from "./item_configurator";
import { AIDialog } from "./ai_features";
import { DateRangeFilter } from "./ai_features";

// ── Theme color map for the swatch picker ──────────────────────────────────
const THEMES = [
    { id: 'default', color: '#6d28d9', label: 'Default' },
    { id: 'dark', color: '#1a1a2e', label: 'Dark' },
    { id: 'ocean', color: '#0ea5e9', label: 'Ocean' },
    { id: 'sunset', color: '#f97316', label: 'Sunset' },
    { id: 'forest', color: '#22c55e', label: 'Forest' },
    { id: 'corporate', color: '#1d4ed8', label: 'Corporate' },
];

export class AdvancedSalesDashboard extends Component {
    static template = "advanced_sales_dashboard.App";
    static components = { DashboardGrid, ItemConfigurator, AIDialog, DateRangeFilter };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");

        this.themes = THEMES;

        this.state = useState({
            // Board list
            boards: [],
            activeBoardId: null,
            activeBoard: null,

            // UI
            sidebarCollapsed: false,
            editMode: false,
            loading: true,
            hasError: false,
            errorMessage: "",

            // Filters (global, override per-item)
            globalDateFilter: "",  // "" = use per-item setting
            globalDateStart: "",
            globalDateEnd: "",

            // Panels
            configuratorOpen: false,
            configuratorItemId: null,
            aiDialogOpen: false,
            aiDialogMode: "dashboard",  // "dashboard" | "item" | "insights"

            // Real-time polling
            polling: false,
            refreshTrigger: 0,
        });

        // Explicitly bind callbacks passed as props to child components
        this.onGlobalDateChange = this.onGlobalDateChange.bind(this);
        this.openConfigurator = this.openConfigurator.bind(this);
        this.closeConfigurator = this.closeConfigurator.bind(this);
        this.onItemSaved = this.onItemSaved.bind(this);
        this.onItemDeleted = this.onItemDeleted.bind(this);
        this.closeAIDialog = this.closeAIDialog.bind(this);
        this.onAIApply = this.onAIApply.bind(this);

        this._pollTimer = null;
        this._autoRefreshToggling = false;
        this._boardParams = this.props.action?.params || {};

        onWillStart(async () => {
            await this._loadBoards();
        });

        onMounted(() => {
            this._startPollingIfNeeded();
        });

        onWillUnmount(() => {
            this._stopPolling();
        });
    }

    // =========================================================================
    // Board loading
    // =========================================================================
    async _loadBoards() {
        this.state.loading = true;
        try {
            const boards = await this.orm.call("dashboard.board", "get_user_boards", []);
            this.state.boards = boards;

            // Restore board from action params or use first
            const targetId = this._boardParams.board_id || (boards[0]?.id || null);
            if (targetId) {
                await this._activateBoard(targetId);
            } else {
                this.state.loading = false;
            }
        } catch (e) {
            this._onError(e, "Failed to load dashboards");
        }
    }

    async _activateBoard(boardId) {
        this.state.loading = true;
        try {
            const board = await this.orm.call("dashboard.board", "get_board_config", [[boardId]]);
            this.state.activeBoardId = boardId;
            // Use Object.assign in-place (same as _refreshBoardData) so OWL keeps
            // the same reactive reference — avoids a full grid re-init on every save/switch.
            if (this.state.activeBoard && this.state.activeBoard.id === boardId) {
                Object.assign(this.state.activeBoard, board);
            } else {
                // First load or different board — must replace the reference
                this.state.activeBoard = board;
            }
        } catch (e) {
            this._onError(e, "Failed to load board");
        } finally {
            this.state.loading = false;
        }
        this._stopPolling();
        this._startPollingIfNeeded();
    }

    // =========================================================================
    // Board CRUD
    // =========================================================================
    async createBoard() {
        const name = await this._promptName("New Dashboard name:", "New Dashboard");
        if (!name) return;
        try {
            const res = await this.orm.call("dashboard.board", "create", [{ name }]);
            await this._loadBoards();
            await this._activateBoard(res);
        } catch (e) {
            this._onError(e, "Could not create dashboard");
        }
    }

    async _promptName(msg, def) {
        /* In Odoo, we can't easily use native prompt in OWL, so use a simple browser prompt */
        return window.prompt(msg, def);
    }

    async renameBoard() {
        if (!this.state.activeBoardId) return;
        const name = await this._promptName("Rename dashboard:", this.state.activeBoard?.name || "");
        if (!name) return;
        await this.orm.call("dashboard.board", "write", [[this.state.activeBoardId], { name }]);
        this.state.activeBoard.name = name;
        // Update sidebar list
        const b = this.state.boards.find(x => x.id === this.state.activeBoardId);
        if (b) b.name = name;
    }

    async duplicateBoard() {
        if (!this.state.activeBoardId) return;
        try {
            const newId = await this.orm.call("dashboard.board", "copy", [[this.state.activeBoardId]]);
            await this._loadBoards();
            await this._activateBoard(newId);
            this.notification.add("Dashboard duplicated!", { type: "success" });
        } catch (e) {
            this._onError(e, "Could not duplicate dashboard");
        }
    }

    async deleteBoard() {
        if (!this.state.activeBoardId) return;
        this.dialogService.add(ConfirmationDialog, {
            body: "Delete this dashboard completely?",
            confirm: async () => {
                await this.orm.call("dashboard.board", "unlink", [[this.state.activeBoardId]]);
                await this._loadBoards();
            }
        });
    }

    async selectBoard(boardId) {
        if (boardId === this.state.activeBoardId) return;
        await this._activateBoard(boardId);
    }

    // =========================================================================
    // Theme
    // =========================================================================
    async setTheme(themeId) {
        if (!this.state.activeBoardId) return;
        await this.orm.call("dashboard.board", "write", [[this.state.activeBoardId], { theme: themeId }]);
        this.state.activeBoard.theme = themeId;
    }

    get themeClass() {
        return `theme-${this.state.activeBoard?.theme || 'default'}`;
    }

    // =========================================================================
    // Edit mode
    // =========================================================================
    toggleEditMode() {
        this.state.editMode = !this.state.editMode;
    }

    // =========================================================================
    // Configurator (item config panel)
    // =========================================================================
    openConfigurator(itemId) {
        this.state.configuratorItemId = itemId;
        this.state.configuratorOpen = true;
    }

    openNewItemConfigurator() {
        this.state.configuratorItemId = null;   // null = creating new
        this.state.configuratorOpen = true;
    }

    closeConfigurator() {
        this.state.configuratorOpen = false;
        this.state.configuratorItemId = null;
    }

    async onItemSaved(itemConfig) {
        this.closeConfigurator();
        // Refresh board
        await this._activateBoard(this.state.activeBoardId);
    }

    async onItemDeleted(itemId) {
        if (itemId) {
            this.dialogService.add(ConfirmationDialog, {
                body: "Delete this tile permanently?",
                confirm: async () => {
                    try {
                        await this.orm.call("dashboard.item", "unlink", [[itemId]]);
                        this.notification.add("Tile deleted", { type: "info" });
                        this.closeConfigurator();
                        await this._activateBoard(this.state.activeBoardId);
                    } catch (e) {
                        this._onError(e, "Could not delete tile");
                    }
                }
            });
            return;
        }
        this.closeConfigurator();
        await this._activateBoard(this.state.activeBoardId);
    }

    // =========================================================================
    // AI Dialog
    // =========================================================================
    openAIDialog(mode = "dashboard") {
        this.state.aiDialogMode = mode;
        this.state.aiDialogOpen = true;
    }

    closeAIDialog() {
        this.state.aiDialogOpen = false;
    }

    onAIApply(result, mode) {
        // Handle AI Application if needed
    }

    // =========================================================================
    // Real-time polling
    // =========================================================================
    _startPollingIfNeeded() {
        // Guard: don't stack a second timer if one is already running
        if (this._pollTimer) return;
        const board = this.state.activeBoard;
        if (!board?.auto_refresh) return;
        const interval = (board.refresh_interval || 30) * 1000;
        console.log(`[Dashboard] Auto-refresh started — interval: ${interval / 1000}s`);
        // Fire once immediately so the user sees a refresh right away
        this._refreshBoardData().catch(() => {});
        this._pollTimer = setInterval(() => {
            this._refreshBoardData().catch(() => {});
        }, interval);
        this.state.polling = true;
    }

    _stopPolling() {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
        this.state.polling = false;
    }

    async _refreshBoardData() {
        if (!this.state.activeBoardId) return;
        try {
            const board = await this.orm.call(
                "dashboard.board", "get_board_config",
                [[this.state.activeBoardId]]
            );
            if (this.state.activeBoard) {
                Object.assign(this.state.activeBoard, board);
            } else {
                this.state.activeBoard = board;
            }
            console.log("[Dashboard] Poll: board data loaded, next trigger =", this.state.refreshTrigger + 1);
        } catch (e) {
            console.warn("[Dashboard] Poll: board config RPC failed — items will still refresh:", e?.data?.message || e?.message);
        } finally {
            // ✅ Always increment — mirrors manualRefresh guarantee.
            // Items re-fetch their own live data on every tick regardless of
            // whether the board-config RPC above succeeded or failed.
            this.state.refreshTrigger++;
        }
    }

    async manualRefresh() {
        if (!this.state.activeBoardId) return;
        if (this.state.loading) return;   // prevent double-click
        this.state.loading = true;
        try {
            // Reload board config (name, theme, item list, settings)
            const board = await this.orm.call(
                "dashboard.board", "get_board_config",
                [[this.state.activeBoardId]]
            );
            if (this.state.activeBoard && this.state.activeBoard.id === board.id) {
                Object.assign(this.state.activeBoard, board);
            } else {
                this.state.activeBoard = board;
            }
        } catch (e) {
            // Board config reload failed — show warning but still continue to
            // refresh item data below (refreshTrigger is incremented in finally)
            this.notification.add(
                e?.data?.message || "Could not reload board config. Item data will still refresh.",
                { type: "warning" }
            );
        } finally {
            // ✅ ALWAYS increment — this is what triggers fetchData() in every
            // DashboardItem via onWillUpdateProps, regardless of whether the
            // board config RPC above succeeded or failed.
            this.state.refreshTrigger++;
            await new Promise(r => setTimeout(r, 400));   // keep spinner visible
            this.state.loading = false;
        }
    }

    // =========================================================================
    // Export / Import
    // =========================================================================
    async exportBoard() {
        if (!this.state.activeBoardId) return;
        try {
            const res = await this.orm.call("dashboard.board", "export_to_json", [[this.state.activeBoardId]]);
            const blob = new Blob([res], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${this.state.activeBoard?.name || 'dashboard'}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            this._onError(e, "Export failed");
        }
    }

    async importBoard() {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ".json";
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const text = await file.text();
            try {
                const res = await this.orm.call("dashboard.board", "import_from_json", [text]);
                await this._loadBoards();
                await this._activateBoard(res);
                this.notification.add("Dashboard imported!", { type: "success" });
            } catch (err) {
                this._onError(err, "Import failed");
            }
        };
        input.click();
    }

    // =========================================================================
    // Auto-refresh toggle
    // =========================================================================
    async toggleAutoRefresh() {
        if (!this.state.activeBoardId) return;
        if (this._autoRefreshToggling) return;   // double-click guard
        this._autoRefreshToggling = true;

        const newVal = !this.state.activeBoard.auto_refresh;
        // Optimistically update UI before the RPC so the button feels instant
        this.state.activeBoard.auto_refresh = newVal;

        try {
            await this.orm.call(
                "dashboard.board", "write",
                [[this.state.activeBoardId], { auto_refresh: newVal }]
            );
            if (newVal) {
                this._startPollingIfNeeded();
                this.notification.add("Auto-refresh enabled", { type: "info" });
            } else {
                this._stopPolling();
                this.notification.add("Auto-refresh disabled", { type: "info" });
            }
        } catch (e) {
            // Rollback optimistic update on failure
            this.state.activeBoard.auto_refresh = !newVal;
            this.notification.add(
                e?.data?.message || "Could not save auto-refresh setting.",
                { type: "danger" }
            );
        } finally {
            this._autoRefreshToggling = false;
        }
    }

    // =========================================================================
    // Global date filter
    // =========================================================================
    onGlobalDateChange(filter, dateStart, dateEnd) {
        this.state.globalDateFilter = filter;
        this.state.globalDateStart = dateStart;
        this.state.globalDateEnd = dateEnd;
    }

    // =========================================================================
    // Error
    // =========================================================================
    _onError(e, msg) {
        console.error(msg, e);
        this.state.hasError = true;
        this.state.errorMessage = e?.data?.message || e?.message || msg;
        this.state.loading = false;
    }

    retryLoad() {
        this.state.hasError = false;
        this._loadBoards();
    }
}

// Register as a client action
registry.category("actions").add("advanced_sales_dashboard.action_dashboard", AdvancedSalesDashboard);
