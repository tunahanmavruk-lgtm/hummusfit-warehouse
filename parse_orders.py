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

counts = defaultdict(int)
orders = set()
i = 0
name_buf = []
n = len(lines)
in_items = False
while i < n:
    line = lines[i]
    m_ord = order_re.search(line)
    if m_ord:
        orders.add(m_ord.group(1))
        name_buf = []
        in_items = False
        i += 1
        continue
    if line in ('ITEMS QUANTITY', 'ITEMS'):
        in_items = True
        name_buf = []
        i += 1
        continue
    if not in_items:
        i += 1
        continue
    if line in ('QUANTITY', 'United States'):
        i += 1
        continue
    m = qty_re.match(line)
    if m:
        prefix, qty, tot = m.group(1).strip(), int(m.group(2)), m.group(3)
        if prefix:
            name_buf.append(prefix)
        name = ' '.join(name_buf).strip()
        if name:
            counts[name] += qty
        name_buf = []
        i += 1
        if i < n and sku_re.match(lines[i]):
            i += 1
        continue
    name_buf.append(line)
    i += 1

print('orders found:', len(orders))
print('total distinct names:', len(counts))
top = sorted(counts.items(), key=lambda x: -x[1])
for k, v in top[:15]:
    print(v, k)
print('---tail (likely junk / unmatched names)---')
for k, v in top[-30:]:
    print(v, k)
print('grand total units', sum(counts.values()))
json.dump(dict(top), open('/home/claude/hummusfit-warehouse/real_order_counts_raw.json', 'w'), indent=2)
