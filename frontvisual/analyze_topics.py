"""分析专利标题和摘要，提取主题"""
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

print('=== 分析标题关键词 ===')
cursor.execute("""
    SELECT title FROM patents 
    WHERE title IS NOT NULL AND title != '' AND title != '-'
    LIMIT 100
""")
titles = [row['title'] for row in cursor.fetchall()]

# 统计常见关键词
keywords = {}
for title in titles:
    for kw in ['机器人', '人形', '手臂', '腿部', '关节', '驱动', '电机', '传感器', '视觉', '导航', '控制', '人工智能', '深度学习', '平衡', '步态', '灵巧手', '拟人', '仿生', '感知', '交互']:
        if kw in title:
            keywords[kw] = keywords.get(kw, 0) + 1

print('标题关键词统计:')
for k, v in sorted(keywords.items(), key=lambda x: -x[1])[:20]:
    print(f'  {k}: {v}')

# 提取IPC分类与主题的关联
print('\n=== IPC分类与主题关联 ===')
cursor.execute("""
    SELECT ipc_subclass, COUNT(*) as cnt
    FROM patents 
    WHERE ipc_subclass IS NOT NULL AND ipc_subclass != '-' AND ipc_subclass != ''
    GROUP BY ipc_subclass
    ORDER BY cnt DESC
    LIMIT 20
""")
ipcs = cursor.fetchall()
for row in ipcs:
    print(f"  {row['ipc_subclass']}: {row['cnt']}")

# 检查许可转让数据
print('\n=== 许可转让数据清洗分析 ===')
cursor.execute("""
    SELECT public_number, licensor, licensee 
    FROM patents 
    WHERE licensor IS NOT NULL AND licensor != '' AND licensor != '-'
    LIMIT 20
""")
records = cursor.fetchall()
for row in records:
    licensor = row['licensor'] if row['licensor'] else ''
    licensee = row['licensee'] if row['licensee'] else ''
    print(f"专利: {row['public_number'][:20]}... | 许可人: {licensor[:50]}... | 被许可人: {licensee[:50]}...")

conn.close()