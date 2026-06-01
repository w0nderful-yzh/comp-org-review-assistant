# CompOrg Review Assistant

CompOrg Review Assistant is a course-specific review system for Computer Organization. The system is designed around the school's existing course materials and review notes, helping students practice multiple-choice questions, fill-in-the-blank questions, and short-answer questions by chapter or across the whole course.

中文名称建议：计算机组成原理复习助手。

## 1. Project Background

本项目面向《计算机组成原理》课程复习场景。当前课程资料已经固定，不需要让学生上传课件。系统可以直接使用开发者预置的九个章节资料作为知识来源。

已有资料来源：

- 原始课件：`materials/courseware-pdfs/chapter-01-courseware.pdf` 到 `materials/courseware-pdfs/chapter-09-courseware.pdf`
- 已整理复习资料：`materials/review-notes/chapter-01-*.docx` 到 `materials/review-notes/chapter-09-*.docx`
- 典型作业题型：`materials/homework-examples/`

资料映射清单见：

```text
materials/MATERIALS_MANIFEST.md
```

题型总结见：

```text
materials/homework-examples/QUESTION_TYPE_SUMMARY.md
```

## 2. Core Goal

系统目标不是做通用问答平台，而是做一个针对本校《计算机组成原理》课程的复习助手。

核心能力包括：

- 按章节复习
- 总复习混合练习
- 单选题、多选题、判断题、填空题、简答题练习
- 自动批改
- 答案解析
- 错题本
- 薄弱章节统计
- 基于复习资料的题目生成与简答题评分

## 3. Product Scope

### 3.1 Student Features

- 选择章节开始练习
- 选择总复习模式
- 选择题型：单选题、多选题、判断题、填空题、简答题、混合练习
- 查看答案与解析
- 查看错题本
- 重新练习错题
- 查看章节掌握情况

### 3.2 Admin / Teacher Features

- 管理章节
- 管理知识点
- 导入或维护复习资料
- 生成题目
- 审核 AI 生成题目
- 修改题干、选项、答案、解析
- 查看学生练习统计

第一版可以先不做完整教师端，直接通过后台脚本或数据库种子数据导入题库。

## 4. Recommended Architecture

推荐使用预置知识库架构，而不是用户上传资料架构。

```text
章节复习资料
    ↓
文档解析与清洗
    ↓
知识点切分
    ↓
章节知识库 / 向量库
    ↓
题目生成与题库入库
    ↓
学生练习
    ↓
自动批改 / 错题本 / 学习统计
```

系统可以分为四层：

```text
Frontend Layer
    学生端页面、章节选择、答题页面、错题本、统计页面

Backend API Layer
    用户服务、章节服务、题库服务、练习服务、批改服务

AI Service Layer
    知识检索、题目生成、简答题评分、解析生成

Data Layer
    关系型数据库、向量数据库、预置复习资料文件
```

## 5. Recommended Tech Stack

适合课程设计和后续快速实现的技术栈：

```text
Frontend: Vue 3 + Vite + TypeScript
Backend: FastAPI + Python
Database: SQLite for prototype, MySQL/PostgreSQL for final version
Vector Store: Chroma or FAISS for prototype, pgvector for production-like setup
Document Parsing: python-docx, PyMuPDF
AI Integration: OpenAI API, local Qwen/DeepSeek, or any compatible LLM API
```

如果希望更贴近 Java 后端课程设计，也可以使用：

```text
Frontend: Vue 3
Backend: Spring Boot
Database: MySQL
AI Service: 独立 Python 服务或通过 HTTP 调用 LLM API
```

推荐第一版采用：

```text
Vue 3 + FastAPI + SQLite + Chroma
```

原因：

- 开发速度快
- 适合处理文档与 AI 逻辑
- 部署和调试成本低
- 后续容易迁移到 MySQL/PostgreSQL

## 6. Main Pages

### 6.1 Home Page

展示课程复习入口：

- 第 1 章：概论
- 第 2 章：总线
- 第 3 章：信息编码与数据表示
- 第 4 章：运算方法与运算器
- 第 5 章：存储体系
- 第 6 章：指令系统
- 第 7 章：控制器
- 第 8 章：RISC-V 与 ARM 模型机设计实例
- 第 9 章：输入输出系统
- 总复习

章节名称来自当前 `materials/review-notes/` 文件名。若最终课程大纲标题不同，以 `materials/MATERIALS_MANIFEST.md` 和教师课件为准。

### 6.2 Chapter Review Page

功能：

- 展示章节知识点
- 选择题型
- 选择题目数量
- 开始练习

### 6.3 Practice Page

功能：

- 单题或整卷答题
- 自动保存作答
- 提交后展示得分
- 展示答案和解析
- 错题自动进入错题本

### 6.4 Wrong Questions Page

功能：

- 按章节筛选错题
- 按题型筛选错题
- 重新练习
- 标记已掌握

### 6.5 Statistics Page

功能：

- 总练习次数
- 正确率
- 各章节正确率
- 各题型正确率
- 薄弱知识点列表

## 7. Core Data Model

### 7.1 Chapter

```text
id
title
description
order_index
source_file
created_at
updated_at
```

### 7.2 KnowledgePoint

```text
id
chapter_id
name
summary
difficulty
created_at
updated_at
```

### 7.3 Question

```text
id
chapter_id
knowledge_point_id
parent_question_id   # for reading-comprehension question groups
type                 # single_choice, multiple_choice, true_false, fill_blank, short_answer, calculation, question_group, cloze, matching
difficulty           # easy, medium, hard
stem
options_json         # for choice, true/false, matching
answer_json          # single answer, answer list, blanks, or matching map
rubric_json          # useful for short-answer and calculation scoring
explanation
source_context
source_assignment
is_ai_generated
is_reviewed
created_at
updated_at
```

### 7.4 PracticeSession

```text
id
user_id
mode                 # chapter, final_review, wrong_questions
chapter_id
question_count
score
started_at
submitted_at
```

### 7.5 AnswerRecord

```text
id
session_id
question_id
user_answer
is_correct
score
feedback
created_at
```

### 7.6 WrongQuestion

```text
id
user_id
question_id
wrong_count
last_wrong_at
mastered
```

## 8. Question Types

### 8.1 Single-Choice Question

适合规则批改。

示例结构：

```json
{
  "type": "single_choice",
  "stem": "下列关于冯·诺依曼计算机特点的说法，正确的是？",
  "options": [
    { "key": "A", "text": "程序和数据都以二进制形式存储" },
    { "key": "B", "text": "只能顺序执行程序，不能跳转" },
    { "key": "C", "text": "运算器负责存储所有数据" },
    { "key": "D", "text": "输入输出设备直接执行算术运算" }
  ],
  "answer": "A",
  "explanation": "冯·诺依曼计算机采用存储程序思想，程序和数据都以二进制形式存放在存储器中。"
}
```

### 8.2 Multiple-Choice Question

适合规则批改，答案应作为集合比较。

```json
{
  "type": "multiple_choice",
  "stem": "下列哪些属于面向机器的语言？",
  "options": [
    { "key": "A", "text": "机器语言" },
    { "key": "B", "text": "汇编语言" },
    { "key": "C", "text": "高级语言" },
    { "key": "D", "text": "自然语言" }
  ],
  "answer": ["A", "B"],
  "explanation": "机器语言和汇编语言都更接近机器，属于面向机器的语言。"
}
```

### 8.3 True / False Question

可视为特殊单选题。

```json
{
  "type": "true_false",
  "stem": "机器字长是指存储器中一个存储单元的位数。",
  "answer": false,
  "explanation": "机器字长通常指 CPU 一次能处理的二进制数据位数。"
}
```

### 8.4 Fill-in-the-Blank Question

适合标准答案 + 同义答案批改。

```json
{
  "type": "fill_blank",
  "stem": "计算机硬件系统通常由运算器、控制器、存储器、输入设备和____组成。",
  "blanks": [
    {
      "index": 1,
      "answer": "输出设备",
      "acceptable_answers": ["输出设备", "输出装置"]
    }
  ],
  "explanation": "计算机硬件五大组成部分包括运算器、控制器、存储器、输入设备和输出设备。"
}
```

### 8.5 Short-Answer Question

适合评分点批改。

```json
{
  "type": "short_answer",
  "stem": "简述存储程序思想的基本含义。",
  "answer": "程序和数据都以二进制形式存放在存储器中，计算机按照程序指定的指令序列自动执行。",
  "rubric": [
    "指出程序和数据存放在存储器中",
    "指出程序和数据采用二进制表示",
    "指出计算机可以按指令序列自动执行"
  ],
  "explanation": "存储程序思想是冯·诺依曼体系结构的核心思想之一。"
}
```

### 8.6 Advanced Question Types

从已整理作业中还观察到这些题型，建议第二阶段支持：

- `calculation`：计算题，保存最终答案、解题步骤、可选误差范围。
- `question_group`：阅读理解题组，父题保存共同材料，子题保存单选、多选、填空或简答。
- `cloze`：完型填空，可作为多空填空题实现。
- `matching`：连线题，可保存左右项和答案映射，也可在 MVP 中转成多空填空题。

详细题型参考：

```text
materials/homework-examples/QUESTION_TYPE_SUMMARY.md
```

## 9. AI / RAG Design

本系统可以使用 RAG，但范围应控制在课程复习资料内。

### 9.1 Knowledge Base Construction

流程：

```text
读取 docx/pdf
    ↓
抽取文本
    ↓
按章节和标题切分
    ↓
生成 embedding
    ↓
写入向量库
```

每个知识片段建议保存：

```text
chunk_id
chapter_id
title
content
source_file
source_page
embedding
```

### 9.2 Question Generation

出题时应指定：

- 章节
- 知识点
- 题型
- 难度
- 数量
- 输出 JSON 格式

生成后不要直接给学生使用，建议先进入待审核状态。

### 9.3 Short-Answer Grading

简答题批改建议采用：

```text
学生答案
    +
标准答案
    +
评分点 rubric
    ↓
LLM 评分
    ↓
分数 + 反馈 + 漏答点
```

选择题和填空题优先使用规则批改，不需要调用 AI。

## 10. MVP Version

第一版建议只做这些：

1. 预置章节列表
2. 题库数据表
3. 按章节抽题
4. 总复习随机抽题
5. 单选题、多选题、判断题、填空题自动批改
6. 简答题显示参考答案或使用简单关键词评分
7. 错题本
8. 基础统计

第一版可以先不做：

- 用户上传课件
- 完整教师端
- 班级管理
- 在线考试防作弊
- 复杂知识图谱
- 多模型配置平台

## 11. Suggested Directory Structure

```text
comp-org-review-assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── data/
│   │   ├── review_notes/        # optional copied/processed text from materials/review-notes
│   │   └── seed_questions/
│   ├── scripts/
│   │   ├── import_review_notes.py
│   │   ├── generate_questions.py
│   │   └── build_vector_store.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── router/
│   │   └── stores/
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── architecture.md
│   └── api-design.md
├── materials/
│   ├── MATERIALS_MANIFEST.md
│   ├── courseware-pdfs/
│   ├── review-notes/
│   └── homework-examples/
├── PROJECT_OVERVIEW.md
└── README.md
```

## 12. API Draft

```text
GET    /api/chapters
GET    /api/chapters/{chapter_id}
GET    /api/chapters/{chapter_id}/knowledge-points

GET    /api/questions
POST   /api/questions/generate
POST   /api/practice-sessions
GET    /api/practice-sessions/{session_id}
POST   /api/practice-sessions/{session_id}/submit

GET    /api/wrong-questions
POST   /api/wrong-questions/{question_id}/mastered

GET    /api/statistics/overview
GET    /api/statistics/chapters
```

## 13. Development Notes for Claude Code

When implementing this project, prefer a small but complete MVP before adding advanced AI features.

Recommended implementation order:

1. Create backend project skeleton.
2. Create database models and seed chapter data from `materials/MATERIALS_MANIFEST.md`.
3. Create question model and seed sample questions from `materials/homework-examples/`.
4. Implement chapter and practice APIs.
5. Create Vue frontend pages for chapter selection and practice.
6. Implement answer submission and scoring.
7. Implement wrong question tracking.
8. Add document parsing for `materials/review-notes/*.docx`.
9. Add RAG only after the basic question bank workflow is stable.

Important design decision:

The system should treat AI-generated questions as draft content. Questions become visible to students only after review or after they are explicitly marked as usable.

## 14. Success Criteria

The MVP is successful if a student can:

- Open the system
- Select a chapter or final review
- Complete a set of mixed questions
- Submit answers
- See score, correct answers, and explanations
- Review wrong questions later

The advanced version is successful if the system can:

- Build a knowledge base from the prepared review notes
- Generate course-style questions from selected chapters
- Grade short answers based on rubric points
- Recommend weak chapters and related practice questions
