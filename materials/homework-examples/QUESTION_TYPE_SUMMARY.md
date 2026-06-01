# Homework Question Type Summary

本目录保存从超星作业列表中整理出的《计算机组成原理》典型题型资料。

抓取范围：

- 已抓取：已完成、待批阅作业
- 已跳过：未交作业，避免影响当前作业状态
- 已清洗：登录参数 URL、个人作答记录、页面噪声文本

原始清洗文本位于：

```text
materials/homework-examples/raw/
```

抓取索引位于：

```text
materials/homework-examples/crawl-results.json
```

## 1. Crawled Assignments

| 作业 | 题量 | 满分 | 主要题型 |
| --- | ---: | ---: | --- |
| 第1章作业 | 20 | 100 | 单选题、判断题、完型填空、连线题、阅读理解、填空题 |
| 第3章作业-1st | 5 | 97 | 阅读理解、填空题 |
| 第3章作业-2nd | 17 | 100 | 单选题、多选题、填空题、计算题、阅读理解、完型填空 |
| 第4章作业 | 15 | 100 | 判断题、单选题、填空题、计算题、阅读理解 |
| 第5章作业-1st | 30 | 100 | 单选题、判断题、填空题 |
| 第5章作业-2nd | 15 | 130 | 判断题、单选题、填空题、阅读理解 |
| 第6章作业-1st | 21 | 100 | 单选题、多选题、简答题、填空题 |
| 第6章作业-2nd | 3 | 100 | 阅读理解、填空题、简答题、单选题 |
| 第7章作业-1st | 22 | 100 | 多选题、单选题、填空题、阅读理解 |
| RISC-V指令系统视频已看完 | 1 | 100 | 单选题 |

## 2. Observed Question Types

从章节作业来看，系统题库至少应该支持这些题型：

| 题型 | 是否建议 MVP 支持 | 批改方式 | 说明 |
| --- | --- | --- | --- |
| 单选题 | 是 | 规则批改 | 最常见题型，选项 A/B/C/D |
| 多选题 | 是 | 规则批改 | 需要答案集合完全匹配 |
| 判断题 | 是 | 规则批改 | 可视为特殊单选题 |
| 填空题 | 是 | 标准答案 + 可接受答案 | 经常包含多个空 |
| 简答题 | 是 | 评分点 / AI 辅助 | 适合后期接入 LLM 批改 |
| 计算题 | 建议支持 | 人工答案 / 公式规则 / AI 辅助 | 常见于补码、浮点数、Cache、性能指标等 |
| 阅读理解 | 建议支持 | 子题规则批改 | 本质是题组，包含单选、多选、填空、简答 |
| 完型填空 | 可选 | 多空规则批改 | 可作为特殊填空题 |
| 连线题 | 可选 | 映射关系批改 | MVP 可以先转成匹配题或多空填空题 |

## 3. Typical Patterns

### 3.1 Single Choice

结构：

```json
{
  "type": "single_choice",
  "stem": "题干",
  "options": [
    { "key": "A", "text": "选项 A" },
    { "key": "B", "text": "选项 B" },
    { "key": "C", "text": "选项 C" },
    { "key": "D", "text": "选项 D" }
  ],
  "answer": "A",
  "explanation": ""
}
```

常见考法：

- 概念辨析
- 错误说法判断
- 公式计算后选结果
- 指令、存储器、CPU、流水线相关概念判断

### 3.2 Multiple Choice

结构：

```json
{
  "type": "multiple_choice",
  "stem": "题干",
  "options": [
    { "key": "A", "text": "选项 A" },
    { "key": "B", "text": "选项 B" },
    { "key": "C", "text": "选项 C" },
    { "key": "D", "text": "选项 D" }
  ],
  "answer": ["A", "C"]
}
```

批改建议：

- 用户答案排序后与标准答案集合比较
- 支持部分得分可以后续再做，MVP 先要求完全正确

### 3.3 True / False

结构：

```json
{
  "type": "true_false",
  "stem": "判断题题干",
  "answer": true
}
```

实现建议：

- 前端显示为“对 / 错”
- 后端可以复用单选题批改逻辑

### 3.4 Fill Blank

结构：

```json
{
  "type": "fill_blank",
  "stem": "题干，包含（1）（2）（3）等空位",
  "blanks": [
    {
      "index": 1,
      "answer": "标准答案",
      "acceptable_answers": ["同义答案1", "同义答案2"]
    }
  ]
}
```

常见考法：

- 性能指标：CPI、MIPS、执行时间
- 数据表示：补码、浮点数、规格化
- 存储系统：Cache 命中率、地址划分
- 指令系统：寻址方式、指令格式字段

### 3.5 Short Answer

结构：

```json
{
  "type": "short_answer",
  "stem": "简答题题干",
  "reference_answer": "参考答案",
  "rubric": [
    "评分点 1",
    "评分点 2",
    "评分点 3"
  ]
}
```

批改建议：

- MVP：展示参考答案，人工自查
- 增强版：使用 LLM 根据 rubric 给分

### 3.6 Calculation

结构：

```json
{
  "type": "calculation",
  "stem": "计算题题干",
  "answer": "最终答案",
  "solution_steps": [
    "步骤 1",
    "步骤 2"
  ],
  "tolerance": null
}
```

常见考法：

- CPU 执行时间公式
- 平均 CPI
- MIPS
- Cache 命中率和平均访问时间
- 浮点数规格化和补码运算

### 3.7 Reading Comprehension / Question Group

阅读理解在作业中常作为“题组”出现，一个大材料下面有多个子题。

推荐结构：

```json
{
  "type": "question_group",
  "group_type": "reading_comprehension",
  "stem": "共同材料",
  "children": [
    {
      "type": "single_choice",
      "stem": "子题 1",
      "options": [],
      "answer": "A"
    },
    {
      "type": "fill_blank",
      "stem": "子题 2",
      "blanks": []
    }
  ]
}
```

实现建议：

- 数据库中可以用 `parent_question_id` 表示父子题
- 前端展示时先显示材料，再显示子题

### 3.8 Matching

连线题可转成映射题：

```json
{
  "type": "matching",
  "left_items": [
    { "key": "1", "text": "左侧描述" }
  ],
  "right_items": [
    { "key": "A", "text": "右侧概念" }
  ],
  "answer": {
    "1": "A"
  }
}
```

MVP 如果不想单独做连线交互，可以先转成多空填空题。

## 4. Suggested MVP Question Types

第一版建议优先实现：

1. 单选题
2. 多选题
3. 判断题
4. 填空题
5. 简答题

第二阶段再实现：

1. 计算题
2. 阅读理解题组
3. 完型填空
4. 连线题

## 5. Database Design Notes

为了兼容这些题型，`questions` 表建议包含：

```text
id
chapter_id
parent_question_id
type
difficulty
stem
options_json
answer_json
rubric_json
explanation
source_assignment
source_chapter
created_at
updated_at
```

说明：

- `parent_question_id` 用于阅读理解题组。
- `options_json` 用于选择题、判断题、连线题。
- `answer_json` 用于保存单答案、多答案、多空答案、匹配关系。
- `rubric_json` 用于简答题和计算题评分点。
- `source_assignment` 用于记录题目来自哪一次作业。

## 6. Generation Guidance

后续根据复习资料生成题目时，Prompt 应尽量模仿这些作业的风格：

- 选择题多用“下列说法正确/错误的是”
- 多选题适合考查多个条件、多个特点、多个步骤
- 填空题适合考公式计算和关键概念
- 简答题要求拆出评分点
- 计算题必须给出标准步骤和最终答案
- 阅读理解题组适合性能计算、指令格式、Cache 地址划分等综合题

