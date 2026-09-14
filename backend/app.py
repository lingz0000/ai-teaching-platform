# -*- coding: utf-8 -*-
"""
人工智能心理咨询陪练系统 - 后端服务
Flask 代理调用大模型接口，前端只与本地后端通信，不暴露任何第三方 API 信息。
"""

import json
import logging
import os
import time

import requests
from dotenv import load_dotenv
from flask import Flask, Response, request, send_from_directory
from flask_cors import CORS

# ---------------------------------------------------------------------------
# 环境变量
# ---------------------------------------------------------------------------
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"

# 上游模型服务的连接 / 读取超时（秒）
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 300

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-counseling-platform")

# ---------------------------------------------------------------------------
# Flask 应用
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)
CORS(app)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


# ---------------------------------------------------------------------------
# Prompt 构建（内置教育学 / 剧本创作规范）
# ---------------------------------------------------------------------------
def build_lesson_prompt(data):
    """根据表单字段拼装教案生成的专业 Prompt。"""
    topic = (data.get("topic") or "").strip()
    stage = (data.get("stage") or "初中").strip()
    duration = str(data.get("duration") or 45).strip()
    style = (data.get("style") or "互动型").strip()

    return f"""你是一位拥有 20 年一线教学经验的特级教师兼教学设计专家，精通布卢姆教育目标分类学、
加涅九大教学事件、 UbD 逆向教学设计和多元智能理论。请为下面的需求撰写一份高质量、可直接落地的教案。

【基本信息】
- 课程主题：{topic}
- 学段：{stage}
- 课时长度：{duration} 分钟
- 教学风格偏好：{style}

【撰写要求】
1. 使用 Markdown 输出，层级清晰（## / ###），重点内容加粗。
2. 教案必须包含以下模块：
   - **课程概述**（课题、课型、适用学段、课时）
   - **教学目标**（按"知识与技能 / 过程与方法 / 情感态度与价值观"三维目标，或新课标核心素养表述，用可测量的行为动词）
   - **教学重点与难点**（分别说明突破策略）
   - **学情分析**（结合该学段学生的认知发展特点）
   - **教学准备**（教具、多媒体资源、课前任务）
   - **教学过程**（按时间轴拆分为若干环节，每个环节标注**时间分配**、教师活动、学生活动、设计意图；环节之间要有清晰的逻辑递进：导入 → 新知探究 → 讲解演示 → 练习巩固 → 拓展提升 → 总结作业）
   - **板书设计**（用文字描述版面结构）
   - **作业布置**（分层作业：基础题 / 提高题 / 拓展题）
   - **教学反思预设**（预判可能的课堂问题及应对方案）
3. 教学风格偏好为"{style}"，请在活动设计上充分体现该风格。
4. 严格匹配 {duration} 分钟的课时长度，各环节时间分配之和应等于总时长。
5. 内容要具体、可操作，避免空话套话；示例、提问、活动都要写出具体内容。

现在，请输出完整教案："""


def build_script_prompt(data):
    """根据表单字段拼装情景剧脚本生成的专业 Prompt。"""
    topic = (data.get("topic") or "").strip()
    characters = str(data.get("characters") or 4).strip()
    duration = str(data.get("duration") or 10).strip()
    setting = (data.get("setting") or "").strip() or "由你根据主题合理设定"
    multi_ending = str(data.get("multiEnding") or "否").strip()

    ending_note = (
        f"在剧本正片结局之后，额外提供 **{max(2, 3)} 个不同的多结局版本**（结局 A / 结局 B / 结局 C），"
        "每个结局单独成段，写出从分歧点到结局的完整剧情走向。"
        if multi_ending in ("是", "yes", "true", "True", "1")
        else "只需一个完整结局，不需要多结局版本。"
    )

    return f"""你是一位资深教育戏剧编剧，擅长创作寓教于乐的校园情景剧，作品曾获全国校园戏剧节金奖。
请为下面的需求创作一个完整的情景剧脚本。

【基本信息】
- 剧本主题：{topic}
- 角色人数：{characters} 人
- 时长：{duration} 分钟
- 场景设定：{setting}
- 多结局：{multi_ending}

【创作要求】
1. 使用 Markdown 输出，格式规范清晰。
2. 脚本结构必须包含：
   - **剧本信息**（剧名、主题、时长、适用场合）
   - **角色表**（每个角色的姓名、身份、性格特点，共 {characters} 个角色，每个角色戏份均衡）
   - **道具与场景**（所需道具清单、舞台布景说明）
   - **正文分幕/分场**（按 "{duration} 分钟" 合理划分场次；每场标注场景、时间、在场角色）
   - 台词格式统一为：**角色名**：（动作/表情提示）台词内容
   - 舞台指示用斜体或括号标注，如 *（灯光渐亮，教室内晨读声起）*
   - **剧终**：{ending_note}
3. 剧情要围绕主题有起承转合：开场引入 → 矛盾冲突 → 高潮 → 结局升华，有明确的育人寓意。
4. 台词要口语化、有个性，符合角色身份；穿插适度的幽默元素但不说教。
5. 角色人数严格为 {characters} 人，不要增减；时长控制在 {duration} 分钟左右（正常语速约 180 字/分钟估算台词量）。

现在，请输出完整剧本："""


PROMPT_BUILDERS = {
    "lesson": build_lesson_prompt,
    "script": build_script_prompt,
}


# ---------------------------------------------------------------------------
# 流式代理
# ---------------------------------------------------------------------------
def stream_model_response(prompt):
    """
    调用上游模型接口并以 SSE（text/event-stream）形式逐段转发生成内容。
    """
    if not API_KEY:
        error_payload = {"error": "服务端未配置模型密钥，请联系管理员（检查 backend/.env 中的 DEEPSEEK_API_KEY）。"}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "你是一位专业的AI教学辅助助手，擅长教案设计与教育剧本创作。输出一律使用规范的 Markdown 格式。"},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    try:
        upstream = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except requests.exceptions.Timeout:
        logger.error("上游模型服务请求超时")
        error_payload = {"error": "模型服务响应超时，请稍后重试。"}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return
    except requests.exceptions.RequestException as exc:
        logger.error("上游模型服务连接失败: %s", exc)
        error_payload = {"error": "无法连接模型服务，请稍后重试。"}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    if upstream.status_code != 200:
        detail = ""
        try:
            detail = upstream.json().get("error", {}).get("message", "")
        except Exception:
            detail = upstream.text[:200]
        logger.error("上游模型服务返回 %s: %s", upstream.status_code, detail)
        error_payload = {"error": f"模型服务返回错误（{upstream.status_code}），请稍后重试。"}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    try:
        for line in upstream.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
    except requests.exceptions.Timeout:
        logger.error("读取模型流式响应超时")
        yield f"data: {json.dumps({'error': '接收生成内容超时，请重试。'}, ensure_ascii=False)}\n\n"
    except Exception as exc:
        logger.exception("流式转发过程中发生异常: %s", exc)
        yield f"data: {json.dumps({'error': '生成过程中出现异常，请重试。'}, ensure_ascii=False)}\n\n"
    finally:
        upstream.close()

    yield "data: [DONE]\n\n"


def validate_and_build_prompt(kind):
    """
    在请求上下文内解析表单并拼装 Prompt。
    必须在响应生成器被迭代之前调用（生成器执行时已脱离请求上下文）。
    返回 (prompt, error_message)：校验通过时 error_message 为 None。
    """
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()

    if not topic:
        return None, "请填写主题后再生成。"

    logger.info(
        "[%s] 生成请求 | 主题: %s | 参数: %s",
        kind, topic, json.dumps(data, ensure_ascii=False),
    )
    return PROMPT_BUILDERS[kind](data), None


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
def sse_response(kind):
    """统一的接口入口：校验参数 → 拼 Prompt → 以 SSE 流式返回。"""
    prompt, error = validate_and_build_prompt(kind)

    def generate():
        if error:
            yield f"data: {json.dumps({'error': error}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        start_ts = time.time()
        first_chunk = True
        for piece in stream_model_response(prompt):
            if first_chunk and '"content"' in piece:
                logger.info("[%s] 首字节耗时 %.2fs", kind, time.time() - start_ts)
                first_chunk = False
            yield piece
        logger.info("[%s] 生成完成，总耗时 %.2fs", kind, time.time() - start_ts)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/generate/lesson", methods=["POST"])
def generate_lesson():
    return sse_response("lesson")


@app.route("/api/generate/script", methods=["POST"])
def generate_script():
    return sse_response("script")


# ---------------------------------------------------------------------------
# 静态托管前端（访问 http://127.0.0.1:5000 即可打开页面）
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    if not API_KEY:
        logger.warning("DEEPSEEK_API_KEY 未配置，生成功能将不可用！请在 backend/.env 中填写。")
    logger.info("人工智能心理咨询陪练系统后端启动: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
