"""处理专利数据生成桑基图和网络图所需的数据"""
import pymysql
import os
import re
from dotenv import load_dotenv
load_dotenv()

conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database='patent_analysis',
    charset='utf8mb4'
)

def create_transfer_tables(cursor):
    """创建专利转让网络数据表"""
    # 1. 专利转让表 - 存储转让关系
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patent_transfer (
            id INT AUTO_INCREMENT PRIMARY KEY,
            public_number VARCHAR(50) COMMENT '专利号',
            licensor VARCHAR(200) COMMENT '转让人/许可人',
            licensee VARCHAR(200) COMMENT '受让人/被许可人',
            transfer_date DATE COMMENT '转让日期',
            transfer_type VARCHAR(50) COMMENT '转让类型',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_licensor (licensor),
            INDEX idx_licensee (licensee),
            INDEX idx_public_number (public_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 2. 申请人关系表 - 存储申请人到省份的关系
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applicant_network (
            id INT AUTO_INCREMENT PRIMARY KEY,
            applicant VARCHAR(200) NOT NULL COMMENT '申请人名称',
            province VARCHAR(100) COMMENT '所在省份',
            patent_count INT DEFAULT 0 COMMENT '专利数量',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_applicant (applicant),
            INDEX idx_province (province)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 3. IPC流转表 - 存储IPC分类流转关系
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ipc_flow (
            id INT AUTO_INCREMENT PRIMARY KEY,
            source_ipc VARCHAR(50) COMMENT '源IPC分类',
            target_ipc VARCHAR(50) COMMENT '目标IPC分类',
            flow_count INT DEFAULT 0 COMMENT '流转数量',
            flow_type VARCHAR(50) COMMENT '流转类型(同申请人/跨申请人)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_ipc_flow (source_ipc, target_ipc, flow_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    print("数据表创建完成!")

def clean_applicant_name(name):
    """清理申请人名称，移除编号前缀"""
    if not name:
        return None
    # 移除 "1." "2." 等编号前缀
    cleaned = re.sub(r'^\d+\.\s*', '', str(name).strip())
    return cleaned if cleaned and cleaned != '-' else None

def parse_transfer_data(cursor):
    """解析并存储专利转让数据"""
    print("开始处理专利转让数据...")
    
    # 获取所有有转让信息的专利
    cursor.execute("""
        SELECT public_number, licensor, licensee
        FROM patents
        WHERE (licensor IS NOT NULL AND licensor != '' AND licensor != '-')
           OR (licensee IS NOT NULL AND licensee != '' AND licensee != '-')
    """)
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条专利转让记录")
    
    transfer_count = 0
    for record in records:
        public_number, licensor, licensee = record
        
        # 处理许可人
        if licensor and licensor.strip() and licensor.strip() != '-':
            licensor_list = re.split(r'[\n;，；]', licensor)
            for lic in licensor_list:
                cleaned = clean_applicant_name(lic)
                if cleaned:
                    cursor.execute("""
                        INSERT INTO patent_transfer (public_number, licensor, transfer_type)
                        VALUES (%s, %s, '许可')
                        ON DUPLICATE KEY UPDATE licensor = VALUES(licensor)
                    """, (public_number, cleaned))
                    transfer_count += 1
        
        # 处理被许可人
        if licensee and licensee.strip() and licensee.strip() != '-':
            licensee_list = re.split(r'[\n;，；]', licensee)
            for lic in licensee_list:
                cleaned = clean_applicant_name(lic)
                if cleaned:
                    cursor.execute("""
                        INSERT INTO patent_transfer (public_number, licensee, transfer_type)
                        VALUES (%s, %s, '许可')
                        ON DUPLICATE KEY UPDATE licensee = VALUES(licensee)
                    """, (public_number, cleaned))
                    transfer_count += 1
    
    print(f"成功处理 {transfer_count} 条转让记录")

def build_applicant_network(cursor):
    """构建申请人网络"""
    print("开始构建申请人网络...")
    
    # 从专利表提取申请人信息
    cursor.execute("""
        INSERT INTO applicant_network (applicant, province, patent_count)
        SELECT DISTINCT original_applicant, applicant_province, COUNT(*) as cnt
        FROM patents
        WHERE original_applicant IS NOT NULL AND original_applicant != ''
        GROUP BY original_applicant, applicant_province
        ON DUPLICATE KEY UPDATE patent_count = VALUES(patent_count)
    """)
    
    print("申请人网络构建完成!")

def build_ipc_flow(cursor):
    """构建IPC流转关系 - 分析同一申请人的IPC分布"""
    print("开始构建IPC流转关系...")
    
    # 按申请人统计IPC分类组合
    cursor.execute("""
        SELECT p1.original_applicant, p1.ipc_subclass as source_ipc, p2.ipc_subclass as target_ipc, COUNT(*) as cnt
        FROM patents p1
        JOIN patents p2 ON p1.original_applicant = p2.original_applicant 
            AND p1.public_number != p2.public_number
            AND p1.ipc_subclass != p2.ipc_subclass
        WHERE p1.original_applicant IS NOT NULL 
            AND p1.original_applicant != ''
            AND p1.ipc_subclass IS NOT NULL 
            AND p1.ipc_subclass != '-'
            AND p2.ipc_subclass IS NOT NULL 
            AND p2.ipc_subclass != '-'
        GROUP BY p1.original_applicant, p1.ipc_subclass, p2.ipc_subclass
        HAVING cnt >= 2
        ORDER BY cnt DESC
        LIMIT 500
    """)
    
    results = cursor.fetchall()
    print(f"找到 {len(results)} 条IPC流转关系")
    
    for row in results:
        cursor.execute("""
            INSERT INTO ipc_flow (source_ipc, target_ipc, flow_count, flow_type)
            VALUES (%s, %s, %s, '同申请人')
            ON DUPLICATE KEY UPDATE flow_count = VALUES(flow_count)
        """, (row[1], row[2], row[3]))
    
    print("IPC流转关系构建完成!")

def generate_sankey_data(cursor):
    """生成桑基图数据 - 专利类型流转"""
    print("生成专利类型流转桑基图数据...")
    
    # 统计从申请到各状态的流转
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
    """)
    
    return cursor.fetchall()

def generate_transfer_network_data(cursor):
    """生成转让网络图数据"""
    print("生成转让网络图数据...")
    
    # 统计转让关系
    cursor.execute("""
        SELECT 
            licensor,
            licensee,
            COUNT(*) as transfer_count
        FROM patent_transfer
        WHERE licensor IS NOT NULL AND licensor != ''
            AND licensee IS NOT NULL AND licensee != ''
            AND licensor != licensee
        GROUP BY licensor, licensee
        ORDER BY transfer_count DESC
        LIMIT 200
    """)
    
    return cursor.fetchall()

if __name__ == '__main__':
    try:
        with conn.cursor() as cursor:
            # 创建表
            create_transfer_tables(cursor)
            
            # 处理数据
            parse_transfer_data(cursor)
            conn.commit()
            
            build_applicant_network(cursor)
            conn.commit()
            
            build_ipc_flow(cursor)
            conn.commit()
            
            # 生成桑基图数据
            sankey_data = generate_sankey_data(cursor)
            print("\n=== 专利类型流转数据 ===")
            for row in sankey_data[:20]:
                print(f"{row[0]} -> {row[1]}: {row[2]}")
            
            # 生成转让网络数据
            transfer_data = generate_transfer_network_data(cursor)
            print("\n=== 专利转让网络数据 (Top 20) ===")
            for row in transfer_data[:20]:
                print(f"{row[0]} -> {row[1]}: {row[2]}")
            
        print("\n数据处理完成!")
    finally:
        conn.close()