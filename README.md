# 计算机组成原理复习助手

面向《计算机组成原理》课程的复习练习系统。基于学校已有的九章复习资料和作业题，提供章节练习、自动批改、错题本、学习统计和 AI 智能出题等功能。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + TypeScript |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL 16 (Docker) |
| AI 出题 | OpenAI 兼容接口 (可配置模型) |

## 项目完成情况

### 已交付功能

**练习系统**
- 按 9 个章节分别练习，支持总复习跨章节随机抽题
- 题型：单选、多选、判断、填空、简答、计算
- 自动批改与评分，提交后即时显示正确答案和解析
- 练习前可选择"只做原题"或"接受 AI 题"
- 题目来源标签（作业原题 / AI 生成 / 样例题）

**错题本**
- 自动记录答错题目，支持多次错题计数
- 错题重练：从错题本中抽题重新练习
- 标记已掌握功能

**学习统计**
- 总览：练习次数、作答总数、正确率、未掌握错题数
- 按章节展示正确率进度条

**知识库**
- 基于 9 章复习笔记 DOCX 解析的知识点和知识块
- 按章节浏览知识点
- 全文检索知识块内容

**AI 智能出题**
- 基于章节知识块，通过 LLM 自动生成复习题
- 前端可选章节、题型、难度、数量和关注点
- 批量生成脚本，自动为题目薄弱的章节补充题目
- 生成的题目直接进入题库，无需人工审核

**题目反馈机制**
- 学生可对题目点赞（有帮助）或标记"没用"
- 点赞数实时显示
- 被多人标记"没用"的 AI 题自动归档，不再出现在练习中

**数据导入**
- 从作业文本文件批量导入题目（`scripts/import_homework_questions.py`）
- 从 DOCX 复习笔记导入知识点和知识块（`scripts/import_review_notes.py`）
- 样例题种子数据（`scripts/seed_sample_questions.py`）

## 快速启动

### 1. 启动数据库

```bash
docker compose up -d
```

### 2. 启动后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 配置 AI API Key
cp .env.example .env
# 编辑 .env 填入 AI_API_KEY

# 导入数据
cd backend
python scripts/seed_sample_questions.py
python scripts/import_homework_questions.py
python scripts/import_review_notes.py

# 批量生成 AI 题目（可选，自动跳过题目充足的章节）
python scripts/batch_generate_ai.py

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # API 路由
│   │   ├── models/entities.py     # 数据模型
│   │   ├── schemas/api.py         # 请求/响应 Schema
│   │   ├── services/              # 批改、AI 出题
│   │   └── core/                  # 配置、数据库连接
│   ├── scripts/                   # 数据导入和批量生成脚本
│   └── tests/                     # 后端测试
├── frontend/
│   └── src/
│       ├── components/            # PracticeView, WrongQuestionsView, StatsView, KnowledgeView
│       ├── composables/           # useSharedState 共享状态
│       ├── api/client.ts          # API 客户端
│       └── styles/global.css      # 全局样式
├── materials/                     # 课程资料（复习笔记、课件、作业）
├── docker/                        # 数据库初始化 SQL
└── docker-compose.yml             # PostgreSQL 服务
```
