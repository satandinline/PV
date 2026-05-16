"""
使用Qwen API对专利标题和摘要进行主题提取
定时任务或手动触发运行
"""
import pymysql
import os
import time
import json
import requests
from dotenv import load_dotenv
from queue import Queue
from threading import Thread

load_dotenv()

# API配置
API_KEY = os.getenv('DASHSCOPE_API_KEY')
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-turbo"

# 预定义主题分类
TOPICS = [
    "运动控制", "关节驱动", "视觉感知", "导航避障", 
    "传感感知", "人工智能", "人机交互", "仿生设计",
    "步态行走", "结构设计", "灵巧手", "其他技术"
]

# 主题关键词映射
TOPIC_KEYWORDS = {
    "运动控制": ["控制", "控制算法", "运动规划", "轨迹", "参数控制", "自适应控制", "模糊控制", "pid"],
    "关节驱动": ["关节", "驱动", "电机", "伺服", "扭矩", "力矩", "执行器", "减速器"],
    "视觉感知": ["视觉", "图像", "摄像头", "识别", "检测", "目标跟踪", "特征提取", "深度学习"],
    "导航避障": ["导航", "定位", "避障", "路径规划", "地图", " slam", "自主导航", "自主移动"],
    "传感感知": ["传感器", "传感", "感知", "探测", "测量", "检测", "信号采集"],
    "人工智能": ["人工智能", "机器学习", "神经网络", "深度学习", "ai", "算法", "智能决策"],
    "人机交互": ["交互", "人机", "语音", "手势", "界面", "通信", "遥控", "遥操作"],
    "仿生设计": ["仿生", "仿人", "仿生学", "生物启发", "人形", "动物形态"],
    "步态行走": ["步态", "行走", "跑步", "跳跃", "平衡", "步行", "双足"],
    "结构设计": ["结构", "设计", "本体", "机身", "关节结构", "机械结构", "轻量化"],
    "灵巧手": ["灵巧手", "机械手", "末端执行器", "夹持", "抓取", "手部", "手指"]
}


def extract_topic_by_keywords(title, abstract):
    """基于关键词提取主题"""
    if not title and not abstract:
        return "其他技术"
    
    text = f"{title or ''} {abstract or ''}".lower()
    scores = {}
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in text:
                score += 1
        if score > 0:
            scores[topic] = score
    
    if scores:
        return max(scores, key=scores.get)
    return "其他技术"


def extract_topic_by_api(title, abstract):
    """使用Qwen API提取主题"""
    try:
        text = f"标题：{title or '无'}\n摘要：{abstract or '无'}"
        prompt = f"""你是一个专利主题分类专家。请根据以下专利的标题和摘要，判断它属于哪个技术主题。

可选主题（只能选一个）：
{', '.join(TOPICS)}

专利信息：
{text[:500]}

直接输出主题名称，不要解释。"""

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        resp = requests.post(API_URL, headers=headers, json=data, timeout=10)
        result = resp.json()
        
        if 'choices' in result and result['choices']:
            topic = result['choices'][0]['message']['content'].strip()
            # 验证主题是否有效
            for t in TOPICS:
                if t in topic:
                    return t
        return "其他技术"
    except Exception as e:
        print(f"API调用失败: {e}")
        return None


def process_batch(batch, use_api=True):
    """处理一批专利的主题提取"""
    results = []
    for row in batch:
        public_number = row[0]
        title = row[1]
        abstract = row[2]
        
        if use_api and API_KEY:
            topic = extract_topic_by_api(title, abstract)
            if topic is None:
                topic = extract_topic_by_keywords(title, abstract)
        else:
            topic = extract_topic_by_keywords(title, abstract)
        
        results.append((public_number, topic))
    
    return results


def update_topics(results, conn):
    """更新数据库中的主题"""
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute("TRUNCATE TABLE patent_topics")
    
    # 批量插入
    sql = "INSERT INTO patent_topics (public_number, topic) VALUES (%s, %s)"
    cursor.executemany(sql, results)
    conn.commit()
    cursor.close()


def main():
    print("=== 专利主题提取工具 ===")
    
    # 检查API配置
    use_api = bool(API_KEY)
    print(f"使用Qwen API: {'是' if use_api else '否'}")
    
    # 连接数据库
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database='patent_analysis',
        charset='utf8mb4'
    )
    
    # 获取需要处理的专利
    cursor = conn.cursor()
    cursor.execute("""
        SELECT public_number, title, abstract 
        FROM patents 
        WHERE title IS NOT NULL AND title != ''
        LIMIT 15000
    """)
    patents = cursor.fetchall()
    cursor.close()
    
    print(f"需要处理 {len(patents)} 条专利...")
    
    # 分批处理
    batch_size = 50
    all_results = []
    
    for i in range(0, len(patents), batch_size):
        batch = patents[i:i+batch_size]
        print(f"处理 {min(i+batch_size, len(patents))}/{len(patents)}...")
        
        results = process_batch(batch, use_api=use_api)
        all_results.extend(results)
        
        # 避免API限流
        if use_api and (i + batch_size) < len(patents):
            time.sleep(0.5)
    
    # 更新数据库
    print("更新数据库...")
    update_topics(all_results, conn)
    
    # 统计结果
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic, COUNT(*) as cnt 
        FROM patent_topics 
        GROUP BY topic 
        ORDER BY cnt DESC
    """)
    print("\n=== 主题分布 ===")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n完成！")


if __name__ == "__main__":
    main()