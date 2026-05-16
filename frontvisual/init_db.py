"""
数据库初始化脚本
创建专利分析所需的数据库表结构
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """初始化数据库和表结构"""
    
    # 连接MySQL
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute("CREATE DATABASE IF NOT EXISTS patent_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("USE patent_analysis")
            
            # 1. 专利表 - 存储专利详细信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    public_number VARCHAR(50) COMMENT '公开(公告)号',
                    title VARCHAR(500) COMMENT '标题',
                    abstract TEXT COMMENT '摘要',
                    applicant_city VARCHAR(100) COMMENT '当前申请(专利权)人地市',
                    applicant_province VARCHAR(100) COMMENT '当前申请(专利权)人州/省',
                    original_applicant VARCHAR(200) COMMENT '原始申请(专利权)人',
                    application_date DATE COMMENT '申请日',
                    ipc_subgroup VARCHAR(50) COMMENT 'IPC主分类号(小组)',
                    ipc_subgroup_desc VARCHAR(500) COMMENT 'IPC主分类号(小组)释义',
                    cited_patents TEXT COMMENT '被引用专利',
                    citing_patents TEXT COMMENT '引用专利',
                    citations_5yr INT DEFAULT 0 COMMENT '5年内被引用数量',
                    citations_3yr INT DEFAULT 0 COMMENT '3年内被引用数量',
                    family_count INT DEFAULT 1 COMMENT 'Patsnap同族专利申请数量',
                    patent_type VARCHAR(50) COMMENT '专利类型',
                    licensor VARCHAR(200) COMMENT '许可人',
                    licensee VARCHAR(200) COMMENT '被许可人',
                    legal_status VARCHAR(100) COMMENT '法律状态/事件',
                    applicant_district VARCHAR(100) COMMENT '当前申请(专利权)人区县',
                    expiry_date DATE COMMENT '预估到期日',
                    receiving_office VARCHAR(50) COMMENT '受理局',
                    abstract_zh TEXT COMMENT '摘要(译)(简体中文)',
                    title_zh VARCHAR(500) COMMENT '标题(译)(简体中文)',
                    ipc_main_group_desc VARCHAR(500) COMMENT 'IPC主分类号(大组)释义',
                    ipc_main_group VARCHAR(50) COMMENT 'IPC主分类号(大组)',
                    ipc_subclass VARCHAR(50) COMMENT 'IPC主分类号(小类)',
                    ipc_subclass_desc VARCHAR(500) COMMENT 'IPC主分类号(小类)释义',
                    grant_date DATE COMMENT '授权日',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_public_number (public_number),
                    INDEX idx_province (applicant_province),
                    INDEX idx_city (applicant_city),
                    INDEX idx_ipc (ipc_subclass),
                    INDEX idx_type (patent_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 2. 对话会话表 - 存储每次对话会话
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    public_number VARCHAR(50) COMMENT '关联的专利号',
                    session_title VARCHAR(200) DEFAULT '新对话' COMMENT '会话标题',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (public_number) REFERENCES patents(public_number) ON DELETE CASCADE,
                    INDEX idx_public_number (public_number)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 3. 对话消息表 - 存储每轮对话
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id INT NOT NULL,
                    message_order INT NOT NULL COMMENT '消息序号',
                    role VARCHAR(20) NOT NULL COMMENT '角色: user/assistant/system',
                    content TEXT NOT NULL COMMENT '消息内容',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    INDEX idx_session (session_id),
                    INDEX idx_order (message_order)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 4. AI总结表 - 存储AI对专利的总结
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patent_summaries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    public_number VARCHAR(50) NOT NULL,
                    summary_type VARCHAR(50) DEFAULT 'default' COMMENT '总结类型',
                    summary_content TEXT COMMENT 'AI总结内容',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (public_number) REFERENCES patents(public_number) ON DELETE CASCADE,
                    INDEX idx_public_number (public_number)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 5. 省份统计表 - 存储省份专利统计（用于地图热力图）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS province_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    province_name VARCHAR(100) NOT NULL COMMENT '省份名称',
                    patent_count INT DEFAULT 0 COMMENT '专利数量',
                    geo_code VARCHAR(50) COMMENT '行政区划代码',
                    latitude DECIMAL(10, 6) COMMENT '中心纬度',
                    longitude DECIMAL(10, 6) COMMENT '中心经度',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_province (province_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 6. 城市统计表 - 存储城市专利统计
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS city_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    province_name VARCHAR(100) NOT NULL COMMENT '所属省份',
                    city_name VARCHAR(100) NOT NULL COMMENT '城市名称',
                    patent_count INT DEFAULT 0 COMMENT '专利数量',
                    geo_code VARCHAR(50) COMMENT '行政区划代码',
                    latitude DECIMAL(10, 6) COMMENT '中心纬度',
                    longitude DECIMAL(10, 6) COMMENT '中心经度',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_province (province_name),
                    UNIQUE KEY uk_city (province_name, city_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            connection.commit()
            print("数据库初始化成功!")
            
            # 初始化省份统计数据
            init_province_stats(cursor)
            connection.commit()
            
    finally:
        connection.close()


def init_province_stats(cursor):
    """初始化省份统计数据"""
    
    # 中国省份数据（包含GeoJSON兼容的名称映射）
    provinces = {
        '北京': {'code': '110000', 'lat': 39.9042, 'lng': 116.4074},
        '天津': {'code': '120000', 'lat': 39.3434, 'lng': 117.3616},
        '河北': {'code': '130000', 'lat': 38.0375, 'lng': 114.5146},
        '山西': {'code': '140000', 'lat': 37.8706, 'lng': 112.5489},
        '内蒙古': {'code': '150000', 'lat': 40.8180, 'lng': 111.6703},
        '辽宁': {'code': '210000', 'lat': 41.7968, 'lng': 123.4315},
        '吉林': {'code': '220000', 'lat': 43.8868, 'lng': 125.3245},
        '黑龙江': {'code': '230000', 'lat': 45.7561, 'lng': 126.6421},
        '上海': {'code': '310000', 'lat': 31.2304, 'lng': 121.4737},
        '江苏': {'code': '320000', 'lat': 32.0603, 'lng': 118.7969},
        '浙江': {'code': '330000', 'lat': 30.2741, 'lng': 120.1551},
        '安徽': {'code': '340000', 'lat': 31.8612, 'lng': 117.2830},
        '福建': {'code': '350000', 'lat': 26.0745, 'lng': 119.2965},
        '江西': {'code': '360000', 'lat': 28.6820, 'lng': 115.8581},
        '山东': {'code': '370000', 'lat': 36.6512, 'lng': 117.1201},
        '河南': {'code': '410000', 'lat': 34.7656, 'lng': 113.7536},
        '湖北': {'code': '420000', 'lat': 30.5928, 'lng': 114.3055},
        '湖南': {'code': '430000', 'lat': 28.2280, 'lng': 112.9388},
        '广东': {'code': '440000', 'lat': 23.1291, 'lng': 113.2644},
        '广西': {'code': '450000', 'lat': 22.8170, 'lng': 108.3665},
        '海南': {'code': '460000', 'lat': 20.0444, 'lng': 110.1999},
        '重庆': {'code': '500000', 'lat': 29.5630, 'lng': 106.5516},
        '四川': {'code': '510000', 'lat': 30.6722, 'lng': 104.0659},
        '贵州': {'code': '520000', 'lat': 26.5984, 'lng': 106.7073},
        '云南': {'code': '530000', 'lat': 25.0453, 'lng': 102.7097},
        '西藏': {'code': '540000', 'lat': 29.6470, 'lng': 91.1174},
        '陕西': {'code': '610000', 'lat': 34.2656, 'lng': 108.9542},
        '甘肃': {'code': '620000', 'lat': 36.0611, 'lng': 103.8343},
        '青海': {'code': '630000', 'lat': 36.6232, 'lng': 101.7782},
        '宁夏': {'code': '640000', 'lat': 38.4872, 'lng': 106.2309},
        '新疆': {'code': '650000', 'lat': 43.7930, 'lng': 87.6177},
        '台湾': {'code': '710000', 'lat': 25.0330, 'lng': 121.5654},
        '香港': {'code': '810000', 'lat': 22.3193, 'lng': 114.1694},
        '澳门': {'code': '820000', 'lat': 22.1987, 'lng': 113.5439},
    }
    
    for province, data in provinces.items():
        cursor.execute("""
            INSERT INTO province_stats (province_name, geo_code, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE geo_code = VALUES(geo_code),
                                   latitude = VALUES(latitude),
                                   longitude = VALUES(longitude)
        """, (province, data['code'], data['lat'], data['lng']))
    
    print("省份统计数据初始化完成!")


def import_patents_from_csv(csv_path):
    """从CSV文件导入专利数据"""
    import pandas as pd
    
    # 读取CSV
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    # 过滤标题行
    df = df[df['专利类型'] != '专利类型'].copy()
    
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database='patent_analysis',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 批量插入专利数据
            for _, row in df.iterrows():
                # 处理日期字段
                def parse_date(val):
                    if val and str(val).strip() and str(val).strip() != '-':
                        try:
                            return pd.to_datetime(val).strftime('%Y-%m-%d')
                        except:
                            return None
                    return None
                            
                row_data = {
                    'public_number': str(row.get('公开(公告)号', ''))[:50],
                    'title': str(row.get('标题', ''))[:500],
                    'abstract': str(row.get('摘要', ''))[:5000],
                    'applicant_city': str(row.get('当前申请(专利权)人地市', ''))[:100],
                    'applicant_province': str(row.get('当前申请(专利权)人州/省', ''))[:100],
                    'original_applicant': str(row.get('原始申请(专利权)人', ''))[:200],
                    'application_date': parse_date(row.get('申请日', '')),
                    'ipc_subgroup': str(row.get('IPC主分类号(小组)', ''))[:50],
                    'ipc_subgroup_desc': str(row.get('IPC主分类号(小组)释义', ''))[:500],
                    'cited_patents': str(row.get('被引用专利', ''))[:2000],
                    'citing_patents': str(row.get('引用专利', ''))[:2000],
                    'citations_5yr': int(row.get('5年内被引用数量', 0)) if str(row.get('5年内被引用数量', 0)).isdigit() else 0,
                    'citations_3yr': int(row.get('3年内被引用数量', 0)) if str(row.get('3年内被引用数量', 0)).isdigit() else 0,
                    'family_count': int(row.get('Patsnap同族专利申请数量', 1)) if str(row.get('Patsnap同族专利申请数量', 1)).isdigit() else 1,
                    'patent_type': str(row.get('专利类型', ''))[:50],
                    'licensor': str(row.get('许可人', ''))[:200],
                    'licensee': str(row.get('被许可人', ''))[:200],
                    'legal_status': str(row.get('法律状态/事件', ''))[:100],
                    'applicant_district': str(row.get('当前申请(专利权)人区县', ''))[:100],
                    'expiry_date': parse_date(row.get('预估到期日', '')),
                    'receiving_office': str(row.get('受理局', ''))[:50],
                    'abstract_zh': str(row.get('摘要(译)(简体中文)', ''))[:5000],
                    'title_zh': str(row.get('标题(译)(简体中文)', ''))[:500],
                    'ipc_main_group_desc': str(row.get('IPC主分类号(大组)释义', ''))[:500],
                    'ipc_main_group': str(row.get('IPC主分类号(大组)', ''))[:50],
                    'ipc_subclass': str(row.get('IPC主分类号(小类)', ''))[:50],
                    'ipc_subclass_desc': str(row.get('IPC主分类号(小类)释义', ''))[:500],
                    'grant_date': parse_date(row.get('授权日', ''))
                }
                            
                cursor.execute("""
                    INSERT INTO patents (
                        public_number, title, abstract, applicant_city, applicant_province,
                        original_applicant, application_date, ipc_subgroup, ipc_subgroup_desc,
                        cited_patents, citing_patents, citations_5yr, citations_3yr, family_count,
                        patent_type, licensor, licensee, legal_status, applicant_district,
                        expiry_date, receiving_office, abstract_zh, title_zh,
                        ipc_main_group_desc, ipc_main_group, ipc_subclass, ipc_subclass_desc, grant_date
                    ) VALUES (
                        %(public_number)s, %(title)s, %(abstract)s, %(applicant_city)s, %(applicant_province)s,
                        %(original_applicant)s, %(application_date)s, %(ipc_subgroup)s, %(ipc_subgroup_desc)s,
                        %(cited_patents)s, %(citing_patents)s, %(citations_5yr)s, %(citations_3yr)s, %(family_count)s,
                        %(patent_type)s, %(licensor)s, %(licensee)s, %(legal_status)s, %(applicant_district)s,
                        %(expiry_date)s, %(receiving_office)s, %(abstract_zh)s, %(title_zh)s,
                        %(ipc_main_group_desc)s, %(ipc_main_group)s, %(ipc_subclass)s, %(ipc_subclass_desc)s, %(grant_date)s
                    )
                    ON DUPLICATE KEY UPDATE title = VALUES(title)
                """, row_data)
            
            connection.commit()
            
            # 更新省份统计
            update_province_stats(cursor)
            # 更新城市统计
            update_city_stats(cursor)
            connection.commit()
            
            print(f"成功导入 {len(df)} 条专利数据!")
            
    finally:
        connection.close()


def update_province_stats(cursor):
    """更新省份统计数据"""
    cursor.execute("""
        UPDATE province_stats ps
        SET patent_count = (
            SELECT COUNT(*) FROM patents p 
            WHERE p.applicant_province = ps.province_name
        )
    """)


def update_city_stats(cursor):
    """更新城市统计数据"""
    cursor.execute("""
        INSERT INTO city_stats (province_name, city_name, patent_count)
        SELECT applicant_province, applicant_city, COUNT(*) as cnt
        FROM patents
        WHERE applicant_city IS NOT NULL AND applicant_city != ''
        GROUP BY applicant_province, applicant_city
        ON DUPLICATE KEY UPDATE patent_count = VALUES(patent_count)
    """)


if __name__ == '__main__':
    init_database()
    import_patents_from_csv('d:/git/mygit/PV/data.csv')