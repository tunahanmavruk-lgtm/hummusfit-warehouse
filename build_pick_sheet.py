"""
Printable pick/restock reference sheet — lane code, product, category,
crates needed/day, units per crate, and a confidence flag for blended
estimates. Two views in one PDF:
  1. Physical walking order (K1->K2->K3->M1->M2->M3, position 1->27) —
     for pickers/restockers physically moving through the room.
  2. Alphabetical-by-product index — for inventory/ordering lookups
     ("how many crates of X do we need") without hunting row by row.
Generated directly from lane_plan.json, the same file that drives the
live app, blueprint, and 3D model — so this sheet can't drift out of
sync with what's actually seeded in the picking app.
"""
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

lane_plan = json.load(open('/home/claude/hummusfit-warehouse/lane_plan.json'))
geometry = json.load(open('/home/claude/hummusfit-warehouse/blueprint_geometry.json'))
POS_BY_SECTION = geometry['positions_per_row_by_section']  # bakery: 35/row, meals: 27/row

ROWS_ORDER = ['K1', 'K2', 'K3', 'M1', 'M2', 'M3']
ROW_SECTION = {'K1': 'Bakery & Snacks', 'K2': 'Bakery & Snacks', 'K3': 'Bakery & Snacks',
               'M1': 'Meals', 'M2': 'Meals', 'M3': 'Meals'}
ROW_SECTION_KEY = {'K1': 'bakery', 'K2': 'bakery', 'K3': 'bakery', 'M1': 'meals', 'M2': 'meals', 'M3': 'meals'}
CAT_LABEL = {'muffin': 'Muffin', 'oats': 'Oats', 'snack': 'Snack', 'meal': 'Meal'}

lanes_by_row = {r: [] for r in ROWS_ORDER}
all_lanes = []
for sec in lane_plan.values():
    for l in sec['lanes']:
        row = l['code'].split('-')[0]
        lanes_by_row[row].append(l)
        all_lanes.append(l)
for r in lanes_by_row:
    lanes_by_row[r].sort(key=lambda l: int(l['code'].split('-')[1]))

styles = getSampleStyleSheet()
title_style = ParagraphStyle('TitleX', parent=styles['Title'], fontSize=18, spaceAfter=2)
sub_style = ParagraphStyle('SubX', parent=styles['Normal'], fontSize=9.5, textColor=colors.HexColor('#555555'), spaceAfter=10)
section_style = ParagraphStyle('SectionX', parent=styles['Heading2'], fontSize=13, spaceBefore=14, spaceAfter=4, textColor=colors.HexColor('#111417'))
row_style = ParagraphStyle('RowX', parent=styles['Heading3'], fontSize=10.5, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor('#2BBFAA'))
cell_style = ParagraphStyle('CellX', parent=styles['Normal'], fontSize=8.5, leading=10)
cell_center = ParagraphStyle('CellC', parent=cell_style, alignment=TA_CENTER)
foot_style = ParagraphStyle('FootX', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#767c85'))

HEADER_BG = colors.HexColor('#111417')
BAKERY_BG = colors.HexColor('#eafaf7')
MEALS_BG = colors.HexColor('#eef0f4')
GRID = colors.HexColor('#dddddd')

def lane_table(lanes, section_name):
    header = ['Lane', 'Product', 'Category', 'Crates / Day', 'Units / Crate']
    data = [header]
    for l in lanes:
        flag = ' ~' if l.get('divergence_flag') else ''
        data.append([
            l['code'] + flag,
            Paragraph(l['product'], cell_style),
            CAT_LABEL.get(l['category'], l['category']),
            str(l['crates_needed']),
            str(l['cap']),
        ])
    t = Table(data, colWidths=[0.7*inch, 3.35*inch, 0.85*inch, 0.9*inch, 0.9*inch], repeatRows=1)
    bg = BAKERY_BG if section_name == 'Bakery & Snacks' else MEALS_BG
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    t.setStyle(TableStyle(style))
    return t

doc = SimpleDocTemplate(
    '/home/claude/hummusfit-warehouse/Hummus_Fit_Pick_Sheet.pdf',
    pagesize=letter,
    topMargin=0.55*inch, bottomMargin=0.55*inch,
    leftMargin=0.55*inch, rightMargin=0.55*inch,
)
story = []

# ---- Page 1+: walking-order pick sheet ----
story.append(Paragraph('Hummus Fit — Walk-In Pick Sheet', title_style))
story.append(Paragraph(
    'Physical walking order (K1 → K2 → K3 → M1 → M2 → M3) — matches the room blueprint. Bakery rows (K1-K3) run '
    '35 positions/row; Meals rows (M1-M3) run 27 positions/row. '
    'Demand is sourced from real Shopify Online Store sales (90-day trailing daily average). '
    '"~" after a lane code means the last 7 days diverge more than 2x from that 90-day average — worth a spot-check. '
    '"Crates / Day" is daily replenishment need; "Units / Crate" is how many units fill one crate. Max stack per lane is 7 crates.',
    sub_style
))

current_section = None
for r in ROWS_ORDER:
    sec_name = ROW_SECTION[r]
    if sec_name != current_section:
        story.append(Paragraph(sec_name, section_style))
        current_section = sec_name
    used = len(lanes_by_row[r])
    total = POS_BY_SECTION[ROW_SECTION_KEY[r]]
    story.append(Paragraph(f'Row {r} — {used}/{total} positions in use', row_style))
    story.append(lane_table(lanes_by_row[r], sec_name))
    story.append(Spacer(1, 4))

# ---- Appendix: alphabetical-by-product index ----
story.append(PageBreak())
story.append(Paragraph('Appendix — Alphabetical Product Index', title_style))
story.append(Paragraph(
    'Same data, sorted by product name for inventory/reorder lookups. Use the Pick Sheet above for physically restocking the room.',
    sub_style
))

alpha_sorted = sorted(all_lanes, key=lambda l: l['product'].lower())
header = ['Product', 'Lane', 'Category', 'Crates / Day', 'Units / Crate']
data = [header]
for l in alpha_sorted:
    flag = ' ~' if l.get('divergence_flag') else ''
    data.append([
        Paragraph(l['product'], cell_style),
        l['code'] + flag,
        CAT_LABEL.get(l['category'], l['category']),
        str(l['crates_needed']),
        str(l['cap']),
    ])
t = Table(data, colWidths=[3.35*inch, 0.7*inch, 0.85*inch, 0.9*inch, 0.9*inch], repeatRows=1)
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTSIZE', (0, 0), (-1, 0), 8.5),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 1), (-1, -1), 8.5),
    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ('GRID', (0, 0), (-1, -1), 0.5, GRID),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
]))
story.append(t)

story.append(Spacer(1, 10))
total_crates = sum(l['crates_needed'] for l in all_lanes)
est_count = sum(1 for l in all_lanes if l.get('divergence_flag'))
story.append(Paragraph(
    f'{len(all_lanes)} products across 162 floor positions · {total_crates} crates/day total across the room · '
    f'{est_count} lanes flagged "~" (7-day vs 90-day Shopify averages diverge >2x — spot-check before trusting). '
    'Generated from lane_plan.json — the same file that seeds the live picking app.',
    foot_style
))

doc.build(story)
print('PDF written:', '/home/claude/hummusfit-warehouse/Hummus_Fit_Pick_Sheet.pdf')
