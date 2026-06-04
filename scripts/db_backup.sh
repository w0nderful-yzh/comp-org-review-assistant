#!/bin/bash
# 数据库备份与恢复脚本
# 用法:
#   ./scripts/db_backup.sh export    # 导出数据库
#   ./scripts/db_backup.sh import    # 导入数据库
#   ./scripts/db_backup.sh status    # 查看数据库状态

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/comp_org_backup_${TIMESTAMP}.sql"
CONTAINER_NAME="comp-org-postgres"
DB_USER="${POSTGRES_USER:-comp_org}"
DB_NAME="${POSTGRES_DB:-comp_org_review}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查容器是否运行
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "容器 ${CONTAINER_NAME} 未运行，请先启动: docker compose up -d"
        exit 1
    fi
}

# 导出数据库
do_export() {
    check_container
    mkdir -p "$BACKUP_DIR"

    print_info "正在导出数据库..."
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$BACKUP_FILE"

    # 压缩备份文件
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"

    FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    print_info "导出完成: ${BACKUP_FILE} (${FILESIZE})"
    print_info "包含数据:"
    echo "  - 章节、知识点、题目（含 AI 生成题目）"
    echo "  - 练习记录、答题记录"
    echo "  - 错题本"
    echo "  - 知识库 chunks"
    echo "  - 用户账号信息"
}

# 导入数据库
do_import() {
    check_container

    # 查找最新的备份文件
    if [ -n "$2" ]; then
        IMPORT_FILE="$2"
    else
        IMPORT_FILE=$(ls -t ${BACKUP_DIR}/comp_org_backup_*.sql.gz 2>/dev/null | head -1)
    fi

    if [ -z "$IMPORT_FILE" ] || [ ! -f "$IMPORT_FILE" ]; then
        print_error "找不到备份文件，请指定文件路径: ./scripts/db_backup.sh import <file>"
        exit 1
    fi

    print_warn "即将导入: ${IMPORT_FILE}"
    print_warn "这将覆盖现有数据！"
    read -p "确认继续？(y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "已取消"
        exit 0
    fi

    print_info "正在导入数据库..."

    # 如果是压缩文件，先解压
    if [[ "$IMPORT_FILE" == *.gz ]]; then
        gunzip -c "$IMPORT_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1
    else
        docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$IMPORT_FILE" > /dev/null 2>&1
    fi

    print_info "导入完成！"
    print_info "验证数据..."
    do_status
}

# 查看数据库状态
do_status() {
    check_container

    echo ""
    print_info "数据库统计:"

    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT '  章节: ' || count(*) FROM chapters
        UNION ALL
        SELECT '  知识点: ' || count(*) FROM knowledge_points
        UNION ALL
        SELECT '  题目: ' || count(*) FROM questions
        UNION ALL
        SELECT '    - 原始题: ' || count(*) FROM questions WHERE is_ai_generated = false
        UNION ALL
        SELECT '    - AI题: ' || count(*) FROM questions WHERE is_ai_generated = true
        UNION ALL
        SELECT '  练习记录: ' || count(*) FROM practice_sessions
        UNION ALL
        SELECT '  答题记录: ' || count(*) FROM answer_records
        UNION ALL
        SELECT '  错题: ' || count(*) FROM wrong_questions
        UNION ALL
        SELECT '  用户: ' || count(*) FROM users
        UNION ALL
        SELECT '  知识块: ' || count(*) FROM knowledge_chunks;
    "

    echo ""
    print_info "备份文件列表:"
    if ls ${BACKUP_DIR}/comp_org_backup_*.sql.gz 1> /dev/null 2>&1; then
        ls -lh ${BACKUP_DIR}/comp_org_backup_*.sql.gz | awk '{print "  " $NF " (" $5 ")"}'
    else
        echo "  (无备份文件)"
    fi
    echo ""
}

# 显示帮助
show_help() {
    echo "数据库备份与恢复脚本"
    echo ""
    echo "用法: ./scripts/db_backup.sh <command> [options]"
    echo ""
    echo "命令:"
    echo "  export          导出当前数据库到备份文件"
    echo "  import [file]   导入备份文件（默认使用最新备份）"
    echo "  status          查看数据库统计和备份列表"
    echo ""
    echo "示例:"
    echo "  ./scripts/db_backup.sh export"
    echo "  ./scripts/db_backup.sh import"
    echo "  ./scripts/db_backup.sh import ./backups/comp_org_backup_20240101_120000.sql.gz"
    echo "  ./scripts/db_backup.sh status"
}

# 主逻辑
case "${1:-}" in
    export)
        do_export
        ;;
    import)
        do_import "$@"
        ;;
    status)
        do_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
