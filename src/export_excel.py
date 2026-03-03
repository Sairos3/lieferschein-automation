import sqlite3
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter


def auto_adjust_column_width(ws, min_width=10, extra_padding=3, filter_padding=2):
    """
    extra_padding: normal spacing
    filter_padding: extra space for Excel filter dropdown arrow in header
    """
    for col_cells in ws.columns:
        column_letter = col_cells[0].column_letter

        # header text (row 1)
        header_val = ws[f"{column_letter}1"].value
        header_len = len(str(header_val)) if header_val is not None else 0

        # max content length (all rows)
        max_len = header_len
        for cell in col_cells:
            if cell.value is None:
                continue
            max_len = max(max_len, len(str(cell.value)))

        # add padding + extra room for filter arrow
        width = max_len + extra_padding + filter_padding
        ws.column_dimensions[column_letter].width = max(min_width, width)

def style_header(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

def apply_column_alignment(ws, align_map: dict[int, str]):
    for row in ws.iter_rows(min_row=2):
        for col_idx, align in align_map.items():
            cell = row[col_idx - 1]
            cell.alignment = Alignment(
                horizontal=align,
                vertical="center",
                wrap_text=(align == "left")
            )

def apply_number_formats(ws, fmt_map: dict[int, str]):
    """
    fmt_map: {1-based column_index: excel_number_format_string}
    """
    for row in ws.iter_rows(min_row=2):
        for col_idx, fmt in fmt_map.items():
            cell = row[col_idx - 1]
            if cell.value is not None:
                cell.number_format = fmt

def export_to_excel(db_path: Path, output_path: Path) -> None:
    con = sqlite3.connect(db_path)
    wb = Workbook()

    # Sheet 1: Delivery Notes
    ws_notes = wb.active
    ws_notes.title = "DeliveryNotes"
    ws_notes.append([
        "Supplier", "DeliveryNoteNo", "DeliveryDate", "CustomerNo", "OrderNo",
        "Subtotal", "VAT", "Total", "SourcePDF"
    ])
    style_header(ws_notes)
    rows = con.execute("""
        SELECT s.name,
               d.delivery_note_no,
               d.delivery_date,
               d.customer_no,
               d.order_no,
               d.subtotal,
               d.vat,
               d.total,
               d.source_pdf
        FROM delivery_notes d
        JOIN suppliers s ON s.id = d.supplier_id
        ORDER BY d.id
    """).fetchall()
    for r in rows:
        ws_notes.append(r)
    # Column alignment (1-based):
    # A Supplier left, B note no left, C date center, D/E left, F/G/H money right, I left
    apply_column_alignment(ws_notes, {
        1: "left", 2: "left", 3: "center", 4: "left", 5: "left",
        6: "right", 7: "right", 8: "right", 9: "left"
    })
    apply_number_formats(ws_notes, {
        6: '#,##0.00 "€"', 7: '#,##0.00 "€"', 8: '#,##0.00 "€"'
    })

    # Sheet 2: Items
    ws_items = wb.create_sheet("Items")
    ws_items.append([
        "Supplier", "DeliveryNoteNo", "LineNo", "ArticleNo", "Description",
        "Quantity", "UnitPrice", "LineTotal"
    ])
    style_header(ws_items)

    item_rows = con.execute("""
        SELECT s.name,
               d.delivery_note_no,
               i.line_no,
               i.article_no,
               i.description,
               i.quantity,
               i.unit_price,
               i.line_total
        FROM delivery_note_items i
        JOIN delivery_notes d ON d.id = i.delivery_note_id
        JOIN suppliers s ON s.id = d.supplier_id
        ORDER BY d.id, i.line_no
    """).fetchall()
    for r in item_rows:
        ws_items.append(r)
    # A Supplier left, B note no left, C line no right, D article left, E desc left,
    # F qty right, G/H money right
    apply_column_alignment(ws_items, {
        1: "left", 2: "left", 3: "right", 4: "left", 5: "left",
        6: "right", 7: "right", 8: "right"
    })
    apply_number_formats(ws_items, {
        6: "0.00", 7: '#,##0.00 "€"', 8: '#,##0.00 "€"'
    })

    # Sheet 3: Summary
    ws_summary = wb.create_sheet("Summary")
    ws_summary.append(["Supplier", "Total Amount"])
    style_header(ws_summary)

    summary_rows = con.execute("""
        SELECT s.name, COALESCE(SUM(d.total), 0)
        FROM delivery_notes d
        JOIN suppliers s ON s.id = d.supplier_id
        GROUP BY s.name
        ORDER BY s.name
    """).fetchall()
    for r in summary_rows:
        ws_summary.append(r)
    apply_column_alignment(ws_summary, {1: "left", 2: "right"})
    apply_number_formats(ws_summary, {2: '#,##0.00 "€"'})
    # Auto adjust widths
    auto_adjust_column_width(ws_notes)
    auto_adjust_column_width(ws_items)
    auto_adjust_column_width(ws_summary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    print("Excel exported to:", output_path.resolve())