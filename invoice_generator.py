"""
請求書PDF自動生成ツール
依存: reportlab
使用: python invoice_generator.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# 日本語フォント登録
pdfmetrics.registerFont(TTFont("HeiseiMIn-W3", "/Users/takedamasahiro/NotoSansJP.ttf"))
pdfmetrics.registerFont(TTFont("HeiseiKakugo-W5", "/Users/takedamasahiro/NotoSansJP.ttf"))
FONT_MINCHO = "HeiseiMIn-W3"
FONT_GOTHIC = "HeiseiKakugo-W5"
MAX_ITEMS = 10  # MAX_TTEMSのタイポも修正


def hex_to_rgb_ratio(hex_color: str):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return r / 255, g / 255, b / 255


def generate_invoice(data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    accent_hex = data.get("accent_color", "#1a73e8")
    r, g, b = hex_to_rgb_ratio(accent_hex)
    accent = colors.Color(r, g, b)
    accent_light = colors.Color(r, g, b, alpha=0.12)
    story = []

    # ---- タイトル行 ----
    # [Fix 1] fontsize → fontSize (大文字S)
    # [Fix 2] tytle_style → title_style (タイポ修正、重複定義も削除)
    title_style = ParagraphStyle(
        "Title", fontName=FONT_GOTHIC, fontSize=22, textColor=accent,
        spaceAfter=2 * mm, leading=28
    )
    story.append(Paragraph("請　求　書", title_style))
    # [Fix 3] HRFliwable → HRFlowable (スペルミス修正)
    story.append(HRFlowable(width="100%", thickness=2, color=accent, spaceAfter=4 * mm))

    # ---- 請求番号・日付 ----
    meta_style = ParagraphStyle("Meta", fontName=FONT_GOTHIC, fontSize=9, textColor=colors.grey)
    invoice_no = data.get("invoice_no", "INV_001")
    issue_date = data.get("issue_date", str(date.today()))
    due_date = data.get("due_date", "")
    # [Fix 4] story.append = ... という誤った代入を削除（story.appendが上書きされるバグ）
    story.append(Paragraph(
        f"請求番号: {invoice_no}　発行日: {issue_date}　支払期限: {due_date}",
        meta_style
    ))
    story.append(Spacer(1, 5 * mm))

    # ---- 請求先 & 請求元　2カラム ----
    client_name = data.get("client_name", "")
    # [Fix 5] client_adress → client_address (スペルミス修正)
    client_address = data.get("client_address", "")
    sender_name = data.get("sender_name", "")
    # [Fix 5] sender_adress → sender_address (スペルミス修正)
    sender_address = data.get("sender_address", "")
    sender_tel = data.get("sender_tel", "")
    sender_email = data.get("sender_email", "")

    # [Fix 6] leaading → leading (タイポ修正)
    left_style = ParagraphStyle("Left", fontName=FONT_GOTHIC, fontSize=10, leading=16)
    right_style = ParagraphStyle("Right", fontName=FONT_GOTHIC, fontSize=9,
                                 leading=14, alignment=TA_RIGHT)
    label_style = ParagraphStyle("Label", fontName=FONT_GOTHIC, fontSize=8,
                                 textColor=colors.white)

    client_block = [
        [Paragraph("請求先", label_style)],
        [Paragraph(f"<b>{client_name} 御中</b>", left_style)],
        [Paragraph(client_address.replace("\n", "<br/>"), left_style)],
    ]
    sender_lines = f"<b>{sender_name}</b><br/>"
    if sender_address:
        sender_lines += sender_address.replace("\n", "<br/>") + "<br/>"
    if sender_tel:
        sender_lines += f"TEL: {sender_tel}<br/>"
    if sender_email:
        sender_lines += f"Email: {sender_email}"

    sender_block = [
        [Paragraph("請求元", label_style)],
        [Paragraph(sender_lines, right_style)],
    ]

    client_table = Table(client_block, colWidths=[85 * mm])
    client_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
    ]))

    sender_table = Table(sender_block, colWidths=[85 * mm])
    sender_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
    ]))

    two_col = Table([[client_table, sender_table]], colWidths=[90 * mm, 90 * mm])
    two_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(two_col)
    story.append(Spacer(1, 6 * mm))

    # ---- 合計金額バナー ----
    items = data.get("items", [])
    tax_rate = float(data.get("tax_rate", 10)) / 100
    subtotal = sum(int(it.get("qty", 0)) * int(it.get("unit_price", 0)) for it in items if it.get("name"))
    tax = int(subtotal * tax_rate)
    total = subtotal + tax

    total_style = ParagraphStyle("Total", fontName=FONT_GOTHIC, fontSize=14,
                                 textColor=colors.white, alignment=TA_CENTER)
    # [Fix: "誤請求金額" → "ご請求金額" (誤字修正)]
    total_table = Table(
        [[Paragraph(f"ご請求金額 ¥{total:,} (税込)", total_style)]],
        colWidths=[170 * mm]
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), accent),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 6 * mm))

    # ---- 明細テーブル ----
    # [Fix 7] fontsize=9 → fontSize=9 (th_style と td_style 両方)
    # [Fix 8] leadinf=13 → leading=13 (td_style のタイポ)
    th_style = ParagraphStyle("TH", fontName=FONT_GOTHIC, fontSize=9,
                              textColor=colors.white, alignment=TA_CENTER)
    td_style = ParagraphStyle("TD", fontName=FONT_MINCHO, fontSize=9, leading=13)
    # [Fix 9] Paragraph("TDR",...) → ParagraphStyle("TDR",...) (クラスの誤り)
    td_right = ParagraphStyle("TDR", fontName=FONT_MINCHO, fontSize=9,
                              leading=13, alignment=TA_RIGHT)

    header = [
        Paragraph("品目・サービス名", th_style),
        Paragraph("数量", th_style),
        Paragraph("単価(円)", th_style),
        Paragraph("金額(円)", th_style),
    ]
    table_data = [header]

    for it in items:
        name = it.get("name", "")
        if not name:
            continue
        qty = int(it.get("qty", 1))
        unit = int(it.get("unit_price", 0))
        amount = qty * unit
        table_data.append([
            Paragraph(name, td_style),
            Paragraph(str(qty), td_right),
            Paragraph(f"{unit:,}", td_right),
            # [Fix 10] f"{amount:,}, td_right" → f"{amount:,}", td_right (クオートの位置ずれ修正)
            Paragraph(f"{amount:,}", td_right),
        ])

    # 空行パディング（最低5行）
    while len(table_data) < 6:
        table_data.append(["", "", "", ""])

    col_w = [90 * mm, 20 * mm, 30 * mm, 30 * mm]
    detail_table = Table(table_data, colWidths=col_w, repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        # [Fix 11] ROWBACKGROUND → ROWBACKGROUNDS (複数形が正しいReportLab命令)
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 6),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 4 * mm))

    doc.build(story)


# ---- GUI ----
class InvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("請求書ジェネレーター")
        self.resizable(False, False)
        self._accent_color = "#1a73e8"
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 基本情報タブ ---
        f1 = ttk.Frame(nb)
        nb.add(f1, text="基本情報")
        fields_basic = [
            ("請求番号", "invoice_no", "INV-001"),
            ("発行日 (YYYY-MM-DD)", "issue_date", str(date.today())),
            ("支払期限 (YYYY-MM-DD)", "due_date", ""),
        ]
        self._entries = {}
        for i, (label, key, default) in enumerate(fields_basic):
            ttk.Label(f1, text=label).grid(row=i, column=0, sticky="w", **pad)
            e = ttk.Entry(f1, width=30)
            e.insert(0, default)
            e.grid(row=i, column=1, sticky="ew", **pad)
            self._entries[key] = e

        # アクセントカラー
        row = len(fields_basic)
        ttk.Label(f1, text="アクセントカラー").grid(row=row, column=0, sticky="w", **pad)
        self._color_btn = tk.Button(f1, bg=self._accent_color, width=8,
                                    command=self._pick_color)
        self._color_btn.grid(row=row, column=1, sticky="w", **pad)

        # --- 請求先タブ ---
        f2 = ttk.Frame(nb)
        nb.add(f2, text="請求先")
        fields_client = [
            ("会社名・氏名", "client_name", ""),
            ("住所", "client_address", ""),
        ]
        for i, (label, key, default) in enumerate(fields_client):
            ttk.Label(f2, text=label).grid(row=i, column=0, sticky="w", **pad)
            e = ttk.Entry(f2, width=40)
            e.insert(0, default)
            e.grid(row=i, column=1, sticky="ew", **pad)
            self._entries[key] = e

        # --- 請求元タブ ---
        f3 = ttk.Frame(nb)
        nb.add(f3, text="請求元")
        fields_sender = [
            ("氏名・会社名", "sender_name", ""),
            ("住所", "sender_address", ""),
            ("電話番号", "sender_tel", ""),
            ("メールアドレス", "sender_email", ""),
        ]
        for i, (label, key, default) in enumerate(fields_sender):
            ttk.Label(f3, text=label).grid(row=i, column=0, sticky="w", **pad)
            e = ttk.Entry(f3, width=40)
            e.insert(0, default)
            e.grid(row=i, column=1, sticky="ew", **pad)
            self._entries[key] = e
 
        # --- 明細タブ ---
        f4 = ttk.Frame(nb)
        nb.add(f4, text="明細")
        ttk.Label(f4, text="品目名").grid(row=0, column=0, **pad)
        ttk.Label(f4, text="数量").grid(row=0, column=1, **pad)
        ttk.Label(f4, text="単価").grid(row=0, column=2, **pad)
        self._item_rows = []
        for i in range(MAX_ITEMS):
            name_e = ttk.Entry(f4, width=25)
            qty_e = ttk.Entry(f4, width=6)
            price_e = ttk.Entry(f4, width=10)
            qty_e.insert(0, "1")
            price_e.insert(0, "0")
            name_e.grid(row=i + 1, column=0, **pad)
            qty_e.grid(row=i + 1, column=1, **pad)
            price_e.grid(row=i + 1, column=2, **pad)
            self._item_rows.append((name_e, qty_e, price_e))
 
        ttk.Label(f4, text="消費税率(%)").grid(row=MAX_ITEMS + 1, column=0, sticky="w", **pad)
        self._tax_entry = ttk.Entry(f4, width=6)
        self._tax_entry.insert(0, "10")
        self._tax_entry.grid(row=MAX_ITEMS + 1, column=1, sticky="w", **pad)
 
        # --- 生成ボタン ---
        ttk.Button(self, text="PDFを生成する", command=self._generate).pack(pady=8)
 
    def _pick_color(self):
        color = colorchooser.askcolor(color=self._accent_color, title="アクセントカラーを選択")[1]
        if color:
            self._accent_color = color
            self._color_btn.configure(bg=color)
 
    def _generate(self):
        data = {k: e.get() for k, e in self._entries.items()}
        data["accent_color"] = self._accent_color
        data["tax_rate"] = self._tax_entry.get()
        data["items"] = []
        for name_e, qty_e, price_e in self._item_rows:
            name = name_e.get().strip()
            if name:
                try:
                    qty = int(qty_e.get())
                    price = int(price_e.get())
                except ValueError:
                    messagebox.showerror("入力エラー", f"「{name}」の数量・単価を正しく入力してください。")
                    return
                data["items"].append({"name": name, "qty": qty, "unit_price": price})
 
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"請求書_{data.get('invoice_no', 'INV-001')}.pdf"
        )
        if not path:
            return
        try:
            generate_invoice(data, path)
            messagebox.showinfo("完了", f"PDFを保存しました:\n{path}")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
 
 
if __name__ == "__main__":
    app = InvoiceApp()
    app.mainloop()
