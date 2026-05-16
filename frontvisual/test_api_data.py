"""测试API数据"""
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

# 测试法律状态流转API
print('=== 测试法律状态流转数据 ===')
cursor.execute("""
    SELECT 
        CASE 
            WHEN patent_type LIKE '%发明申请%' THEN '发明申请'
            WHEN patent_type LIKE '%授权发明%' THEN '授权发明'
            WHEN patent_type LIKE '%实用新型%' THEN '实用新型'
            WHEN patent_type LIKE '%外观设计%' THEN '外观设计'
            ELSE patent_type
        END as patent_type,
        legal_status,
        COUNT(*) as count
    FROM patents
    WHERE patent_type IS NOT NULL AND patent_type != ''
    GROUP BY patent_type, legal_status
    HAVING count >= 2
    ORDER BY count DESC
    LIMIT 10
""")
results = cursor.fetchall()
print(f'找到 {len(results)} 条数据')
for r in results:
    print(f"{r['patent_type']} -> {r['legal_status']}: {r['count']}")

# 测试省份流转网络API
print('\n=== 测试省份流转网络数据 ===')
cursor.execute("""
    SELECT p1.applicant_province as source, p2.applicant_province as target, COUNT(*) as cnt
    FROM patents p1
    JOIN patents p2 ON p1.original_applicant = p2.original_applicant 
        AND p1.public_number != p2.public_number
        AND p1.applicant_province != p2.applicant_province
    WHERE p1.original_applicant IS NOT NULL AND p1.original_applicant != ''
        AND p1.applicant_province IS NOT NULL AND p1.applicant_province != '-'
        AND p2.applicant_province IS NOT NULL AND p2.applicant_province != '-'
    GROUP BY p1.applicant_province, p2.applicant_province
    HAVING cnt >= 50
    ORDER BY cnt DESC
    LIMIT 20
""")
results = cursor.fetchall()
print(f'找到 {len(results)} 条数据')
for r in results:
    print(f"{r['source']} -> {r['target']}: {r['cnt']}")

# 测试IPC流转API
print('\n=== 测试IPC流转数据 ===')
cursor.execute("""
    SELECT source_ipc, target_ipc, flow_count
    FROM ipc_flow
    WHERE flow_count >= 5
    ORDER BY flow_count DESC
    LIMIT 10
""")
results = cursor.fetchall()
print(f'找到 {len(results)} 条数据')
for r in results:
    print(f"{r['source_ipc']} -> {r['target_ipc']}: {r['flow_count']}")

conn.close()