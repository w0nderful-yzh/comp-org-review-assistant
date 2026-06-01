from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import Question


QUESTIONS = [
    {
        "chapter_id": 1,
        "type": "single_choice",
        "difficulty": "easy",
        "stem": "冯·诺依曼计算机的核心思想是？",
        "options_json": [
            {"key": "A", "text": "存储程序"},
            {"key": "B", "text": "分布式计算"},
            {"key": "C", "text": "流水线并行"},
            {"key": "D", "text": "虚拟存储"},
        ],
        "answer_json": {"answer": "A"},
        "explanation": "冯·诺依曼体系结构的核心是把程序和数据以二进制形式存放在存储器中，并按指令序列自动执行。",
    },
    {
        "chapter_id": 2,
        "type": "true_false",
        "difficulty": "easy",
        "stem": "总线是一组能为多个部件分时共享的信息传输线。",
        "options_json": [{"key": "true", "text": "对"}, {"key": "false", "text": "错"}],
        "answer_json": {"answer": "TRUE"},
        "explanation": "总线通常由多个部件共享，通过总线仲裁和时序控制完成信息传输。",
    },
    {
        "chapter_id": 3,
        "type": "fill_blank",
        "difficulty": "medium",
        "stem": "带符号整数常用的机器数表示包括原码、反码和____。",
        "options_json": [],
        "answer_json": {"blanks": [{"index": 1, "answer": "补码", "acceptable_answers": ["二进制补码"]}]},
        "explanation": "补码可以把减法转换为加法，是计算机中最常用的带符号整数表示方式。",
    },
    {
        "chapter_id": 4,
        "type": "multiple_choice",
        "difficulty": "medium",
        "stem": "下列哪些部件通常属于运算器的组成部分？",
        "options_json": [
            {"key": "A", "text": "ALU"},
            {"key": "B", "text": "累加器"},
            {"key": "C", "text": "状态寄存器"},
            {"key": "D", "text": "外部磁盘"},
        ],
        "answer_json": {"answer": ["A", "B", "C"]},
        "explanation": "运算器通常包含 ALU、通用/专用寄存器及状态标志相关部件，外部磁盘属于外存设备。",
    },
    {
        "chapter_id": 5,
        "type": "single_choice",
        "difficulty": "medium",
        "stem": "Cache 的主要作用是？",
        "options_json": [
            {"key": "A", "text": "扩大外存容量"},
            {"key": "B", "text": "缓解 CPU 与主存速度差异"},
            {"key": "C", "text": "替代寄存器"},
            {"key": "D", "text": "执行算术运算"},
        ],
        "answer_json": {"answer": "B"},
        "explanation": "Cache 利用程序局部性，在 CPU 和主存之间提供高速缓冲。",
    },
    {
        "chapter_id": 6,
        "type": "multiple_choice",
        "difficulty": "medium",
        "stem": "指令通常可以包含哪些字段？",
        "options_json": [
            {"key": "A", "text": "操作码"},
            {"key": "B", "text": "地址码"},
            {"key": "C", "text": "寻址方式信息"},
            {"key": "D", "text": "显示器刷新率"},
        ],
        "answer_json": {"answer": ["A", "B", "C"]},
        "explanation": "指令格式通常描述操作码、操作数地址以及寻址方式等信息。",
    },
    {
        "chapter_id": 7,
        "type": "short_answer",
        "difficulty": "medium",
        "stem": "简述控制器的主要功能。",
        "options_json": [],
        "answer_json": {"reference_answer": "控制器负责取指令、分析指令，并按时序产生控制信号，协调运算器、存储器和输入输出设备完成指令执行。"},
        "rubric_json": ["取指令", "分析指令", "控制信号", "协调"],
        "explanation": "控制器是 CPU 的指挥部件，核心任务是产生正确的操作控制信号和时序信号。",
    },
    {
        "chapter_id": 8,
        "type": "single_choice",
        "difficulty": "easy",
        "stem": "RISC-V 属于哪类指令集体系结构？",
        "options_json": [
            {"key": "A", "text": "复杂指令集 CISC"},
            {"key": "B", "text": "精简指令集 RISC"},
            {"key": "C", "text": "专用图形指令集"},
            {"key": "D", "text": "数据库查询语言"},
        ],
        "answer_json": {"answer": "B"},
        "explanation": "RISC-V 是开放的精简指令集架构。",
    },
    {
        "chapter_id": 9,
        "type": "true_false",
        "difficulty": "medium",
        "stem": "DMA 可以在不经过 CPU 逐字节干预的情况下完成主存与外设之间的数据传送。",
        "options_json": [{"key": "true", "text": "对"}, {"key": "false", "text": "错"}],
        "answer_json": {"answer": "TRUE"},
        "explanation": "DMA 通过专门控制器管理数据块传送，CPU 主要负责初始化和结束处理。",
    },
]


def main() -> None:
    with SessionLocal() as db:
        inserted = 0
        for item in QUESTIONS:
            exists = db.scalar(select(Question.id).where(Question.stem == item["stem"]))
            if exists:
                continue
            db.add(
                Question(
                    **item,
                    knowledge_point_id=None,
                    parent_question_id=None,
                    source_context="phase-1 sample seed",
                    source_assignment=None,
                    is_ai_generated=False,
                    is_reviewed=True,
                )
            )
            inserted += 1
        db.commit()
        print(f"Inserted {inserted} sample questions")


if __name__ == "__main__":
    main()
