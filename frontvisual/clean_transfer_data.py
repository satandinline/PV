"""清洗许可转让数据并创建主题桑基图"""
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

def clean_applicant(name):
    """清理申请人名称"""
    if not name or name == '-' or name == '':
        return None
    # 移除编号前缀如 "1." "2."
    name = re.sub(r'^["\d\.]+\s*', '', str(name).strip())
    name = name.strip('"')
    return name if name and name != '-' else None

def parse_multi_applicants(text):
    """解析多个申请人（用换行或分号分隔）"""
    if not text:
        return []
    # 用换行符、分号或逗号分隔
    parts = re.split(r'[\n;，；,]+', text)
    result = []
    for part in parts:
        cleaned = clean_applicant(part)
        if cleaned:
            result.append(cleaned)
    return result

def create_transfer_clean_table(cursor):
    """创建清洗后的许可转让表"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patent_transfer_clean (
            id INT AUTO_INCREMENT PRIMARY KEY,
            public_number VARCHAR(50) COMMENT '专利号',
            licensor VARCHAR(200) COMMENT '许可人',
            licensee VARCHAR(200) COMMENT '被许可人',
            transfer_type VARCHAR(50) COMMENT '转让类型',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_licensor (licensor),
            INDEX idx_licensee (licensee),
            INDEX idx_public_number (public_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

def build_clean_transfer_data(cursor):
    """构建清洗后的许可转让数据"""
    print("开始清洗许可转让数据...")
    
    # 清空旧数据
    cursor.execute("TRUNCATE TABLE patent_transfer_clean")
    
    # 从专利表获取数据
    cursor.execute("""
        SELECT public_number, licensor, licensee
        FROM patents
        WHERE (licensor IS NOT NULL AND licensor != '' AND licensor != '-')
           OR (licensee IS NOT NULL AND licensee != '' AND licensee != '-')
    """)
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条原始记录")
    
    count = 0
    for row in records:
        public_number, licensor, licensee = row
        
        # 解析许可人
        licensors = parse_multi_applicants(licensor) if licensor else []
        # 解析被许可人
        licensees = parse_multi_applicants(licensee) if licensee else []
        
        # 为每个许可人-被许可人组合创建记录
        for lic in licensors:
            for lic_se in licensees:
                if lic and lic_se and lic != lic_se:
                    cursor.execute("""
                        INSERT INTO patent_transfer_clean (public_number, licensor, licensee, transfer_type)
                        VALUES (%s, %s, %s, '许可')
                    """, (public_number, lic, lic_se))
                    count += 1
    
    print(f"创建了 {count} 条清洗后的记录")
    return count

def create_patent_topic_table(cursor):
    """创建专利主题表"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patent_topics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            public_number VARCHAR(50) COMMENT '专利号',
            topic VARCHAR(100) COMMENT '主题',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_topic (topic),
            INDEX idx_public_number (public_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

def extract_topics(cursor):
    """从标题和摘要提取专利主题"""
    print("开始提取专利主题...")
    
    # 定义主题关键词映射
    topic_mapping = {
        '运动控制': ['控制', '控制方法', '控制系统', '运动控制', '姿态控制', '平衡控制'],
        '关节驱动': ['关节', '驱动', '电机驱动', '伺服', '舵机', '线性执行器'],
        '视觉感知': ['视觉', '感知', '识别', '图像处理', '目标检测', '人脸识别'],
        '导航避障': ['导航', '路径规划', '避障', '定位', 'SLAM', '地图'],
        '灵巧手': ['灵巧手', '机械手', '末端执行器', '抓取', '夹持'],
        '步态行走': ['步态', '行走', '跑步', '跳跃', '双足'],
        '人工智能': ['人工智能', '深度学习', '神经网络', '机器学习', 'AI'],
        '传感感知': ['传感器', '传感', '力传感', '触觉', '姿态传感'],
        '人机交互': ['交互', '人机交互', '语音', '手势', '脑电'],
        '仿生设计': ['仿生', '拟人', '生物启发', '仿人'],
        '结构设计': ['结构', '机构', '连杆', '骨架', '外壳'],
    }
    
    # 提取主题
    cursor.execute("""
        SELECT public_number, title, abstract
        FROM patents
        WHERE title IS NOT NULL AND title != '' AND title != '-'
    """)
    
    records = cursor.fetchall()
    print(f"处理 {len(records)} 条专利")
    
    cursor.execute("TRUNCATE TABLE patent_topics")
    
    count = 0
    for row in records:
        public_number, title, abstract_text = row
        title = title or ''
        abstract_text = abstract_text or ''
        combined = title + ' ' + abstract_text
        
        # 检测主题
        detected_topics = []
        for topic, keywords in topic_mapping.items():
            for kw in keywords:
                if kw in combined:
                    detected_topics.append(topic)
                    break
        
        # 默认主题
        if not detected_topics:
            detected_topics = ['其他技术']
        
        # 取第一个主题作为主主题
        main_topic = detected_topics[0]
        
        cursor.execute("""
            INSERT INTO patent_topics (public_number, topic)
            VALUES (%s, %s)
        """, (public_number, main_topic))
        count += 1
    
    print(f"提取了 {count} 个专利主题")
    
    # 统计主题分布
    cursor.execute("""
        SELECT topic, COUNT(*) as cnt
        FROM patent_topics
        GROUP BY topic
        ORDER BY cnt DESC
    """)
    print("\n主题分布:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    return count

if __name__ == '__main__':
    try:
        with conn.cursor() as cursor:
            # 创建清洗后的转让表
            create_transfer_clean_table(cursor)
            
            # 构建清洗后的转让数据
            build_clean_transfer_data(cursor)
            
            # 创建专利主题表
            create_patent_topic_table(cursor)
            
            # 提取专利主题
            extract_topics(cursor)
            
            conn.commit()
            print("\n数据处理完成!")
    finally:
        conn.close()