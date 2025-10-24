import sqlite3

conn = sqlite3.connect('./data/activity_test.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== Activities ===')
cursor.execute('''
    SELECT a.id, a.name, c.name as cat_name
    FROM activities a
    JOIN categories c ON a.category_id = c.id
    ORDER BY a.category_id, a.order_index
''')
for row in cursor.fetchall():
    print(f'{row["id"]:2d}. [{row["cat_name"]}] {row["name"]}')

print('\n=== Tags (sample 5) ===')
cursor.execute('''
    SELECT t.id, c.name as cat, a.name as act, t.duration_min
    FROM tags t
    JOIN categories c ON t.category_id = c.id
    JOIN activities a ON t.activity_id = a.id
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'Tag {row["id"]}: [{row["cat"]}] {row["act"]} ({row["duration_min"]}min)')

conn.close()
