"""检查许可转让数据"""
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database='patent_analysis',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cursor = conn.cursor()

print('=== 专利转让表数据 ===')
cursor.execute('SELECT COUNT(*) as cnt FROM patent_transfer')
print(f'总记录数: {cursor.fetchone()["cnt"]}')

cursor.execute('SELECT COUNT(*) as cnt FROM patent_transfer WHERE licensor IS NOT NULL AND licensor != "" AND licensee IS NOT NULL AND licensee != ""')
print(f'有licensor和licensee的记录: {cursor.fetchone()["cnt"]}')

print('\n=== 示例数据 ===')
cursor.execute('SELECT licensor, licensee, transfer_type, COUNT(*) as cnt FROM patent_transfer GROUP BY licensor, licensee, transfer_type ORDER BY cnt DESC LIMIT 20')
for row in cursor.fetchall():
    print(f'{row["licensor"]} -> {row["licensee"]} ({row["transfer_type"]}): {row["cnt"]}')

print('\n=== 原始数据示例 ===')
cursor.execute("SELECT licensor, licensee FROM patent_transfer LIMIT 10")
for row in cursor.fetchall():
    licensor = row['licensor'] if row['licensor'] else 'NULL'
    licensee = row['licensee'] if row['licensee'] else 'NULL'
    print(f'licensor="{licensor}", licensee="{licensee}"')

conn.close()