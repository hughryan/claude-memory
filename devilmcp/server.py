"""
DevilMCP Server - AI Memory System with Semantic Understanding

A smarter MCP server that provides:
1. Semantic memory storage and retrieval (TF-IDF, not just keywords)
2. Time-weighted recall (recent memories matter more)
3. Conflict detection (warns about contradicting decisions)
4. Rule-based decision trees for consistent AI behavior
5. Outcome tracking for continuous learning

Core Tools:
- remember: Store a decision, pattern, warning, or learning
- recall: Retrieve relevant memories for a topic (semantic search)
- add_rule: Add a decision tree node
- check_rules: Validate an action against rules
- record_outcome: Track whether a decision worked
- get_briefing: Get everything needed to start a session
"""

import sys
import logging
import atexit
from typing import Dict, List, Optional, Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: fastmcp not installed. Run: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

from .config import settings
from .database import DatabaseManager
from .memory import MemoryManager
from .rules import RulesEngine
from .models import Memory, Rule
from sqlalchemy import select, desc

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("DevilMCP")

# Initialize core modules
storage_path = settings.get_storage_path()
db_manager = DatabaseManager(storage_path)
memory_manager = MemoryManager(db_manager)
rules_engine = RulesEngine(db_manager)

logger.info(f"DevilMCP Server initialized (storage: {storage_path})")


# ============================================================================
# Tool 1: REMEMBER - Store a memory with conflict detection
# ============================================================================
@mcp.tool()
async def remember(
    category: str,
    content: str,
    rationale: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Store a decision, pattern, warning, or learning in long-term memory.

    NOW WITH CONFLICT DETECTION: If you're storing something that contradicts
    a previous decision or matches a known failure, you'll be warned.

    Use this immediately when:
    - Making an architectural decision
    - Establishing a pattern to follow
    - Encountering something that should be avoided (warning)
    - Learning something useful from experience

    Args:
        category: One of 'decision', 'pattern', 'warning', 'learning'
        content: The actual content to remember
        rationale: Why this is important / the reasoning behind it
        context: Structured context (files involved, alternatives considered, etc.)
        tags: Tags for easier retrieval (e.g., ['auth', 'security', 'api'])

    Returns:
        The created memory with its ID, plus any conflict warnings

    Examples:
        remember("decision", "Use JWT tokens instead of sessions",
                 rationale="Need stateless auth for horizontal scaling",
                 tags=["auth", "architecture"])

        remember("warning", "Don't use sync DB calls in request handlers",
                 rationale="Caused timeout issues in production",
                 context={"file": "api/handlers.py"})
    """
    await db_manager.init_db()
    return await memory_manager.remember(
        category=category,
        content=content,
        rationale=rationale,
        context=context,
        tags=tags
    )


# ============================================================================
# Tool 2: RECALL - Semantic memory retrieval with decay
# ============================================================================
@mcp.tool()
async def recall(
    topic: str,
    categories: Optional[List[str]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Recall memories relevant to a topic using SEMANTIC SIMILARITY.

    This uses TF-IDF matching, not just keywords - it understands related concepts.
    Results are weighted by:
    - Semantic relevance to your query
    - Recency (recent memories score higher)
    - Importance (warnings and failed decisions are boosted)

    Call this before working on any feature to get:
    - Past decisions about this area
    - Patterns that should be followed
    - Warnings about what to avoid (including failed approaches)
    - Learnings from previous work

    Args:
        topic: What you're looking for (e.g., "authentication", "database schema")
        categories: Limit to specific categories (default: all)
        limit: Max memories per category (default: 10)

    Returns:
        Categorized memories with relevance scores and failure warnings

    Examples:
        recall("authentication")  # Get all memories about auth
        recall("API endpoints", categories=["pattern", "warning"])
        recall("database")  # Before making DB changes
    """
    await db_manager.init_db()
    return await memory_manager.recall(
        topic=topic,
        categories=categories,
        limit=limit
    )


# ============================================================================
# Tool 3: ADD_RULE - Create a decision tree node
# ============================================================================
@mcp.tool()
async def add_rule(
    trigger: str,
    must_do: Optional[List[str]] = None,
    must_not: Optional[List[str]] = None,
    ask_first: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    priority: int = 0
) -> Dict[str, Any]:
    """
    Add a rule to the decision tree. Rules provide automatic guidance.

    Rules are matched SEMANTICALLY - you don't need exact keyword matches.
    "adding API endpoint" will match "creating a new REST route".

    When an action matches a rule's trigger, the AI gets guidance on:
    - What MUST be done
    - What MUST NOT be done
    - What questions to ask first
    - What warnings to consider

    Args:
        trigger: What activates this rule (natural language, e.g., "adding new API endpoint")
        must_do: Things that must be done when this rule applies
        must_not: Things that must be avoided
        ask_first: Questions to consider before proceeding
        warnings: Warnings from past experience
        priority: Higher priority rules are shown first (default: 0)

    Returns:
        The created rule

    Examples:
        add_rule(
            trigger="adding new API endpoint",
            must_do=["Add rate limiting", "Add to OpenAPI spec", "Write integration test"],
            must_not=["Use synchronous database calls"],
            ask_first=["Is this a breaking change?", "Does this need authentication?"]
        )

        add_rule(
            trigger="modifying database schema",
            must_do=["Create migration", "Test rollback", "Update seed data"],
            warnings=["Schema change on 2024-10-01 caused 2hr outage"],
            priority=10  # High priority
        )
    """
    await db_manager.init_db()
    return await rules_engine.add_rule(
        trigger=trigger,
        must_do=must_do,
        must_not=must_not,
        ask_first=ask_first,
        warnings=warnings,
        priority=priority
    )


# ============================================================================
# Tool 4: CHECK_RULES - Validate an action against rules
# ============================================================================
@mcp.tool()
async def check_rules(
    action: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Check if an action triggers any rules and get guidance.

    Uses SEMANTIC matching - "creating REST endpoint" will match rules about "adding API routes".

    Call this BEFORE taking any significant action to get:
    - Matching rules for this type of action
    - Combined must_do / must_not guidance
    - Relevant warnings
    - Questions to consider

    Args:
        action: Description of what you're about to do
        context: Optional context (files involved, etc.)

    Returns:
        Matching rules and combined guidance with severity indicator

    Examples:
        check_rules("adding a new REST endpoint for user profiles")
        check_rules("modifying the authentication middleware")
        check_rules("updating the database schema to add a new column")
    """
    await db_manager.init_db()
    return await rules_engine.check_rules(action=action, context=context)


# ============================================================================
# Tool 5: RECORD_OUTCOME - Track if a decision worked
# ============================================================================
@mcp.tool()
async def record_outcome(
    memory_id: int,
    outcome: str,
    worked: bool
) -> Dict[str, Any]:
    """
    Record the outcome of a decision to learn from it.

    IMPORTANT: Failed decisions become implicit warnings that get BOOSTED
    in future recalls. This is how the system learns.

    Use this after implementing a decision to track:
    - What actually happened
    - Whether it worked out

    Args:
        memory_id: The ID of the memory (returned from 'remember')
        outcome: Description of what happened
        worked: Did it work? True/False

    Returns:
        Updated memory, with suggestions if it failed

    Examples:
        record_outcome(42, "JWT auth works well, no session issues", worked=True)
        record_outcome(43, "Caching caused stale data bugs", worked=False)
    """
    await db_manager.init_db()
    return await memory_manager.record_outcome(
        memory_id=memory_id,
        outcome=outcome,
        worked=worked
    )


# ============================================================================
# Tool 6: GET_BRIEFING - Smart session start summary
# ============================================================================
@mcp.tool()
async def get_briefing(
    project_path: Optional[str] = None,
    focus_areas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get everything needed to start a session - call this FIRST.

    Returns:
    - Memory statistics and learning insights
    - Recent decisions (what changed lately)
    - Active warnings (what to watch out for)
    - High-priority rules (what to always check)
    - Failed approaches (what not to repeat)

    If you provide focus_areas, you'll also get relevant memories for those topics.

    Args:
        project_path: Optional project path (uses default if not specified)
        focus_areas: Optional list of topics to pre-fetch memories for

    Returns:
        Complete session briefing with actionable context

    Example:
        get_briefing()  # Basic briefing
        get_briefing(focus_areas=["authentication", "API"])  # With pre-loaded context
    """
    await db_manager.init_db()

    # Get statistics with learning insights
    stats = await memory_manager.get_statistics()

    async with db_manager.get_session() as session:
        # Get recent decisions (last 5)
        result = await session.execute(
            select(Memory)
            .where(Memory.category == 'decision')
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        recent_decisions = [
            {
                "id": m.id,
                "content": m.content,
                "worked": m.worked,
                "created_at": m.created_at.isoformat()
            }
            for m in result.scalars().all()
        ]

        # Get active warnings
        result = await session.execute(
            select(Memory)
            .where(Memory.category == 'warning')
            .order_by(Memory.created_at.desc())
            .limit(10)
        )
        active_warnings = [
            {"id": m.id, "content": m.content}
            for m in result.scalars().all()
        ]

        # Get FAILED decisions - these are critical
        result = await session.execute(
            select(Memory)
            .where(Memory.worked == False)  # noqa: E712
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        failed_approaches = [
            {
                "id": m.id,
                "content": m.content,
                "outcome": m.outcome,
                "category": m.category
            }
            for m in result.scalars().all()
        ]

        # Get high-priority rules
        result = await session.execute(
            select(Rule)
            .where(Rule.enabled == True)  # noqa: E712
            .order_by(Rule.priority.desc())
            .limit(5)
        )
        top_rules = [
            {
                "id": r.id,
                "trigger": r.trigger,
                "priority": r.priority,
                "has_warnings": len(r.warnings) > 0
            }
            for r in result.scalars().all()
        ]

    # Pre-fetch memories for focus areas if specified
    focus_memories = {}
    if focus_areas:
        for area in focus_areas[:3]:  # Limit to 3 areas
            memories = await memory_manager.recall(area, limit=5)
            focus_memories[area] = {
                "found": memories.get("found", 0),
                "summary": memories.get("summary"),
                "has_warnings": len(memories.get("warnings", [])) > 0,
                "has_failed": any(
                    m.get("worked") is False
                    for cat in ["decisions", "patterns", "learnings"]
                    for m in memories.get(cat, [])
                )
            }

    # Build actionable message
    message_parts = [f"DevilMCP ready. {stats['total_memories']} memories stored."]

    if failed_approaches:
        message_parts.append(f"⚠️ {len(failed_approaches)} failed approaches to avoid!")

    if active_warnings:
        message_parts.append(f"{len(active_warnings)} active warnings.")

    if stats.get("learning_insights", {}).get("suggestion"):
        message_parts.append(stats["learning_insights"]["suggestion"])

    return {
        "status": "ready",
        "statistics": stats,
        "recent_decisions": recent_decisions,
        "active_warnings": active_warnings,
        "failed_approaches": failed_approaches,
        "top_rules": top_rules,
        "focus_areas": focus_memories if focus_memories else None,
        "message": " ".join(message_parts)
    }


# ============================================================================
# Tool 7: SEARCH - Full text search across memories
# ============================================================================
@mcp.tool()
async def search_memories(
    query: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search across all memories with semantic similarity.

    Use this when you need to find specific memories by content.
    Uses TF-IDF matching for better results than exact text search.

    Args:
        query: Search text
        limit: Maximum results (default: 20)

    Returns:
        Matching memories ranked by relevance
    """
    await db_manager.init_db()
    return await memory_manager.search(query=query, limit=limit)


# ============================================================================
# Tool 8: LIST_RULES - See all configured rules
# ============================================================================
@mcp.tool()
async def list_rules(
    enabled_only: bool = True,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List all configured rules.

    Args:
        enabled_only: Only show enabled rules (default: True)
        limit: Maximum results (default: 50)

    Returns:
        List of rules with their guidance
    """
    await db_manager.init_db()
    return await rules_engine.list_rules(enabled_only=enabled_only, limit=limit)


# ============================================================================
# Tool 9: UPDATE_RULE - Modify existing rules
# ============================================================================
@mcp.tool()
async def update_rule(
    rule_id: int,
    must_do: Optional[List[str]] = None,
    must_not: Optional[List[str]] = None,
    ask_first: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    priority: Optional[int] = None,
    enabled: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing rule.

    Args:
        rule_id: ID of the rule to update
        must_do: New must_do list (replaces existing)
        must_not: New must_not list (replaces existing)
        ask_first: New ask_first list (replaces existing)
        warnings: New warnings list (replaces existing)
        priority: New priority
        enabled: Enable/disable rule

    Returns:
        Updated rule or error
    """
    await db_manager.init_db()
    return await rules_engine.update_rule(
        rule_id=rule_id,
        must_do=must_do,
        must_not=must_not,
        ask_first=ask_first,
        warnings=warnings,
        priority=priority,
        enabled=enabled
    )


# ============================================================================
# Tool 10: FIND_RELATED - Discover connected memories
# ============================================================================
@mcp.tool()
async def find_related(
    memory_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find memories related to a specific memory.

    Useful for exploring connected decisions and understanding context.
    Uses semantic similarity to find related content.

    Args:
        memory_id: ID of the memory to find related content for
        limit: Maximum related memories to return (default: 5)

    Returns:
        List of related memories with similarity scores

    Example:
        # After seeing a decision about auth, find related patterns/warnings
        find_related(42)
    """
    await db_manager.init_db()
    return await memory_manager.find_related(memory_id=memory_id, limit=limit)


# ============================================================================
# Tool 11: CONTEXT_CHECK - Quick relevance check for current work
# ============================================================================
@mcp.tool()
async def context_check(
    description: str
) -> Dict[str, Any]:
    """
    Quick check for any relevant memories and rules for what you're about to do.

    Combines recall and check_rules in one call. Use this as a fast
    pre-flight check before making changes.

    Args:
        description: Brief description of what you're working on

    Returns:
        Combined results: relevant memories, matching rules, and any warnings

    Example:
        context_check("modifying the user authentication flow")
    """
    await db_manager.init_db()

    # Get relevant memories
    memories = await memory_manager.recall(description, limit=5)

    # Check rules
    rules = await rules_engine.check_rules(description)

    # Collect all warnings
    warnings = []

    # From memories
    for cat in ['warnings', 'decisions', 'patterns', 'learnings']:
        for mem in memories.get(cat, []):
            if mem.get('worked') is False:
                warnings.append({
                    "source": "failed_decision",
                    "content": mem['content'],
                    "outcome": mem.get('outcome')
                })
            elif cat == 'warnings':
                warnings.append({
                    "source": "warning",
                    "content": mem['content']
                })

    # From rules
    if rules.get('guidance', {}).get('warnings'):
        for w in rules['guidance']['warnings']:
            warnings.append({
                "source": "rule",
                "content": w
            })

    has_concerns = len(warnings) > 0 or rules.get('has_blockers', False)

    return {
        "description": description,
        "has_concerns": has_concerns,
        "memories_found": memories.get('found', 0),
        "rules_matched": rules.get('matched_rules', 0),
        "warnings": warnings,
        "must_do": rules.get('guidance', {}).get('must_do', []),
        "must_not": rules.get('guidance', {}).get('must_not', []),
        "ask_first": rules.get('guidance', {}).get('ask_first', []),
        "message": (
            "⚠️ Review warnings before proceeding" if has_concerns else
            "✓ No concerns found, but always use good judgment"
        )
    }


# ============================================================================
# Cleanup
# ============================================================================
def cleanup():
    """Cleanup on exit."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(db_manager.close())
        else:
            loop.run_until_complete(db_manager.close())
    except Exception:
        pass


atexit.register(cleanup)


# ============================================================================
# Entry point
# ============================================================================
def main():
    """Run the MCP server."""
    import asyncio

    logger.info("Starting DevilMCP server...")
    logger.info(f"Storage: {storage_path}")

    # Initialize database
    try:
        asyncio.run(db_manager.init_db())
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Run MCP server
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
