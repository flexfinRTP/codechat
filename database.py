import os
import sqlite3
from datetime import datetime
import json
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConversationDatabase:
    def __init__(self, db_path='conversations.db'):
        """
        Initialize the conversation database with improved error handling and logging
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections with automatic commit/rollback
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()

    def _safe_add_column(self, cursor, table_name: str, column_name: str, column_type: str, default_value: str = 'NULL'):
        """
        Safely add a column to a table if it doesn't exist
        
        :param cursor: Database cursor
        :param table_name: Name of the table
        :param column_name: Name of the column to add
        :param column_type: SQLite column type
        :param default_value: Default value for the column
        """
        try:
            # Check if column exists
            cursor.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, so add it
            try:
                alter_query = f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {column_name} {column_type} DEFAULT {default_value}
                """
                cursor.execute(alter_query)
                self.logger.info(f"Added column {column_name} to {table_name}")
                
                # Update existing rows with default value
                update_query = f"""
                UPDATE {table_name} 
                SET {column_name} = {default_value} 
                WHERE {column_name} IS NULL
                """
                cursor.execute(update_query)
            except Exception as e:
                self.logger.error(f"Error adding column {column_name} to {table_name}: {str(e)}")
                raise

    def _migrate_database(self):
        """
        Perform comprehensive database migrations with improved error handling
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Migration steps for code_artifacts table
                migrations = [
                    {
                        'table': 'code_artifacts',
                        'columns': [
                            {'name': 'is_executable', 'type': 'INTEGER', 'default': '0'},
                            {'name': 'language', 'type': 'TEXT', 'default': "'markup'"},
                            {'name': 'metadata', 'type': 'TEXT', 'default': "'{}'"}
                        ]
                    }
                ]

                # Add metadata column to project_contexts if it doesn't exist
                self._safe_add_column(
                    cursor,
                    'project_contexts',
                    'metadata',
                    'TEXT',
                    "'{}'"
                )

                # Perform migrations
                for table_migration in migrations:
                    table_name = table_migration['table']
                    
                    # Get existing columns
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    existing_columns = {row['name'] for row in cursor.fetchall()}
                    
                    for column in table_migration['columns']:
                        if column['name'] not in existing_columns:
                            # Add missing column
                            alter_query = f'''
                                ALTER TABLE {table_name} 
                                ADD COLUMN {column['name']} {column['type']} 
                                DEFAULT {column['default']}
                            '''
                            cursor.execute(alter_query)
                            self.logger.info(f"Added {column['name']} column to {table_name} table")
                            
                            # Update existing rows
                            update_query = f'''
                                UPDATE {table_name} 
                                SET {column['name']} = {column['default']} 
                                WHERE {column['name']} IS NULL
                            '''
                            cursor.execute(update_query)

                # Add missing indexes
                indexes = [
                    ('idx_art_conv_lang', 'code_artifacts', 'conversation_id, language'),
                    ('idx_art_exec', 'code_artifacts', 'is_executable')
                ]
                
                for idx_name, table, columns in indexes:
                    try:
                        cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})')
                    except Exception as e:
                        self.logger.warning(f"Failed to create index {idx_name}: {str(e)}")
                
                self.logger.info("Database migration completed successfully")
                
        except Exception as e:
            self.logger.error(f"Database migration failed: {str(e)}")
            raise

    def _initialize_database(self):
        """
        Initialize database with improved schema and indexes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Create conversations table with additional metadata
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT DEFAULT 'Unnamed Conversation',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        total_input_tokens INTEGER DEFAULT 0,
                        total_output_tokens INTEGER DEFAULT 0,
                        is_deleted INTEGER DEFAULT 0,
                        is_favorite INTEGER DEFAULT 0,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Create messages table with improved structure
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER,
                        role TEXT CHECK(role IN ('user', 'assistant', 'system')),
                        content TEXT NOT NULL,
                        tokens_input INTEGER DEFAULT 0,
                        tokens_output INTEGER DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Create project_contexts table with file metadata
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_contexts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER,
                        file_path TEXT NOT NULL,
                        file_content TEXT NOT NULL,
                        file_type TEXT,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Create code_artifacts table with improved structure
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS code_artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER,
                        content TEXT NOT NULL,
                        language TEXT DEFAULT 'markup',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_executable INTEGER DEFAULT 0,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Create indexes for better query performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_deleted ON conversations(is_deleted)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(last_updated)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ctx_conv ON project_contexts(conversation_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_art_conv ON code_artifacts(conversation_id)')
                
                self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise

    def create_conversation(self, name: str = 'New Conversation', metadata: Dict = None) -> int:
        """
        Create a new conversation with metadata support
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversations (name, created_at, metadata)
                    VALUES (?, datetime('now'), ?)
                ''', (name, json.dumps(metadata or {})))
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {str(e)}")
            raise

    def rename_conversation(self, conversation_id: int, new_name: str) -> bool:
        """
        Rename a conversation with validation
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET name = ?, last_updated = datetime('now')
                    WHERE id = ? AND is_deleted = 0
                ''', (new_name, conversation_id))
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to rename conversation {conversation_id}: {str(e)}")
            raise

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Soft delete a conversation and associated data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET is_deleted = 1, last_updated = datetime('now')
                    WHERE id = ? AND is_deleted = 0
                ''', (conversation_id,))
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}")
            raise

    def get_conversation_name(self, conversation_id: int) -> Optional[str]:
        """
        Get conversation name by ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name FROM conversations 
                    WHERE id = ? AND is_deleted = 0
                ''', (conversation_id,))
                result = cursor.fetchone()
                return result['name'] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get conversation name {conversation_id}: {str(e)}")
            raise

    def add_message(self, conversation_id: int, role: str, content: str,
                   input_tokens: int = 0, output_tokens: int = 0,
                   metadata: Dict = None) -> int:
        """
        Add a message to a conversation with metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages 
                    (conversation_id, role, content, tokens_input, tokens_output, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, role, content, input_tokens, output_tokens,
                     json.dumps(metadata or {})))
                
                # Update conversation token counts and timestamp
                cursor.execute('''
                    UPDATE conversations 
                    SET total_input_tokens = total_input_tokens + ?,
                        total_output_tokens = total_output_tokens + ?,
                        last_updated = datetime('now')
                    WHERE id = ?
                ''', (input_tokens, output_tokens, conversation_id))
                
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to add message to conversation {conversation_id}: {str(e)}")
            raise

    def add_project_context(self, conversation_id: int, file_path: str,
                          file_content: str, file_type: str = None,
                          metadata: Dict = None) -> int:
        """
        Add project context with improved metadata handling
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for existing context
                cursor.execute('''
                    SELECT id FROM project_contexts 
                    WHERE conversation_id = ? AND file_path = ?
                ''', (conversation_id, file_path))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing context
                    cursor.execute('''
                        UPDATE project_contexts 
                        SET file_content = ?, file_type = ?, metadata = ?,
                            last_updated = datetime('now')
                        WHERE id = ?
                    ''', (file_content, file_type, json.dumps(metadata or {}),
                         existing['id']))
                    return existing['id']
                else:
                    # Insert new context
                    cursor.execute('''
                        INSERT INTO project_contexts 
                        (conversation_id, file_path, file_content, file_type, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (conversation_id, file_path, file_content, file_type,
                         json.dumps(metadata or {})))
                    return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to add project context: {str(e)}")
            raise

    def add_code_artifact(self, conversation_id: int, content: str,
                        language: str = 'markup', is_executable: bool = False,
                        metadata: Dict = None) -> int:
        """
        Add a code artifact with improved metadata handling
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Validate language
                language = language.lower()
                if not language:
                    language = 'markup'
                
                # Prepare metadata
                if metadata is None:
                    metadata = {}
                
                metadata.update({
                    'added_at': datetime.now().isoformat(),
                    'size': len(content),
                    'language_detected': language
                })
                
                cursor.execute('''
                    INSERT INTO code_artifacts 
                    (conversation_id, content, language, 
                    timestamp, is_executable, metadata)
                    VALUES (?, ?, ?, datetime('now'), ?, ?)
                ''', (
                    conversation_id,
                    content,
                    language,
                    1 if is_executable else 0,
                    json.dumps(metadata)
                ))
                
                # Update conversation last_updated
                cursor.execute('''
                    UPDATE conversations 
                    SET last_updated = datetime('now')
                    WHERE id = ?
                ''', (conversation_id,))
                
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to add code artifact: {str(e)}")
            raise

    def get_conversation_history(self, limit: int = 50,
                               include_deleted: bool = False) -> List[Dict]:
        """
        Get conversation history with improved metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                where_clause = '' if include_deleted else 'WHERE is_deleted = 0'
                cursor.execute(f'''
                    SELECT id, name, created_at, last_updated,
                           total_input_tokens, total_output_tokens,
                           is_favorite, metadata
                    FROM conversations 
                    {where_clause}
                    ORDER BY last_updated DESC 
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {str(e)}")
            raise

    def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        """
        Get messages for a conversation with metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, content, tokens_input, tokens_output,
                           timestamp, metadata
                    FROM messages 
                    WHERE conversation_id = ? 
                    ORDER BY timestamp ASC
                ''', (conversation_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get conversation messages: {str(e)}")
            raise

    def get_project_contexts(self, conversation_id: int) -> List[Dict]:
        """
        Get project contexts with metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_path, file_content, file_type,
                           last_updated, metadata
                    FROM project_contexts 
                    WHERE conversation_id = ?
                ''', (conversation_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get project contexts: {str(e)}")
            raise

    def get_code_artifacts(self, conversation_id: int) -> List[Dict]:
        """
        Get all code artifacts for a conversation with improved metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, content, language, timestamp,
                        is_executable, metadata
                    FROM code_artifacts 
                    WHERE conversation_id = ? 
                    ORDER BY timestamp ASC
                ''', (conversation_id,))
                
                artifacts = []
                for row in cursor.fetchall():
                    artifact = dict(row)
                    # Parse metadata if it exists
                    try:
                        artifact['metadata'] = json.loads(artifact['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        artifact['metadata'] = {}
                        
                    # Ensure proper timestamp format
                    if isinstance(artifact['timestamp'], str):
                        try:
                            # Validate timestamp format
                            datetime.strptime(artifact['timestamp'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            # If invalid, replace with current timestamp
                            artifact['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    artifacts.append(artifact)
                
                return artifacts
        except Exception as e:
            self.logger.error(f"Failed to get code artifacts: {str(e)}")
            raise

    def get_conversation_tokens(self, conversation_id: int) -> Dict[str, int]:
        """
        Get token counts for a conversation
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT total_input_tokens, total_output_tokens
                    FROM conversations 
                    WHERE id = ?
                ''', (conversation_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        "total_input_tokens": result['total_input_tokens'],
                        "total_output_tokens": result['total_output_tokens'],
                        "total_tokens": result['total_input_tokens'] + result['total_output_tokens']
                    }
                return {"total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0}
        except Exception as e:
            self.logger.error(f"Failed to get conversation tokens: {str(e)}")
            raise

    def toggle_favorite(self, conversation_id: int) -> bool:
        """
        Toggle favorite status of a conversation
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET is_favorite = CASE WHEN is_favorite = 0 THEN 1 ELSE 0 END,
                        last_updated = datetime('now')
                    WHERE id = ? AND is_deleted = 0
                ''', (conversation_id,))
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to toggle favorite: {str(e)}")
            raise

    def get_conversation_stats(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a conversation
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        c.total_input_tokens,
                        c.total_output_tokens,
                        c.created_at,
                        c.last_updated,
                        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
                        (SELECT COUNT(*) FROM code_artifacts WHERE conversation_id = c.id) as artifact_count,
                        (SELECT COUNT(*) FROM project_contexts WHERE conversation_id = c.id) as context_count
                    FROM conversations c
                    WHERE c.id = ? AND c.is_deleted = 0
                ''', (conversation_id,))
                result = cursor.fetchone()
                if not result:
                    return {}
                
                return {
                    "total_input_tokens": result['total_input_tokens'],
                    "total_output_tokens": result['total_output_tokens'],
                    "total_tokens": result['total_input_tokens'] + result['total_output_tokens'],
                    "message_count": result['message_count'],
                    "artifact_count": result['artifact_count'],
                    "context_count": result['context_count'],
                    "created_at": result['created_at'],
                    "last_updated": result['last_updated'],
                    "duration": self._calculate_duration(result['created_at'], result['last_updated'])
                }
        except Exception as e:
            self.logger.error(f"Failed to get conversation stats: {str(e)}")
            raise

    def _calculate_duration(self, start: str, end: str) -> str:
        """
        Calculate human-readable duration between two timestamps
        """
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
            duration = end_dt - start_dt
            
            if duration.days > 0:
                return f"{duration.days} days"
            hours = duration.seconds // 3600
            if hours > 0:
                return f"{hours} hours"
            minutes = (duration.seconds % 3600) // 60
            if minutes > 0:
                return f"{minutes} minutes"
            return f"{duration.seconds} seconds"
        except Exception as e:
            self.logger.error(f"Failed to calculate duration: {str(e)}")
            return "unknown duration"

    def cleanup_old_conversations(self, days: int = 30) -> int:
        """
        Clean up conversations older than specified days
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations
                    SET is_deleted = 1
                    WHERE last_updated < datetime('now', ?) 
                    AND is_deleted = 0
                    AND is_favorite = 0
                ''', (f'-{days} days',))
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Failed to cleanup old conversations: {str(e)}")
            raise

    def export_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """
        Export a complete conversation with all related data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get conversation details
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE id = ? AND is_deleted = 0
                ''', (conversation_id,))
                conversation = dict(cursor.fetchone())
                
                # Get messages
                cursor.execute('SELECT * FROM messages WHERE conversation_id = ?', (conversation_id,))
                messages = [dict(row) for row in cursor.fetchall()]
                
                # Get contexts
                cursor.execute('SELECT * FROM project_contexts WHERE conversation_id = ?', (conversation_id,))
                contexts = [dict(row) for row in cursor.fetchall()]
                
                # Get artifacts
                cursor.execute('SELECT * FROM code_artifacts WHERE conversation_id = ?', (conversation_id,))
                artifacts = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "conversation": conversation,
                    "messages": messages,
                    "contexts": contexts,
                    "artifacts": artifacts,
                    "stats": self.get_conversation_stats(conversation_id),
                    "export_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            self.logger.error(f"Failed to export conversation {conversation_id}: {str(e)}")
            raise

    def import_conversation(self, data: Dict[str, Any]) -> int:
        """
        Import a conversation from exported data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert conversation
                conv_data = data['conversation']
                cursor.execute('''
                    INSERT INTO conversations 
                    (name, created_at, last_updated, total_input_tokens, 
                     total_output_tokens, is_favorite, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conv_data['name'],
                    conv_data['created_at'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    conv_data['total_input_tokens'],
                    conv_data['total_output_tokens'],
                    conv_data.get('is_favorite', 0),
                    conv_data.get('metadata', '{}')
                ))
                new_conv_id = cursor.lastrowid
                
                # Import messages
                for msg in data['messages']:
                    cursor.execute('''
                        INSERT INTO messages 
                        (conversation_id, role, content, tokens_input, 
                         tokens_output, timestamp, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        new_conv_id,
                        msg['role'],
                        msg['content'],
                        msg['tokens_input'],
                        msg['tokens_output'],
                        msg['timestamp'],
                        msg.get('metadata', '{}')
                    ))
                
                # Import contexts
                for ctx in data['contexts']:
                    cursor.execute('''
                        INSERT INTO project_contexts 
                        (conversation_id, file_path, file_content, 
                         file_type, last_updated, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        new_conv_id,
                        ctx['file_path'],
                        ctx['file_content'],
                        ctx.get('file_type'),
                        ctx['last_updated'],
                        ctx.get('metadata', '{}')
                    ))
                
                # Import artifacts
                for art in data['artifacts']:
                    cursor.execute('''
                        INSERT INTO code_artifacts 
                        (conversation_id, content, language, 
                         timestamp, is_executable, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        new_conv_id,
                        art['content'],
                        art['language'],
                        art['timestamp'],
                        art.get('is_executable', 0),
                        art.get('metadata', '{}')
                    ))
                
                return new_conv_id
        except Exception as e:
            self.logger.error(f"Failed to import conversation: {str(e)}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Get total counts
                cursor.execute('SELECT COUNT(*) FROM conversations WHERE is_deleted = 0')
                stats['active_conversations'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM messages')
                stats['total_messages'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM code_artifacts')
                stats['total_artifacts'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM project_contexts')
                stats['total_contexts'] = cursor.fetchone()[0]
                
                # Get token statistics
                cursor.execute('''
                    SELECT 
                        SUM(total_input_tokens) as total_input,
                        SUM(total_output_tokens) as total_output
                    FROM conversations
                    WHERE is_deleted = 0
                ''')
                token_stats = cursor.fetchone()
                stats['total_input_tokens'] = token_stats[0] or 0
                stats['total_output_tokens'] = token_stats[1] or 0
                stats['total_tokens'] = (token_stats[0] or 0) + (token_stats[1] or 0)
                
                # Get database size
                stats['database_size'] = os.path.getsize(self.db_path)
                
                return stats
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            raise
