"""
API服务 - 提供专利数据和AI对话接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
import json
import urllib.request

load_dotenv()

app = Flask(__name__)
CORS(app)

# 高德地图API配置
GAODE_API_KEY = os.getenv('GAODE_API_KEY', '')

# 根路由 - 返回HTML页面
@app.route('/')
def index():
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    return send_file(html_path)

# 获取高德地图行政区划GeoJSON
@app.route('/api/map/geojson', methods=['GET'])
def get_map_geojson():
    """获取中国省份GeoJSON数据 - 使用阿里云DataV API"""
    try:
        # 直接使用阿里云DataV的GeoJSON API（免key）
        url = 'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            geojson = json.loads(response.read().decode('utf-8'))
        
        # 转换格式确保兼容性
        if geojson.get('type') == 'FeatureCollection' and geojson.get('features'):
            return jsonify({
                'success': True,
                'data': geojson
            })
        else:
            raise ValueError('Invalid GeoJSON structure')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 数据库连接
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database='patent_analysis',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    """获取省份统计数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT province_name, patent_count, latitude, longitude, geo_code
                FROM province_stats
                WHERE patent_count > 0
                ORDER BY patent_count DESC
            """)
            result = cursor.fetchall()
            return jsonify({
                'success': True,
                'data': result
            })
    finally:
        conn.close()


@app.route('/api/cities/<province>', methods=['GET'])
def get_cities(province):
    """获取指定省份的城市统计数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT city_name, patent_count, latitude, longitude, geo_code
                FROM city_stats
                WHERE province_name = %s AND patent_count > 0
                ORDER BY patent_count DESC
            """, (province,))
            result = cursor.fetchall()
            return jsonify({
                'success': True,
                'data': result
            })
    finally:
        conn.close()


@app.route('/api/patents/province/<province>', methods=['GET'])
def get_patents_by_province(province):
    """获取指定省份的专利列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    sort = request.args.get('sort', 'date_desc')  # date_desc, date_asc, citations
    
    # 排序方式
    order_by = {
        'date_desc': 'application_date DESC',
        'date_asc': 'application_date ASC',
        'citations': 'citations_5yr DESC'
    }.get(sort, 'application_date DESC')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 获取总数
            cursor.execute("SELECT COUNT(*) as total FROM patents WHERE applicant_province = %s", (province,))
            total = cursor.fetchone()['total']
            
            # 获取专利列表
            offset = (page - 1) * page_size
            cursor.execute(f"""
                SELECT public_number, title, applicant_city, application_date, 
                       patent_type, ipc_subclass, citations_5yr
                FROM patents
                WHERE applicant_province = %s
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """, (province, page_size, offset))
            patents = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': patents,
                'total': total,
                'page': page,
                'page_size': page_size
            })
    finally:
        conn.close()


@app.route('/api/patents/city/<province>/<city>', methods=['GET'])
def get_patents_by_city(province, city):
    """获取指定城市的专利列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    sort = request.args.get('sort', 'date_desc')
    
    order_by = {
        'date_desc': 'application_date DESC',
        'date_asc': 'application_date ASC',
        'citations': 'citations_5yr DESC'
    }.get(sort, 'application_date DESC')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM patents WHERE applicant_province = %s AND applicant_city = %s", (province, city))
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            cursor.execute(f"""
                SELECT public_number, title, applicant_city, application_date,
                       patent_type, ipc_subclass, citations_5yr
                FROM patents
                WHERE applicant_province = %s AND applicant_city = %s
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """, (province, city, page_size, offset))
            patents = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': patents,
                'total': total,
                'page': page,
                'page_size': page_size
            })
    finally:
        conn.close()


@app.route('/api/patent/<public_number>', methods=['GET'])
def get_patent_detail(public_number):
    """获取专利详细信息"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM patents WHERE public_number = %s
            """, (public_number,))
            patent = cursor.fetchone()
            
            if patent:
                # 转换日期格式
                for key in ['application_date', 'expiry_date', 'grant_date']:
                    if patent.get(key):
                        patent[key] = patent[key].isoformat() if hasattr(patent[key], 'isoformat') else str(patent[key])
                return jsonify({
                    'success': True,
                    'data': patent
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Patent not found'
                }), 404
    finally:
        conn.close()


@app.route('/api/patent/<public_number>/summary', methods=['GET'])
def get_patent_summary(public_number):
    """获取专利AI总结"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 先检查数据库中是否有缓存的总结
            cursor.execute("""
                SELECT summary_content FROM patent_summaries 
                WHERE public_number = %s AND summary_type = 'default'
            """, (public_number,))
            cached = cursor.fetchone()
            
            if cached and cached['summary_content']:
                return jsonify({
                    'success': True,
                    'data': {'summary': cached['summary_content']}
                })
            
            # 如果没有缓存，获取专利信息并生成总结
            cursor.execute("SELECT * FROM patents WHERE public_number = %s", (public_number,))
            patent = cursor.fetchone()
            
            if not patent:
                return jsonify({'success': False, 'message': 'Patent not found'}), 404
            
            # 生成AI总结
            summary = generate_ai_summary(patent)
            
            # 保存到数据库
            cursor.execute("""
                INSERT INTO patent_summaries (public_number, summary_type, summary_content)
                VALUES (%s, 'default', %s)
                ON DUPLICATE KEY UPDATE summary_content = VALUES(summary_content)
            """, (public_number, summary))
            conn.commit()
            
            return jsonify({
                'success': True,
                'data': {'summary': summary}
            })
    finally:
        conn.close()


def generate_ai_summary(patent):
    """使用AI生成专利总结"""
    import urllib.request
    import urllib.parse
    
    prompt = f"""请对以下专利进行简要总结（200字以内）：

标题：{patent.get('title', '')}
摘要：{patent.get('abstract', '')}
申请人：{patent.get('original_applicant', '')}
申请日期：{patent.get('application_date', '')}
专利类型：{patent.get('patent_type', '')}
IPC分类：{patent.get('ipc_subclass', '')} - {patent.get('ipc_subclass_desc', '')}

请从技术领域、创新点、应用场景三个方面简要总结。"""
    
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            'Authorization': f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'qwen-plus',
            'messages': [
                {'role': 'system', 'content': '你是一个专业的专利分析助手，擅长总结和分析专利技术。'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 500
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"AI summary error: {e}")
        return f"专利{patent.get('public_number', '')}总结生成失败"


@app.route('/api/chat/session', methods=['POST'])
def create_chat_session():
    """创建新的对话会话"""
    data = request.get_json()
    public_number = data.get('public_number')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 创建新会话
            cursor.execute("""
                INSERT INTO chat_sessions (public_number, session_title)
                VALUES (%s, %s)
            """, (public_number, f"专利 {public_number} 对话"))
            session_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'success': True,
                'data': {'session_id': session_id}
            })
    finally:
        conn.close()


@app.route('/api/chat/<int:session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """获取对话消息历史"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, role, content, message_order, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY message_order ASC
            """, (session_id,))
            messages = cursor.fetchall()
            
            # 转换时间格式
            for msg in messages:
                if msg.get('created_at'):
                    msg['created_at'] = msg['created_at'].isoformat()
            
            return jsonify({
                'success': True,
                'data': messages
            })
    finally:
        conn.close()


@app.route('/api/chat/<int:session_id>/send', methods=['POST'])
def send_chat_message(session_id):
    """发送聊天消息并获取AI回复"""
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 获取会话关联的专利信息
            cursor.execute("SELECT public_number FROM chat_sessions WHERE id = %s", (session_id,))
            session = cursor.fetchone()
            
            if not session:
                return jsonify({'success': False, 'message': 'Session not found'}), 404
            
            public_number = session['public_number']
            
            # 获取专利详细信息用于上下文
            cursor.execute("SELECT * FROM patents WHERE public_number = %s", (public_number,))
            patent = cursor.fetchone()
            
            # 获取之前的对话历史
            cursor.execute("""
                SELECT role, content FROM chat_messages
                WHERE session_id = %s
                ORDER BY message_order ASC
            """, (session_id,))
            history = cursor.fetchall()
            
            # 构建AI回复
            ai_response = chat_with_ai(patent, user_message, history)
            
            # 保存用户消息
            cursor.execute("""
                INSERT INTO chat_messages (session_id, message_order, role, content)
                SELECT %s, COALESCE(MAX(message_order), 0) + 1, 'user', %s
                FROM chat_messages WHERE session_id = %s
            """, (session_id, user_message, session_id))
            
            # 保存AI回复
            cursor.execute("""
                INSERT INTO chat_messages (session_id, message_order, role, content)
                SELECT %s, COALESCE(MAX(message_order), 0) + 1, 'assistant', %s
                FROM chat_messages WHERE session_id = %s
            """, (session_id, ai_response, session_id))
            
            # 更新会话时间
            cursor.execute("UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s", (session_id,))
            
            conn.commit()
            
            # 获取新消息的ID
            cursor.execute("""
                SELECT id, message_order FROM chat_messages
                WHERE session_id = %s ORDER BY message_order DESC LIMIT 2
            """, (session_id,))
            recent = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'user_message': {'id': recent[1]['id'], 'content': user_message},
                    'ai_response': {'id': recent[0]['id'], 'content': ai_response}
                }
            })
    finally:
        conn.close()


def chat_with_ai(patent, user_message, history):
    """与AI进行对话"""
    import urllib.request
    import urllib.parse
    
    # 构建专利上下文
    patent_context = f"""专利信息：
- 专利号：{patent.get('public_number', '')}
- 标题：{patent.get('title', '')}
- 摘要：{patent.get('abstract', '')}
- 申请人：{patent.get('original_applicant', '')}
- 申请日期：{patent.get('application_date', '')}
- 专利类型：{patent.get('patent_type', '')}
- 法律状态：{patent.get('legal_status', '')}
- IPC分类：{patent.get('ipc_subclass', '')} - {patent.get('ipc_subclass_desc', '')}
- 被引用次数（5年内）：{patent.get('citations_5yr', 0)}
"""
    
    # 构建消息历史
    messages = [
        {'role': 'system', 'content': '你是一个专业的专利分析助手，擅长分析专利技术、解答用户关于专利的问题。请基于提供的专利信息回答用户的问题。'},
        {'role': 'user', 'content': patent_context}
    ]
    
    # 添加历史对话
    for h in history:
        role = 'user' if h['role'] == 'user' else 'assistant'
        messages.append({'role': role, 'content': h['content']})
    
    # 添加当前用户消息
    messages.append({'role': 'user', 'content': user_message})
    
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            'Authorization': f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'qwen-plus',
            'messages': messages,
            'max_tokens': 1000
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Chat error: {e}")
        return f"抱歉，AI服务暂时不可用。请稍后再试。错误信息: {str(e)}"


@app.route('/api/stats/overview', methods=['GET'])
def get_overview_stats():
    """获取总体统计数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 总专利数
            cursor.execute("SELECT COUNT(*) as total FROM patents")
            total = cursor.fetchone()['total']
            
            # 专利类型分布
            cursor.execute("""
                SELECT patent_type, COUNT(*) as count
                FROM patents GROUP BY patent_type ORDER BY count DESC
            """)
            types = cursor.fetchall()
            
            # 法律状态分布
            cursor.execute("""
                SELECT legal_status, COUNT(*) as count
                FROM patents GROUP BY legal_status ORDER BY count DESC LIMIT 10
            """)
            statuses = cursor.fetchall()
            
            # IPC分类Top10
            cursor.execute("""
                SELECT ipc_subclass, COUNT(*) as count
                FROM patents GROUP BY ipc_subclass ORDER BY count DESC LIMIT 10
            """)
            ipc = cursor.fetchall()
            
            # 年份分布
            cursor.execute("""
                SELECT YEAR(application_date) as year, COUNT(*) as count
                FROM patents
                WHERE application_date IS NOT NULL
                GROUP BY YEAR(application_date)
                ORDER BY year DESC LIMIT 20
            """)
            years = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'data': {
                    'total_patents': total,
                    'patent_types': types,
                    'legal_statuses': statuses,
                    'ipc_distribution': ipc,
                    'year_distribution': years
                }
            })
    finally:
        conn.close()


# 统计API
@app.route('/api/stats/patent-types', methods=['GET'])
def get_patent_types_stats():
    """获取专利类型统计"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT patent_type, COUNT(*) as count
                FROM patents GROUP BY patent_type ORDER BY count DESC
            """)
            result = cursor.fetchall()
            return jsonify({'success': True, 'data': result})
    finally:
        conn.close()


@app.route('/api/stats/ipc', methods=['GET'])
def get_ipc_stats():
    """获取IPC分类统计"""
    limit = request.args.get('limit', 15, type=int)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT ipc_subclass, ipc_subclass_desc, COUNT(*) as count
                FROM patents
                WHERE ipc_subclass IS NOT NULL AND ipc_subclass != '-'
                GROUP BY ipc_subclass, ipc_subclass_desc
                ORDER BY count DESC LIMIT %s
            """, (limit,))
            result = cursor.fetchall()
            return jsonify({'success': True, 'data': result})
    finally:
        conn.close()


@app.route('/api/stats/years', methods=['GET'])
def get_years_stats():
    """获取年份统计"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT YEAR(application_date) as year, COUNT(*) as count
                FROM patents
                WHERE application_date IS NOT NULL
                GROUP BY YEAR(application_date)
                ORDER BY year ASC
            """)
            result = cursor.fetchall()
            return jsonify({'success': True, 'data': result})
    finally:
        conn.close()


@app.route('/api/stats/citations', methods=['GET'])
def get_citations_stats():
    """获取引用统计"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT citations_5yr, citations_3yr, family_count
                FROM patents
            """)
            results = cursor.fetchall()
            
            # 计算统计
            citations_5yr = [r['citations_5yr'] for r in results if r['citations_5yr']]
            citations_3yr = [r['citations_3yr'] for r in results if r['citations_3yr']]
            family = [r['family_count'] for r in results if r['family_count']]
            
            import numpy as np
            return jsonify({
                'success': True,
                'data': {
                    'citations_5yr': {
                        'mean': float(np.mean(citations_5yr)) if citations_5yr else 0,
                        'median': float(np.median(citations_5yr)) if citations_5yr else 0,
                        'max': max(citations_5yr) if citations_5yr else 0
                    },
                    'citations_3yr': {
                        'mean': float(np.mean(citations_3yr)) if citations_3yr else 0,
                        'median': float(np.median(citations_3yr)) if citations_3yr else 0,
                        'max': max(citations_3yr) if citations_3yr else 0
                    },
                    'family_count': {
                        'mean': float(np.mean(family)) if family else 0,
                        'median': float(np.median(family)) if family else 0,
                        'max': max(family) if family else 0
                    }
                }
            })
    finally:
        conn.close()


@app.route('/api/stats/legal', methods=['GET'])
def get_legal_stats():
    """获取法律状态统计"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 合并分类统计
            def classify_legal(status):
                if not status:
                    return 'Other'
                if '授权' in status:
                    return 'Granted'
                elif '实质审查' in status:
                    return 'Examination'
                elif '驳回' in status:
                    return 'Rejected'
                elif '撤回' in status:
                    return 'Withdrawn'
                elif '未缴年费' in status:
                    return 'Lapsed'
                elif '公开' in status:
                    return 'Published'
                else:
                    return 'Other'
            
            cursor.execute("""
                SELECT legal_status, COUNT(*) as count
                FROM patents GROUP BY legal_status ORDER BY count DESC LIMIT 20
            """)
            raw = cursor.fetchall()
            
            # 合并统计
            merged = {}
            for r in raw:
                status = r['legal_status']
                category = classify_legal(status)
                if category in merged:
                    merged[category] += r['count']
                else:
                    merged[category] = r['count']
            
            result = [{'status': k, 'count': v} for k, v in merged.items()]
            result.sort(key=lambda x: x['count'], reverse=True)
            
            return jsonify({'success': True, 'data': result})
    finally:
        conn.close()


# 桑基图API - 专利类型到法律状态流转
@app.route('/api/stats/sankey/legal-flow', methods=['GET'])
def get_sankey_legal_flow():
    """获取专利类型到法律状态的桑基图数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
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
                ORDER BY count DESC
            """)
            results = cursor.fetchall()
            
            # 法律状态归类映射
            def classify_legal(status):
                if not status:
                    return '其他'
                status = str(status)
                if '授权' in status:
                    return '已授权'
                elif '实质审查' in status:
                    return '审查中'
                elif '公开' in status:
                    return '已公开'
                elif '驳回' in status:
                    return '已驳回'
                elif '撤回' in status:
                    return '已撤回'
                elif '未缴年费' in status:
                    return '未缴年费'
                elif '期限届满' in status:
                    return '期限届满'
                elif '权利转移' in status:
                    return '权利转移'
                elif '许可' in status:
                    return '许可'
                else:
                    return '其他'
            
            # 合并统计
            merged = {}
            for row in results:
                src = row['patent_type']
                tgt = classify_legal(row['legal_status'])
                val = row['count']
                
                key = (src, tgt)
                if key in merged:
                    merged[key] += val
                else:
                    merged[key] = val
            
            # 构建节点和边
            nodes = {}
            links = []
            
            for (src, tgt), val in merged.items():
                if val < 10:  # 过滤掉太少的记录
                    continue
                
                if src not in nodes:
                    nodes[src] = {'name': src, 'category': 'type'}
                if tgt not in nodes:
                    nodes[tgt] = {'name': tgt, 'category': 'status'}
                
                links.append({'source': src, 'target': tgt, 'value': val})
            
            return jsonify({
                'success': True,
                'data': {
                    'nodes': list(nodes.values()),
                    'links': links
                }
            })
    finally:
        conn.close()


@app.route('/api/stats/sankey/ipc-flow', methods=['GET'])
def get_sankey_ipc_flow():
    """获取IPC分类流转桑基图数据 - 只显示主要分类分布，不显示双向流转"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # IPC分类归类 - 简化为8个主要类别
            ipc_mapping = {
                'B25J': '操作控制',     # 机器人操作（最大类6950个）
                'B62D': '移动系统',      # 车辆/移动底盘（1140个）
                'G06F': '计算控制',      # 计算机/控制（642个）
                'G05D': '运动控制',      # 运动控制（526个）
                'G05B': '控制调节',      # 控制/调节（482个）
                'G06V': '感知识别',      # 视觉识别（304个）
                'G06T': '图像处理',      # 图形处理（278个）
                'F16H': '传动机械',      # 传动（276个）
                'H02K': '电机驱动',      # 电机（274个）
                'G01C': '导航定位',      # 导航/测量（244个）
                'G06N': '智能算法',      # 神经网络/AI（228个）
            }
            
            # 直接统计各IPC分类的专利数量分布
            cursor.execute("""
                SELECT ipc_subclass, COUNT(*) as cnt
                FROM patents
                WHERE ipc_subclass IS NOT NULL AND ipc_subclass != '-' AND ipc_subclass != ''
                GROUP BY ipc_subclass
                ORDER BY cnt DESC
                LIMIT 12
            """)
            results = cursor.fetchall()
            
            # 归类IPC并统计
            category_stats = {}
            for row in results:
                ipc = row['ipc_subclass']
                cnt = row['cnt']
                category = ipc_mapping.get(ipc, '其他')
                if category in category_stats:
                    category_stats[category] += cnt
                else:
                    category_stats[category] = cnt
            
            # 构建节点：左侧是专利总数，右侧是分类
            nodes = [
                {'name': '专利总数', 'category': 'total'}
            ]
            
            # 按数量排序分类
            sorted_cats = sorted(category_stats.items(), key=lambda x: -x[1])
            for cat, cnt in sorted_cats:
                nodes.append({'name': cat, 'category': 'ipc', 'value': cnt})
            
            # 构建链接：从总数到各分类
            total_patents = sum(category_stats.values())
            links = []
            for cat, cnt in sorted_cats:
                links.append({'source': '专利总数', 'target': cat, 'value': cnt})
            
            return jsonify({
                'success': True,
                'data': {
                    'nodes': nodes,
                    'links': links
                }
            })
    finally:
        conn.close()


# 专利转让网络图API
@app.route('/api/stats/network/transfer', methods=['GET'])
def get_transfer_network():
    """获取清洗后的专利许可转让网络数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 使用清洗后的数据表
            cursor.execute("""
                SELECT licensor, licensee, COUNT(*) as transfer_count
                FROM patent_transfer_clean
                WHERE licensor IS NOT NULL AND licensor != ''
                    AND licensee IS NOT NULL AND licensee != ''
                    AND licensor != licensee
                GROUP BY licensor, licensee
                HAVING transfer_count >= 1
                ORDER BY transfer_count DESC
                LIMIT 80
            """)
            results = cursor.fetchall()
            
            nodes = {}
            links = []
            
            for row in results:
                src = row['licensor']
                tgt = row['licensee']
                val = row['transfer_count']
                
                if src not in nodes:
                    nodes[src] = {'name': src, 'category': 'licensor', 'value': val}
                if tgt not in nodes:
                    nodes[tgt] = {'name': tgt, 'category': 'licensee', 'value': val}
                
                links.append({'source': src, 'target': tgt, 'value': val})
            
            return jsonify({
                'success': True,
                'data': {
                    'nodes': list(nodes.values()),
                    'links': links
                }
            })
    finally:
        conn.close()


# 主题桑基图API
@app.route('/api/stats/sankey/topic', methods=['GET'])
def get_sankey_topic():
    """获取主题到IPC分类的桑基图数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # IPC分类归类
            ipc_mapping = {
                'B25J': '操作控制', 'B62D': '移动系统', 'G06F': '计算控制',
                'G05D': '运动控制', 'G05B': '控制调节', 'G06V': '感知识别',
                'G06T': '图像处理', 'G01C': '导航定位', 'G01M': '机械测试',
                'H02K': '电机驱动', 'H02J': '电力系统', 'A61B': '医疗设备',
                'F16H': '传动机械', 'A63H': '玩具娱乐', 'G06N': '智能算法',
                'G10L': '语音交互', 'G01S': '传感定位', 'H01M': '能源电池',
                'G01L': '力学传感', 'G06Q': '数据管理'
            }
            
            cursor.execute("""
                SELECT pt.topic, p.ipc_subclass, COUNT(*) as cnt
                FROM patent_topics pt
                JOIN patents p ON pt.public_number = p.public_number
                WHERE pt.topic IS NOT NULL AND p.ipc_subclass IS NOT NULL 
                    AND p.ipc_subclass != '' AND p.ipc_subclass != '-'
                GROUP BY pt.topic, p.ipc_subclass
                HAVING cnt >= 50
                ORDER BY cnt DESC
            """)
            results = cursor.fetchall()
            
            nodes = {}
            links = []
            
            for row in results:
                topic = row['topic']
                ipc = ipc_mapping.get(row['ipc_subclass'], '其他技术')
                val = row['cnt']
                
                if topic not in nodes:
                    nodes[topic] = {'name': topic, 'category': 'topic'}
                if ipc not in nodes:
                    nodes[ipc] = {'name': ipc, 'category': 'ipc'}
                
                links.append({'source': topic, 'target': ipc, 'value': val})
            
            return jsonify({
                'success': True,
                'data': {
                    'nodes': list(nodes.values()),
                    'links': links
                }
            })
    finally:
        conn.close()


@app.route('/api/stats/network/provinces-flow', methods=['GET'])
def get_provinces_flow_network():
    """获取省份流转网络数据 - 基于申请人省份的流转分析"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
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
                HAVING cnt >= 20
                ORDER BY cnt DESC
            """)
            results = cursor.fetchall()
            
            nodes = {}
            links = []
            
            for row in results:
                src = row['source']
                tgt = row['target']
                val = row['cnt']
                
                if src not in nodes:
                    nodes[src] = {'name': src, 'category': 'province'}
                if tgt not in nodes:
                    nodes[tgt] = {'name': tgt, 'category': 'province'}
                
                links.append({'source': src, 'target': tgt, 'value': val})
            
            return jsonify({
                'success': True,
                'data': {
                    'nodes': list(nodes.values()),
                    'links': links
                }
            })
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)