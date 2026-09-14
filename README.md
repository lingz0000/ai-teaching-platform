# 人工智能心理咨询陪练系统

自研人工智能心理咨询陪练系统：支持**教案生成**与**情景剧脚本生成**，前端产品化呈现（深色科技风 / 数据大屏视觉），后端代理调用大模型能力并流式返回。前端只与本地后端通信，**不暴露任何第三方 API 信息与密钥**。

## 项目结构

```
ai-teaching-platform/
├── backend/
│   ├── app.py                # Flask 后端（代理调用大模型 + 静态托管前端）
│   ├── requirements.txt      # Python 依赖
│   └── .env                  # 存放 DEEPSEEK_API_KEY（请勿提交到 git）
├── frontend/
│   ├── index.html            # 页面结构
│   ├── style.css             # 深色科技风样式
│   └── script.js             # 交互逻辑 + 流式渲染
└── README.md
```

## 功能一览

| 模块 | 表单字段 | 说明 |
| --- | --- | --- |
| 教案生成 | 课程主题、学段（小学/初中/高中/大学）、课时长度（40/45/90 分钟）、教学风格（互动型/讲授型/体验式） | 内置教育学规范（三维目标、学情分析、时间轴教学过程、分层作业等） |
| 情景剧脚本生成 | 剧本主题、角色人数、时长（5/10/15 分钟）、场景设定、多结局（是/否） | 内置剧本创作规范（角色表、分幕、台词格式、舞台指示） |

- 生成结果**流式逐字渲染**，Markdown 实时排版
- 结果区支持**一键复制**、**导出 txt**
- 生成中按钮禁用并显示"生成中..."，防止重复提交

## 环境要求

- Python 3.9+
- 现代浏览器（Chrome / Edge / Firefox）

## 安装与配置

### 1. 安装后端依赖

```bash
cd ai-teaching-platform/backend
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `backend/.env`，将 `sk-xxx...` 替换为你的真实 DeepSeek API Key（可在 https://platform.deepseek.com 获取）：

```
DEEPSEEK_API_KEY=sk-你的真实密钥
```

> `.env` 仅在后端读取，前端代码中**不包含也不出现**任何密钥。

### 3. 启动后端

```bash
cd ai-teaching-platform/backend
python app.py
```

启动后终端会输出：

```
[INFO] 人工智能心理咨询陪练系统后端启动: http://127.0.0.1:5000
```

### 4. 访问前端（两种方式任选）

**方式 A（推荐）：后端静态托管**

直接在浏览器打开 <http://127.0.0.1:5000>，无需额外启动任何前端服务。

**方式 B：直接打开 HTML**

双击 `frontend/index.html` 以 `file://` 方式打开。
此时需将 `frontend/script.js` 顶部的 `API_BASE` 改为后端地址：

```js
const API_BASE = "http://127.0.0.1:5000";
```

（后端已开启 CORS，跨源访问可直接工作。）

## 使用方法

1. 打开页面后，顶部 Tab 切换「教案生成」/「情景剧脚本生成」。
2. 填写左侧表单（主题为必填项），选择对应参数。
3. 点击「生成教案」/「生成脚本」，右侧结果区将流式输出内容。
4. 生成完成后，可点击「复制」或「导出 txt」保存结果。

## 接口说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/generate/lesson` | 生成教案，请求体 JSON：`{ "topic", "stage", "duration", "style" }` |
| POST | `/api/generate/script` | 生成情景剧脚本，请求体 JSON：`{ "topic", "characters", "duration", "setting", "multiEnding" }` |

两个接口均返回 `text/event-stream` 流式数据：

- `data: {"content": "..."}` — 增量生成内容
- `data: {"error": "..."}` — 业务错误信息
- `data: [DONE]` — 流结束

## 常见问题

**Q：点击生成后提示"服务端未配置模型密钥"？**
A：说明 `backend/.env` 中的 `DEEPSEEK_API_KEY` 未填写或为占位符，填写真实密钥后重启后端。

**Q：提示"无法连接模型服务"？**
A：检查本机网络是否可访问外网，以及 API Key 是否有效。

**Q：直接打开 index.html 后点击生成无反应？**
A：`file://` 方式需按上文"方式 B"修改 `API_BASE`，或改用方式 A 访问。

## 安全提示

- 请勿将 `.env` 文件提交到公开仓库。
- 本项目为本地开发配置，如需部署到公网，请自行增加鉴权、限流等防护措施。
