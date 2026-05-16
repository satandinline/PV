"""检查数据库中的数据用于桑基图和网络图"""
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database='patent_analysis',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 查看licensor和licensee字段的数据
print('=== 许可人字段示例 ===')
cursor.execute("SELECT DISTINCT licensor FROM patents WHERE licensor IS NOT NULL AND licensor != '' AND licensor != '-' LIMIT 20")
for row in cursor.fetchall():
    print(row[0])

print('\n=== 被许可人字段示例 ===')
cursor.execute("SELECT DISTINCT licensee FROM patents WHERE licensee IS NOT NULL AND licensee != '' AND licensee != '-' LIMIT 20")
for row in cursor.fetchall():
    print(row[0])

print('\n=== 专利类型分布 ===')
cursor.execute("SELECT patent_type, COUNT(*) as cnt FROM patents GROUP BY patent_type ORDER BY cnt DESC")
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

print('\n=== IPC小类分布 ===')
cursor.execute("SELECT ipc_subclass, COUNT(*) as cnt FROM patents WHERE ipc_subclass IS NOT NULL AND ipc_subclass != '-' GROUP BY ipc_subclass ORDER BY cnt DESC LIMIT 10")
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

print('\n=== 省份分布 ===')
cursor.execute("SELECT applicant_province, COUNT(*) as cnt FROM patents GROUP BY applicant_province ORDER BY cnt DESC LIMIT 15")
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

conn.close()