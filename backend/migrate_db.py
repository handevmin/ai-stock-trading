"""데이터베이스 마이그레이션 스크립트"""
import sqlite3
from pathlib import Path
from app.config import settings
from app.utils.logger import logger

def migrate_database():
    """데이터베이스 스키마 마이그레이션"""
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    
    if not db_path.exists():
        logger.info("데이터베이스 파일이 없습니다. 새로 생성됩니다.")
        return
    
    logger.info(f"데이터베이스 마이그레이션 시작: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # strategies 테이블에 새 컬럼 추가
        cursor.execute("PRAGMA table_info(strategies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "stock_selection_mode" not in columns:
            logger.info("strategies 테이블에 stock_selection_mode 컬럼 추가 중...")
            cursor.execute("ALTER TABLE strategies ADD COLUMN stock_selection_mode VARCHAR DEFAULT 'watchlist'")
            conn.commit()
            logger.info("stock_selection_mode 컬럼 추가 완료")
        else:
            logger.info("stock_selection_mode 컬럼이 이미 존재합니다.")
        
        if "auto_selection_config" not in columns:
            logger.info("strategies 테이블에 auto_selection_config 컬럼 추가 중...")
            cursor.execute("ALTER TABLE strategies ADD COLUMN auto_selection_config JSON")
            conn.commit()
            logger.info("auto_selection_config 컬럼 추가 완료")
        else:
            logger.info("auto_selection_config 컬럼이 이미 존재합니다.")
        
        # watchlist 테이블 생성 (없는 경우)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='watchlist'
        """)
        if not cursor.fetchone():
            logger.info("watchlist 테이블 생성 중...")
            cursor.execute("""
                CREATE TABLE watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(6) NOT NULL,
                    stock_name VARCHAR,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX ix_watchlist_stock_code ON watchlist(stock_code)")
            conn.commit()
            logger.info("watchlist 테이블 생성 완료")
        else:
            logger.info("watchlist 테이블이 이미 존재합니다.")
        
        logger.info("데이터베이스 마이그레이션 완료")
        
    except Exception as e:
        logger.error(f"마이그레이션 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()


