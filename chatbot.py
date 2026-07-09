"""
知墨教育智能咨询助手 - 核心聊天逻辑
"""
import os
import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

# ============================================================
# 知识库加载
# ============================================================

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), 'knowledge')

def load_knowledge() -> dict[str, str]:
    """加载所有知识文件到内存"""
    knowledge = {}
    for fname in os.listdir(KNOWLEDGE_DIR):
        if fname.endswith('.txt'):
            path = os.path.join(KNOWLEDGE_DIR, fname)
            with open(path, 'r', encoding='utf-8') as f:
                knowledge[fname] = f.read()
    return knowledge

KNOWLEDGE = load_knowledge()

# ============================================================
# 关键词检索
# ============================================================

# 关键词 → 知识文件映射
KEYWORD_MAP = {
    # 课程相关
    '数学': ['courses.txt', 'math_competition.txt', 'teachers.txt'],
    '英语': ['courses.txt'],
    '语文': ['courses.txt', 'chinese_lectures.txt', 'teachers.txt'],
    '科学': ['courses.txt'],
    '课程': ['courses.txt'],
    '课表': ['courses.txt'],
    '竞赛': ['courses.txt', 'math_competition.txt'],
    '联赛': ['courses.txt', 'math_competition.txt'],
    '一对一': ['courses.txt'],
    '课内': ['courses.txt', 'teachers.txt'],
    '中考': ['courses.txt', 'chinese_lectures.txt'],
    '高考': ['courses.txt', 'teachers.txt'],
    '教材': ['courses.txt', 'math_competition.txt'],
    '讲义': ['math_competition.txt'],
    '讲义资料': ['math_competition.txt', 'chinese_lectures.txt'],
    # 教师相关
    '老师': ['teachers.txt'],
    '教师': ['teachers.txt'],
    '师资': ['teachers.txt'],
    '孙宇航': ['teachers.txt'],
    '佘孟谦': ['teachers.txt'],
    '王老师': ['teachers.txt'],
    '林忠晶': ['teachers.txt'],
    '林老师': ['teachers.txt'],
    'Lydia': ['teachers.txt'],
    '吴老师': ['teachers.txt'],
    # 语文课件
    '作文': ['chinese_lectures.txt', 'courses.txt'],
    '文言文': ['chinese_lectures.txt', 'courses.txt'],
    '古诗': ['chinese_lectures.txt', 'courses.txt'],
    '阅读': ['chinese_lectures.txt', 'courses.txt'],
    '语法': ['chinese_lectures.txt', 'courses.txt'],
    # 常见问题
    '价格': ['faq.txt'],
    '费用': ['faq.txt'],
    '收费': ['faq.txt'],
    '试听': ['faq.txt'],
    '预约': ['faq.txt'],
    '咨询': ['faq.txt'],
    '电话': ['faq.txt'],
    '时间': ['faq.txt'],
    '报名': ['faq.txt'],
    '怎么': ['faq.txt', 'courses.txt'],
    '适合': ['faq.txt', 'teachers.txt'],
}

def retrieve_knowledge(query: str) -> str:
    """根据用户问题检索相关知识片段"""
    relevant_files = set()
    query_lower = query.lower()
    for keyword, files in KEYWORD_MAP.items():
        if keyword in query_lower:
            relevant_files.update(files)
    
    # 如果没有命中关键词，返回所有FAQ和课程概览
    if not relevant_files:
        relevant_files = {'faq.txt', 'courses.txt', 'teachers.txt'}
    
    context_parts = []
    for fname in sorted(relevant_files):
        if fname in KNOWLEDGE:
            context_parts.append(KNOWLEDGE[fname])
    
    return '\n\n'.join(context_parts)

# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = """你是"知墨教育"的智能咨询助手，专门帮助家长了解我们的课程、教师和教学服务。

【你的身份】
- 你是知墨教育的官方AI咨询顾问
- 你代表知墨教育与家长交流

【你的核心任务】
1. 准确解答家长关于课程内容、教师资质、教学效果的疑问
2. 根据孩子情况推荐合适的课程和老师
3. 在回答中自然地推荐我们的优势课程
4. 适时引导家长拨打咨询电话 18668861895 预约试听课

【回答风格】
- 专业但亲切，像一位热心的教育顾问
- 回答要有条理，善用分点列举
- 引用具体数据（提分成绩、课程节数等）增加可信度
- 适当使用 emoji 让回答更生动
- 回答不要太长，控制在200字以内，除非家长问得很详细

【重要规则】
- 不要编造不存在的课程或教师信息
- 不要回答与教育无关的问题，礼貌引导回教育话题
- 涉及具体报价问题时，引导家长拨打 18668861895 咨询
- 始终正面积极，展现知墨教育的优势
- 当推荐老师时，要具体说明老师的亮点和适合的学生类型

【课程推荐逻辑】
- 数学竞赛/联赛 → 推荐孙宇航老师（初中）或佘孟谦老师（高中）
- 课内数学基础 → 推荐孙宇航老师或佘孟谦老师
- 语文提分 → 推荐王老师（北师大硕士，近十年教龄）
- 英语中考 → 推荐英语冲刺课程（32节系统课程）
- 基础薄弱学生 → 强调一对一辅导，定制方案
- 尖子生 → 推荐竞赛课程，挑战更高难度
"""

# ============================================================
# LLM 调用
# ============================================================

def get_client() -> AsyncOpenAI:
    """获取 LLM 客户端"""
    return AsyncOpenAI(
        api_key=os.getenv('LLM_API_KEY', ''),
        base_url=os.getenv('LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
    )

async def chat_stream(message: str, history: list[dict]) -> AsyncGenerator[str, None]:
    """流式聊天，返回 AsyncGenerator"""
    # 检索相关知识
    context = retrieve_knowledge(message)
    
    # 构建 messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"【参考资料】\n以下是你可以参考的知识：\n{context}"},
    ]
    
    # 添加对话历史（最近10轮）
    for msg in history[-20:]:
        messages.append(msg)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    # 调用 LLM
    client = get_client()
    model = os.getenv('LLM_MODEL', 'qwen-plus-latest')
    
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=1024,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n\n抱歉，系统暂时繁忙，请稍后再试或拨打咨询电话 18668861895。（错误：{str(e)}）"
