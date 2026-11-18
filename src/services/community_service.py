"""
AgriMind Farmer Community & Social Connection Service.
Provides peer-to-peer agricultural discussions, knowledge sharing,
threaded Q&A replies, helpful/like reactions, solution acceptance,
content reporting, and owner/moderator controls.
"""
import os
import sys
import uuid
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.environ.get(
    "DATABASE_URL",
    os.environ.get("AGRIMIND_DB_URL", os.path.join(WORKSPACE_DIR, "data", "cases.db"))
)
COMMUNITY_UPLOADS_DIR = os.environ.get(
    "AGRIMIND_UPLOADS_DIR",
    os.path.join(WORKSPACE_DIR, "data", "community_uploads")
)

logger = logging.getLogger(__name__)

# Predefined valid agricultural categories
VALID_COMMUNITY_CATEGORIES = [
    "crop_disease",
    "pest_management",
    "irrigation",
    "soil_health",
    "fertilizers",
    "weather_impacts",
    "general_farming"
]

CATEGORY_LABELS = {
    "crop_disease": "Crop Disease",
    "pest_management": "Pest Management",
    "irrigation": "Irrigation",
    "soil_health": "Soil Health",
    "fertilizers": "Fertilizers & Nutrients",
    "weather_impacts": "Weather Impacts",
    "general_farming": "General Farming Advice"
}


try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class DBConnectionWrapper:
    """
    Transparent connection wrapper enabling uniform parameterized query execution
    across Neon PostgreSQL (psycopg2) and local development / test SQLite instances.
    """
    def __init__(self, raw_conn, is_postgres: bool):
        self._conn = raw_conn
        self.is_postgres = is_postgres

    def execute(self, sql: str, params: tuple = ()):
        formatted_sql = sql.replace("?", "%s") if self.is_postgres else sql.replace("%s", "?")
        if self.is_postgres:
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = self._conn.cursor()
        cur.execute(formatted_sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


class CommunityService:
    """Manages farmer community posts, comments, threaded replies, reactions, and reports."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.is_postgres = str(db_path).startswith("postgres://") or str(db_path).startswith("postgresql://")
        if self.is_postgres and not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL database URL specified, but 'psycopg2' is not installed.")
        self._ensure_db()
        if not self.is_postgres:
            os.makedirs(COMMUNITY_UPLOADS_DIR, exist_ok=True)

    def _ensure_db(self):
        if not self.is_postgres and self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        with self._connection() as conn:
            # 1. Community Posts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_posts (
                    post_id TEXT PRIMARY KEY,
                    author_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_role TEXT NOT NULL DEFAULT 'farmer',
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general_farming',
                    image_url TEXT,
                    likes_count INTEGER NOT NULL DEFAULT 0,
                    comments_count INTEGER NOT NULL DEFAULT 0,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    is_resolved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(author_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON community_posts(created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON community_posts(category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_author ON community_posts(author_id);")

            # 2. Community Comments & Threaded Replies
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_comments (
                    comment_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    parent_comment_id TEXT,
                    author_id TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    author_role TEXT NOT NULL DEFAULT 'farmer',
                    comment_text TEXT NOT NULL,
                    likes_count INTEGER NOT NULL DEFAULT 0,
                    is_accepted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
                    FOREIGN KEY(author_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comm_post ON community_comments(post_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comm_parent ON community_comments(parent_comment_id);")

            # 3. Community Reactions (Likes & Helpful Votes)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_reactions (
                    reaction_id TEXT PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    reaction_type TEXT NOT NULL DEFAULT 'like',
                    created_at TEXT NOT NULL,
                    UNIQUE(target_type, target_id, user_id, reaction_type),
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reactions_target ON community_reactions(target_type, target_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reactions_user ON community_reactions(user_id);")

            # 4. Community Reports (Moderation & Safety)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS community_reports (
                    report_id TEXT PRIMARY KEY,
                    reporter_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    details TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    FOREIGN KEY(reporter_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON community_reports(status);")

            conn.commit()

    @contextmanager
    def _connection(self):
        if self.is_postgres:
            raw_conn = psycopg2.connect(self.db_path)
            raw_conn.autocommit = False
            wrapper = DBConnectionWrapper(raw_conn, is_postgres=True)
            try:
                yield wrapper
                wrapper.commit()
            except Exception:
                wrapper.rollback()
                raise
            finally:
                wrapper.close()
        else:
            raw_conn = sqlite3.connect(self.db_path, timeout=10.0)
            raw_conn.row_factory = sqlite3.Row
            wrapper = DBConnectionWrapper(raw_conn, is_postgres=False)
            try:
                yield wrapper
                wrapper.commit()
            except Exception:
                wrapper.rollback()
                raise
            finally:
                wrapper.close()

    # =========================================================================
    # Posts Management
    # =========================================================================

    def create_post(
        self,
        author_user: Dict[str, Any],
        title: str,
        content: str,
        category: str = "general_farming",
        image_url: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Creates a new farmer community post."""
        clean_title = (title or "").strip()
        clean_content = (content or "").strip()

        if len(clean_title) < 3:
            return False, "Post title must be at least 3 characters long.", None
        if len(clean_content) < 5:
            return False, "Post content must be at least 5 characters long.", None

        clean_cat = category.strip().lower()
        if clean_cat not in VALID_COMMUNITY_CATEGORIES:
            clean_cat = "general_farming"

        post_id = f"POST-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        author_id = author_user.get("user_id", author_user.get("sub", ""))
        author_name = author_user.get("full_name") or author_user.get("email", "Farmer")
        author_role = author_user.get("role", "farmer")

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO community_posts (
                    post_id, author_id, author_name, author_role,
                    title, content, category, image_url,
                    likes_count, comments_count, is_pinned, is_resolved,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?);
            """, (
                post_id, author_id, author_name, author_role,
                clean_title, clean_content, clean_cat, image_url,
                now, now
            ))
            conn.commit()

        post_dict = {
            "post_id": post_id,
            "author_id": author_id,
            "author_name": author_name,
            "author_role": author_role,
            "title": clean_title,
            "content": clean_content,
            "category": clean_cat,
            "category_label": CATEGORY_LABELS.get(clean_cat, clean_cat),
            "image_url": image_url,
            "likes_count": 0,
            "comments_count": 0,
            "has_liked": False,
            "is_pinned": False,
            "is_resolved": False,
            "created_at": now,
            "updated_at": now
        }
        return True, "Post created successfully.", post_dict

    def get_feed(
        self,
        current_user_id: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Retrieves paginated community feed with search and category filters."""
        limit = max(1, min(limit, 50))
        offset = max(0, offset)

        params: List[Any] = []
        where_clauses = ["1=1"]

        if category and category.strip():
            cat = category.strip().lower()
            if cat in VALID_COMMUNITY_CATEGORIES:
                where_clauses.append("p.category = ?")
                params.append(cat)

        if query and query.strip():
            clean_q = f"%{query.strip().lower()}%"
            where_clauses.append("(LOWER(p.title) LIKE ? OR LOWER(p.content) LIKE ?)")
            params.extend([clean_q, clean_q])

        where_str = " AND ".join(where_clauses)

        with self._connection() as conn:
            # Count total
            total_count_row = conn.execute(f"SELECT COUNT(*) AS count FROM community_posts p WHERE {where_str};", params).fetchone()
            total_count = total_count_row["count"] if total_count_row else 0

            # Fetch page
            query_sql = f"""
                SELECT p.post_id, p.author_id, p.author_name, p.author_role,
                       p.title, p.content, p.category, p.image_url,
                       p.likes_count, p.comments_count, p.is_pinned, p.is_resolved,
                       p.created_at, p.updated_at,
                       CASE WHEN r.reaction_id IS NOT NULL THEN 1 ELSE 0 END AS has_liked
                FROM community_posts p
                LEFT JOIN community_reactions r
                    ON r.target_type = 'post' AND r.target_id = p.post_id AND r.user_id = ?
                WHERE {where_str}
                ORDER BY p.is_pinned DESC, p.created_at DESC
                LIMIT ? OFFSET ?;
            """
            exec_params = [current_user_id or ""] + params + [limit, offset]
            rows = conn.execute(query_sql, exec_params).fetchall()

            posts = []
            for r in rows:
                p_dict = dict(r)
                p_dict["has_liked"] = bool(p_dict.get("has_liked", 0))
                p_dict["is_pinned"] = bool(p_dict.get("is_pinned", 0))
                p_dict["is_resolved"] = bool(p_dict.get("is_resolved", 0))
                p_dict["category_label"] = CATEGORY_LABELS.get(p_dict["category"], p_dict["category"])
                posts.append(p_dict)

            has_more = (offset + len(posts)) < total_count

            return {
                "posts": posts,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            }

    def get_post_by_id(
        self,
        post_id: str,
        current_user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a single community post by ID."""
        with self._connection() as conn:
            row = conn.execute("""
                SELECT p.post_id, p.author_id, p.author_name, p.author_role,
                       p.title, p.content, p.category, p.image_url,
                       p.likes_count, p.comments_count, p.is_pinned, p.is_resolved,
                       p.created_at, p.updated_at,
                       CASE WHEN r.reaction_id IS NOT NULL THEN 1 ELSE 0 END AS has_liked
                FROM community_posts p
                LEFT JOIN community_reactions r
                    ON r.target_type = 'post' AND r.target_id = p.post_id AND r.user_id = %s
                WHERE p.post_id = %s;
            """, (current_user_id or "", post_id)).fetchone()

            if not row:
                return None

            p = dict(row)
            p["has_liked"] = bool(p.get("has_liked", 0))
            p["is_pinned"] = bool(p.get("is_pinned", 0))
            p["is_resolved"] = bool(p.get("is_resolved", 0))
            p["category_label"] = CATEGORY_LABELS.get(p["category"], p["category"])
            return p

    def update_post(
        self,
        acting_user: Dict[str, Any],
        post_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Edits an existing post. Only author can edit post text."""
        post = self.get_post_by_id(post_id)
        if not post:
            return False, f"Post '{post_id}' not found.", None

        actor_id = acting_user.get("user_id", acting_user.get("sub", ""))
        if actor_id != post["author_id"]:
            return False, "Forbidden: Only the post author can edit this post.", None

        updates = []
        params = []

        if title is not None:
            clean_title = title.strip()
            if len(clean_title) < 3:
                return False, "Title must be at least 3 characters long.", None
            updates.append("title = ?")
            params.append(clean_title)

        if content is not None:
            clean_content = content.strip()
            if len(clean_content) < 5:
                return False, "Content must be at least 5 characters long.", None
            updates.append("content = ?")
            params.append(clean_content)

        if category is not None:
            clean_cat = category.strip().lower()
            if clean_cat in VALID_COMMUNITY_CATEGORIES:
                updates.append("category = ?")
                params.append(clean_cat)

        if image_url is not None:
            updates.append("image_url = ?")
            params.append(image_url)

        if not updates:
            return True, "No changes provided.", post

        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(post_id)

        with self._connection() as conn:
            conn.execute(f"UPDATE community_posts SET {', '.join(updates)} WHERE post_id = ?;", params)
            conn.commit()

        updated_post = self.get_post_by_id(post_id, current_user_id=actor_id)
        return True, "Post updated successfully.", updated_post

    def delete_post(
        self,
        acting_user: Dict[str, Any],
        post_id: str,
        auth_service: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """
        Deletes a post. Permitted for:
        1. Author of the post
        2. Main Project Owner ('owner')
        3. Sub-Owner possessing 'can_moderate_cases' permission
        """
        post = self.get_post_by_id(post_id)
        if not post:
            return False, f"Post '{post_id}' not found."

        actor_id = acting_user.get("user_id", acting_user.get("sub", ""))
        actor_role = acting_user.get("role", "farmer")

        is_author = (actor_id == post["author_id"])
        is_owner = (actor_role == "owner")
        is_moderator = False
        if auth_service and actor_role == "sub_owner":
            is_moderator = auth_service.has_permission(acting_user, "can_moderate_cases")

        if not (is_author or is_owner or is_moderator):
            return False, "Forbidden: You do not have permission to delete this post."

        with self._connection() as conn:
            conn.execute("DELETE FROM community_reports WHERE target_type = 'post' AND target_id = %s;", (post_id,))
            conn.execute("DELETE FROM community_reactions WHERE target_type = 'post' AND target_id = %s;", (post_id,))
            # Delete comments and comment reactions
            comment_ids = [row["comment_id"] for row in conn.execute("SELECT comment_id FROM community_comments WHERE post_id = %s;", (post_id,)).fetchall()]
            for cid in comment_ids:
                conn.execute("DELETE FROM community_reactions WHERE target_type = 'comment' AND target_id = %s;", (cid,))
                conn.execute("DELETE FROM community_reports WHERE target_type = 'comment' AND target_id = %s;", (cid,))
            conn.execute("DELETE FROM community_comments WHERE post_id = %s;", (post_id,))
            conn.execute("DELETE FROM community_posts WHERE post_id = %s;", (post_id,))
            conn.commit()

        # Audit moderation deletion
        if not is_author and auth_service:
            auth_service.log_audit_event(
                actor_id=actor_id,
                actor_email=acting_user.get("email", ""),
                actor_role=actor_role,
                action="COMMUNITY_POST_MODERATED",
                details=f"Moderator deleted community post '{post['title']}' by author {post['author_name']}.",
                target_user_id=post["author_id"]
            )

        return True, "Post deleted successfully."

    # =========================================================================
    # Comments & Threaded Replies Management
    # =========================================================================

    def add_comment(
        self,
        author_user: Dict[str, Any],
        post_id: str,
        comment_text: str,
        parent_comment_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Adds a comment or threaded reply to a post."""
        clean_text = (comment_text or "").strip()
        if len(clean_text) < 1:
            return False, "Comment text cannot be empty.", None

        # Verify post exists
        post = self.get_post_by_id(post_id)
        if not post:
            return False, f"Post '{post_id}' does not exist.", None

        # Verify parent comment exists if provided
        if parent_comment_id:
            with self._connection() as conn:
                parent = conn.execute("SELECT comment_id FROM community_comments WHERE comment_id = %s AND post_id = %s;", (parent_comment_id, post_id)).fetchone()
                if not parent:
                    return False, f"Parent comment '{parent_comment_id}' not found on this post.", None

        comment_id = f"COMM-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        author_id = author_user.get("user_id", author_user.get("sub", ""))
        author_name = author_user.get("full_name") or author_user.get("email", "Farmer")
        author_role = author_user.get("role", "farmer")

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO community_comments (
                    comment_id, post_id, parent_comment_id,
                    author_id, author_name, author_role,
                    comment_text, likes_count, is_accepted,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?);
            """, (
                comment_id, post_id, parent_comment_id,
                author_id, author_name, author_role,
                clean_text, now, now
            ))
            # Increment post comments_count
            conn.execute("UPDATE community_posts SET comments_count = comments_count + 1 WHERE post_id = %s;", (post_id,))
            conn.commit()

        comment_dict = {
            "comment_id": comment_id,
            "post_id": post_id,
            "parent_comment_id": parent_comment_id,
            "author_id": author_id,
            "author_name": author_name,
            "author_role": author_role,
            "comment_text": clean_text,
            "likes_count": 0,
            "has_liked": False,
            "is_accepted": False,
            "created_at": now,
            "updated_at": now,
            "replies": []
        }
        return True, "Comment added successfully.", comment_dict

    def get_comments(
        self,
        post_id: str,
        current_user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves threaded comments and replies for a post."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT c.comment_id, c.post_id, c.parent_comment_id,
                       c.author_id, c.author_name, c.author_role,
                       c.comment_text, c.likes_count, c.is_accepted,
                       c.created_at, c.updated_at,
                       CASE WHEN r.reaction_id IS NOT NULL THEN 1 ELSE 0 END AS has_liked
                FROM community_comments c
                LEFT JOIN community_reactions r
                    ON r.target_type = 'comment' AND r.target_id = c.comment_id AND r.user_id = %s
                WHERE c.post_id = %s
                ORDER BY c.is_accepted DESC, c.created_at ASC;
            """, (current_user_id or "", post_id)).fetchall()

        all_comments = []
        top_level_map: Dict[str, Dict[str, Any]] = {}
        child_replies: List[Dict[str, Any]] = []

        for row in rows:
            c = dict(row)
            c["has_liked"] = bool(c.get("has_liked", 0))
            c["is_accepted"] = bool(c.get("is_accepted", 0))
            c["replies"] = []

            if not c["parent_comment_id"]:
                top_level_map[c["comment_id"]] = c
                all_comments.append(c)
            else:
                child_replies.append(c)

        # Attach replies to parent comments
        for child in child_replies:
            parent_id = child["parent_comment_id"]
            if parent_id in top_level_map:
                top_level_map[parent_id]["replies"].append(child)
            else:
                # If parent not found at top level, treat as top level
                all_comments.append(child)

        return all_comments

    def delete_comment(
        self,
        acting_user: Dict[str, Any],
        comment_id: str,
        auth_service: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """Deletes a comment. Permitted for comment author or authorized moderator."""
        with self._connection() as conn:
            row = conn.execute("SELECT comment_id, post_id, author_id, author_name FROM community_comments WHERE comment_id = %s;", (comment_id,)).fetchone()
            if not row:
                return False, f"Comment '{comment_id}' not found."

            post_id = row["post_id"]
            comment_author_id = row["author_id"]

            actor_id = acting_user.get("user_id", acting_user.get("sub", ""))
            actor_role = acting_user.get("role", "farmer")

            is_author = (actor_id == comment_author_id)
            is_owner = (actor_role == "owner")
            is_moderator = False
            if auth_service and actor_role == "sub_owner":
                is_moderator = auth_service.has_permission(acting_user, "can_moderate_cases")

            if not (is_author or is_owner or is_moderator):
                return False, "Forbidden: You do not have permission to delete this comment."

            # Delete child replies and reactions
            child_ids = [r["comment_id"] for r in conn.execute("SELECT comment_id FROM community_comments WHERE parent_comment_id = %s;", (comment_id,)).fetchall()]
            for cid in child_ids:
                conn.execute("DELETE FROM community_reactions WHERE target_type = 'comment' AND target_id = %s;", (cid,))
                conn.execute("DELETE FROM community_reports WHERE target_type = 'comment' AND target_id = %s;", (cid,))
            conn.execute("DELETE FROM community_comments WHERE parent_comment_id = %s;", (comment_id,))

            conn.execute("DELETE FROM community_reactions WHERE target_type = 'comment' AND target_id = %s;", (comment_id,))
            conn.execute("DELETE FROM community_reports WHERE target_type = 'comment' AND target_id = %s;", (comment_id,))
            conn.execute("DELETE FROM community_comments WHERE comment_id = %s;", (comment_id,))

            # Decrement comment count on post (GREATEST for PostgreSQL, MAX for SQLite)
            deleted_count = 1 + len(child_ids)
            max_fn = "GREATEST" if self.is_postgres else "MAX"
            conn.execute(f"UPDATE community_posts SET comments_count = {max_fn}(0, comments_count - %s) WHERE post_id = %s;", (deleted_count, post_id))
            conn.commit()

        if not is_author and auth_service:
            auth_service.log_audit_event(
                actor_id=actor_id,
                actor_email=acting_user.get("email", ""),
                actor_role=actor_role,
                action="COMMUNITY_COMMENT_MODERATED",
                details=f"Moderator deleted comment '{comment_id}' from post '{post_id}'.",
                target_user_id=comment_author_id
            )

        return True, "Comment removed successfully."

    def mark_accepted_answer(
        self,
        acting_user: Dict[str, Any],
        post_id: str,
        comment_id: str
    ) -> Tuple[bool, str]:
        """
        Marks or unmarks a comment as the accepted helpful solution.
        STRICT REQUIREMENT: ONLY the author of the post can mark an answer as accepted.
        """
        post = self.get_post_by_id(post_id)
        if not post:
            return False, f"Post '{post_id}' not found."

        actor_id = acting_user.get("user_id", acting_user.get("sub", ""))
        if actor_id != post["author_id"]:
            return False, "Forbidden: Only the question author can accept a community solution."

        with self._connection() as conn:
            comm = conn.execute("SELECT comment_id, is_accepted FROM community_comments WHERE comment_id = %s AND post_id = %s;", (comment_id, post_id)).fetchone()
            if not comm:
                return False, f"Comment '{comment_id}' does not exist on post '{post_id}'."

            current_status = bool(comm["is_accepted"])
            new_status = not current_status

            # Clear any previously accepted comments on this post if setting new one
            if new_status:
                conn.execute("UPDATE community_comments SET is_accepted = 0 WHERE post_id = %s;", (post_id,))

            conn.execute("UPDATE community_comments SET is_accepted = %s WHERE comment_id = %s;", (1 if new_status else 0, comment_id))
            conn.execute("UPDATE community_posts SET is_resolved = %s WHERE post_id = %s;", (1 if new_status else 0, post_id))
            conn.commit()

        msg = "Solution marked as accepted answer." if new_status else "Solution acceptance removed."
        return True, msg

    # =========================================================================
    # Reactions (Like / Helpful)
    # =========================================================================

    def toggle_reaction(
        self,
        acting_user: Dict[str, Any],
        target_type: str,
        target_id: str,
        reaction_type: str = "like"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Toggles a like or helpful reaction on a post or comment."""
        clean_target_type = target_type.strip().lower()
        if clean_target_type not in ("post", "comment"):
            return False, "Invalid target type. Must be 'post' or 'comment'.", {}

        clean_rx_type = (reaction_type or "like").strip().lower()
        user_id = acting_user.get("user_id", acting_user.get("sub", ""))

        table_name = "community_posts" if clean_target_type == "post" else "community_comments"
        id_col = "post_id" if clean_target_type == "post" else "comment_id"

        with self._connection() as conn:
            # Check target exists
            target = conn.execute(f"SELECT {id_col}, likes_count FROM {table_name} WHERE {id_col} = %s;", (target_id,)).fetchone()
            if not target:
                return False, f"Target {clean_target_type} '{target_id}' not found.", {}

            # Check if reaction exists
            existing = conn.execute("""
                SELECT reaction_id FROM community_reactions
                WHERE target_type = %s AND target_id = %s AND user_id = %s AND reaction_type = %s;
            """, (clean_target_type, target_id, user_id, clean_rx_type)).fetchone()

            if existing:
                # Remove reaction (GREATEST for PostgreSQL, MAX for SQLite)
                max_fn = "GREATEST" if self.is_postgres else "MAX"
                conn.execute("DELETE FROM community_reactions WHERE reaction_id = %s;", (existing["reaction_id"],))
                conn.execute(f"UPDATE {table_name} SET likes_count = {max_fn}(0, likes_count - 1) WHERE {id_col} = %s;", (target_id,))
                conn.commit()
                has_liked = False
                msg = "Reaction removed."
            else:
                # Add reaction
                rx_id = f"RX-{uuid.uuid4().hex[:10].upper()}"
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT INTO community_reactions (reaction_id, target_type, target_id, user_id, reaction_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (rx_id, clean_target_type, target_id, user_id, clean_rx_type, now))
                conn.execute(f"UPDATE {table_name} SET likes_count = likes_count + 1 WHERE {id_col} = %s;", (target_id,))
                conn.commit()
                has_liked = True
                msg = "Reaction recorded."

            new_count = conn.execute(f"SELECT likes_count FROM {table_name} WHERE {id_col} = %s;", (target_id,)).fetchone()["likes_count"]

        return True, msg, {
            "target_type": clean_target_type,
            "target_id": target_id,
            "likes_count": new_count,
            "has_liked": has_liked
        }

    # =========================================================================
    # Reporting & Community Safety
    # =========================================================================

    def report_content(
        self,
        reporter_user: Dict[str, Any],
        target_type: str,
        target_id: str,
        reason: str,
        details: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Submits a safety/moderation report for inappropriate content."""
        clean_target = target_type.strip().lower()
        if clean_target not in ("post", "comment"):
            return False, "Target must be 'post' or 'comment'."

        clean_reason = (reason or "").strip()
        if not clean_reason:
            clean_reason = "inappropriate"

        reporter_id = reporter_user.get("user_id", reporter_user.get("sub", ""))
        report_id = f"REP-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO community_reports (
                    report_id, reporter_id, target_type, target_id,
                    reason, details, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?);
            """, (
                report_id, reporter_id, clean_target, target_id,
                clean_reason, details, now
            ))
            conn.commit()

        return True, "Report submitted successfully. Community moderators will review this content."

    def list_reports(
        self,
        acting_user: Dict[str, Any],
        auth_service: Optional[Any] = None,
        limit: int = 50
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Lists pending moderation reports (moderators & owners only)."""
        actor_role = acting_user.get("role", "farmer")
        is_owner = (actor_role == "owner")
        is_moderator = False
        if auth_service and actor_role == "sub_owner":
            is_moderator = auth_service.has_permission(acting_user, "can_moderate_cases")

        if not (is_owner or is_moderator):
            return False, "Forbidden: Only community moderators can view reports.", []

        with self._connection() as conn:
            rows = conn.execute("""
                SELECT report_id, reporter_id, target_type, target_id,
                       reason, details, status, created_at, reviewed_by, reviewed_at
                FROM community_reports
                ORDER BY created_at DESC LIMIT %s;
            """, (limit,)).fetchall()
            return True, "Reports retrieved.", [dict(r) for r in rows]

    # =========================================================================
    # Image Upload Storage
    # =========================================================================

    def save_community_image(
        self,
        file_bytes: bytes,
        original_filename: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Saves an uploaded image for a community post securely."""
        if not file_bytes:
            return False, "Empty image file provided.", None

        # Max 5 MB limit for community images
        if len(file_bytes) > 5 * 1024 * 1024:
            return False, "Image file exceeds maximum 5MB size limit.", None

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return False, "Unsupported image type. Please upload a JPG, PNG, or WEBP image.", None

        safe_name = f"community_{uuid.uuid4().hex[:12]}{ext}"

        # Cloud storage via Supabase Storage if configured
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                sb_client = create_client(supabase_url, supabase_key)
                bucket_name = os.environ.get("SUPABASE_STORAGE_BUCKET", "community_images")
                content_type = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
                sb_client.storage.from_(bucket_name).upload(
                    path=safe_name,
                    file=file_bytes,
                    file_options={"content-type": content_type}
                )
                public_url = sb_client.storage.from_(bucket_name).get_public_url(safe_name)
                return True, "Image uploaded to Supabase Storage successfully.", public_url
            except Exception as sb_err:
                logger.warning(f"Supabase Storage upload failed, falling back to local: {sb_err}")

        # Local storage fallback
        target_path = os.path.join(COMMUNITY_UPLOADS_DIR, safe_name)
        try:
            os.makedirs(COMMUNITY_UPLOADS_DIR, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(file_bytes)
            relative_url = f"/community/images/{safe_name}"
            return True, "Image uploaded successfully.", relative_url
        except Exception as e:
            logger.error(f"Failed to save community image: {e}")
            return False, "Internal error saving uploaded image.", None


# Global singleton instance
_COMMUNITY_SERVICE: Optional[CommunityService] = None


def get_community_service(db_path: str = DEFAULT_DB_PATH) -> CommunityService:
    global _COMMUNITY_SERVICE
    if _COMMUNITY_SERVICE is None or (db_path and _COMMUNITY_SERVICE.db_path != db_path):
        _COMMUNITY_SERVICE = CommunityService(db_path=db_path)
    return _COMMUNITY_SERVICE


def set_community_service(service: Optional[CommunityService]) -> None:
    global _COMMUNITY_SERVICE
    _COMMUNITY_SERVICE = service

