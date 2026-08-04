import pdfplumber, re, json
from collections import defaultdict

path = '/root/.claude/uploads/1d5a60a2-2ab9-5d9c-afaa-d9d01b21efc6/4a1098c9-180_monday_shipout_ps.pdf'
p = pdfplumber.open(path)
full_text = []
for pg in p.pages:
    t = pg.extract_text() or ''
    full_text.append(t)
text = '\n'.join(full_text)
lines = [l.strip() for l in text.split('\n') if l.strip()]

qty_re = re.compile(r'^(.*?)\s*(\d+) of (\d+)$')
sku_re = re.compile(r'^\d{6,}$')
order_re = re.compile(r'Order #(\d+)')

def canon(k):
    if k.startswith('Buffin Muffin '):
        return 'Buffin Muffin - ' + k[len('Buffin Muffin '):]
    if k.startswith('Overnight Oats '):
        return 'Overnight Oats - ' + k[len('Overnight Oats '):]
    return k

prods = json.load(open('/home/claude/hummusfit-warehouse/products.json'))
valid_names = {p['name'] for p in prods}

orders = {}  # order_id -> set(product names)
current_order = None
name_buf = []
in_items = False
i = 0
n = len(lines)
while i < n:
    line = lines[i]
    m_ord = order_re.search(line)
    if m_ord:
        current_order = m_ord.group(1)
        orders.setdefault(current_order, set())
        name_buf = []
        in_items = False
        i += 1
        continue
    if line in ('ITEMS QUANTITY', 'ITEMS'):
        in_items = True
        name_buf = []
        i += 1
        continue
    if not in_items or current_order is None:
        i += 1
        continue
    if line in ('QUANTITY', 'United States'):
        i += 1
        continue
    m = qty_re.match(line)
    if m:
        prefix = m.group(1).strip()
        if prefix:
            name_buf.append(prefix)
        name = ' '.join(name_buf).strip()
        ck = canon(name)
        if ck in valid_names:
            orders[current_order].add(ck)
        name_buf = []
        i += 1
        if i < n and sku_re.match(lines[i]):
            i += 1
        continue
    name_buf.append(line)
    i += 1

# drop first-item contamination artifacts: if an order's item set contains a name
# that never matched (skipped) it's fine, we only added valid canon matches.
orders = {k: v for k, v in orders.items() if v}
print('orders with valid items:', len(orders))
print('avg items/order:', sum(len(v) for v in orders.values()) / len(orders))

json.dump({k: sorted(v) for k, v in orders.items()}, open('/home/claude/hummusfit-warehouse/order_items.json', 'w'), indent=2)
