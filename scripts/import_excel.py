
import pandas as pd
import sqlite3
import os
import json

EXCEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'Screening_Table_Complete.xlsx')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'server', 'database.sqlite')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'server', 'schema.sql')

def init_db():
    print(f"Initializing DB at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    return conn

def import_data(conn):
    print(f"Reading Excel from {EXCEL_PATH}")
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=0)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    print("Columns found:", df.columns.tolist())
    
    # Clean column names to lowercase/strip
    df.columns = [c.strip() for c in df.columns]
    
    # Assume generic column mapping if exact names don't match
    # Mapping strategy: Look for keywords
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if 'module' in cl and 'key' in cl: col_map['module_key'] = c
        elif 'module' in cl: col_map['module_name'] = c
        elif 'item' in cl and 'key' in cl: col_map['item_key'] = c
        elif 'item' in cl: col_map['item_name'] = c
        elif 'desc' in cl: col_map['description'] = c
        elif 'weight' in cl: col_map['weight'] = c
        elif 'min' in cl: col_map['score_min'] = c
        elif 'max' in cl: col_map['score_max'] = c
        elif 'rule' in cl: col_map['rule_json'] = c
    
    cursor = conn.cursor()
    
    # 1. Modules
    # Group by module_name/key to get unique modules
    if 'module_key' not in col_map:
        # Fallback: Generate keys if missing
        print("Warning: No module_key column found. Generating from name.")
        df['module_key_gen'] = df[col_map['module_name']].apply(lambda x: str(x).lower().replace(' ', '_'))
        col_map['module_key'] = 'module_key_gen'

    unique_modules = df[[col_map['module_key'], col_map['module_name']]].drop_duplicates()
    
    for idx, row in unique_modules.iterrows():
        key = row[col_map['module_key']]
        name = row[col_map['module_name']]
        print(f"Inserting Module: {name} ({key})")
        cursor.execute('''
            INSERT OR IGNORE INTO scoring_modules (module_key, module_name, sort_order)
            VALUES (?, ?, ?)
        ''', (key, name, idx))
    
    conn.commit()
    
    # 2. Items
    # Need to map module_key to module_id
    cursor.execute("SELECT module_key, id FROM scoring_modules")
    mod_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    for idx, row in df.iterrows():
        mod_key = row[col_map['module_key']]
        mod_id = mod_map.get(mod_key)
        
        if not mod_id:
            print(f"Skipping row {idx}: Module key {mod_key} not found in DB")
            continue
            
        item_key = row.get(col_map.get('item_key', ''), f"item_{idx}")
        # If item key is header or empty, skip or gen
        if pd.isna(item_key) or item_key == '':
            item_key = f"item_{idx}"
            
        item_name = row.get(col_map.get('item_name'), 'Unnamed Item')
        desc = row.get(col_map.get('description'), '')
        weight = row.get(col_map.get('weight'), 1.0)
        s_min = row.get(col_map.get('score_min'), 1.0)
        s_max = row.get(col_map.get('score_max'), 5.0)
        
        # safely handle numeric conversions
        try: weight = float(weight) 
        except: weight = 0
        try: s_min = float(s_min)
        except: s_min = 1.0
        try: s_max = float(s_max)
        except: s_max = 5.0

        print(f"Inserting Item: {item_name} -> Module {mod_id}")
        cursor.execute('''
            INSERT OR REPLACE INTO scoring_items 
            (module_id, item_key, item_name, description, weight, score_min, score_max, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mod_id, item_key, item_name, desc, weight, s_min, s_max, idx))

    conn.commit()
    print("Import completed.")

if __name__ == "__main__":
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
        
    conn = init_db()
    import_data(conn)
    conn.close()
