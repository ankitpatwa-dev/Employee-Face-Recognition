/** @odoo-module **/
/**
 * Download utilities — CSV, Excel (SheetJS), PDF (jsPDF), PNG (html2canvas)
 */

/**
 * Main entry point called by DashboardItem
 * @param {Object} config - item config
 * @param {Object} data   - fetched data
 * @param {string} format - "csv" | "excel" | "pdf" | "png"
 */
export function downloadItem(config, data, format) {
    const filename = (config.name || "dashboard_item").replace(/\s+/g, "_");

    if (format === "csv")   { _downloadCSV(config, data, filename);   return; }
    if (format === "excel") { _downloadExcel(config, data, filename);  return; }
    if (format === "pdf")   { _downloadPDF(config, data, filename);    return; }
}

// ──────────────────────────────────────────────────────────────────────────
// CSV
// ──────────────────────────────────────────────────────────────────────────
function _downloadCSV(config, data, filename) {
    const rows = _getRows(config, data);
    if (!rows.length) { alert("No data to export."); return; }

    const header = Object.keys(rows[0]);
    const csv    = [
        header.join(","),
        ...rows.map(r => header.map(h => _csvCell(r[h])).join(","))
    ].join("\n");

    _downloadBlob(csv, `${filename}.csv`, "text/csv");
}

function _csvCell(val) {
    if (val === null || val === undefined) return "";
    const s = String(val);
    return s.includes(",") || s.includes('"') || s.includes("\n")
        ? `"${s.replace(/"/g, '""')}"`
        : s;
}

// ──────────────────────────────────────────────────────────────────────────
// Excel via SheetJS (XLSX)
// ──────────────────────────────────────────────────────────────────────────
function _downloadExcel(config, data, filename) {
    if (typeof XLSX === "undefined") {
        alert("SheetJS (XLSX) not loaded. Add it to the asset bundle.");
        return;
    }
    const rows = _getRows(config, data);
    if (!rows.length) { alert("No data to export."); return; }

    const wb  = XLSX.utils.book_new();
    const ws  = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, config.name || "Data");
    XLSX.writeFile(wb, `${filename}.xlsx`);
}

// ──────────────────────────────────────────────────────────────────────────
// PDF via jsPDF + autoTable
// ──────────────────────────────────────────────────────────────────────────
function _downloadPDF(config, data, filename) {
    if (typeof jspdf === "undefined" && typeof window.jspdf === "undefined") {
        alert("jsPDF not loaded.");
        return;
    }
    const jsPDF  = (window.jspdf?.jsPDF) || window.jsPDF;
    const doc    = new jsPDF({ orientation: "landscape", unit: "mm" });

    doc.setFontSize(14);
    doc.text(config.name || "Dashboard Item", 14, 16);
    doc.setFontSize(9);
    doc.text(`Exported: ${new Date().toLocaleDateString()}`, 14, 22);

    const rows = _getRows(config, data);
    if (rows.length && typeof doc.autoTable === "function") {
        const head = [Object.keys(rows[0])];
        const body = rows.map(r => Object.values(r).map(v => String(v ?? "")));
        doc.autoTable({ head, body, startY: 28, styles: { fontSize: 8 }, headStyles: { fillColor: [109, 40, 217] } });
    } else if (data?.value !== undefined) {
        doc.setFontSize(36);
        doc.text(String(data.value ?? ""), 14, 50);
    } else {
        doc.setFontSize(10);
        doc.text("Chart / visual data — use PNG for this item type.", 14, 40);
    }

    doc.save(`${filename}.pdf`);
}

// ──────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────
function _getRows(config, data) {
    if (!data) return [];
    // List items
    if (data.records)  return data.records;
    // Chart labels + values
    if (data.labels && data.datasets) {
        const ds = data.datasets[0]?.data || [];
        return data.labels.map((l, i) => ({ label: l, value: ds[i] ?? "" }));
    }
    // KPI
    if (data.value !== undefined) {
        return [{ metric: config.name, value: data.value, growth: data.growth || "" }];
    }
    return [];
}

function _downloadBlob(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
