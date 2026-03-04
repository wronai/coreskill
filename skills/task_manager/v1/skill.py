#!/usr/bin/env python3
"""
task_manager skill - Task and reminder management for office workers.
Uses JSON file storage in ~/.evo_tasks/
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid


def get_info():
    return {
        "name": "task_manager",
        "version": "v1",
        "description": "Task and reminder management with priorities, due dates, and categories. Stored in ~/.evo_tasks/",
        "capabilities": ["tasks", "reminders", "management", "organization"],
        "actions": ["add", "list", "complete", "delete", "update", "due_soon", "overdue", "search", "stats"]
    }


def health_check():
    try:
        tasks_dir = Path.home() / ".evo_tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


class TaskManagerSkill:
    """Task and reminder management."""
    
    def __init__(self):
        self.tasks_dir = Path.home() / ".evo_tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.tasks_dir / "tasks.json"
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure tasks storage file exists."""
        if not self.tasks_file.exists():
            self._save_tasks({})
    
    def _load_tasks(self):
        """Load all tasks from storage."""
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_tasks(self, tasks):
        """Save all tasks to storage."""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False, default=str)
    
    def _parse_due_date(self, due_str):
        """Parse due date string to ISO format."""
        if not due_str:
            return None
        
        # Try various formats
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%H:%M",  # Today at specific time
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(due_str, fmt)
                if fmt == "%H:%M":
                    # Today at specified time
                    now = datetime.now()
                    dt = dt.replace(year=now.year, month=now.month, day=now.day)
                return dt.replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                continue
        
        # Try relative dates
        relative_patterns = [
            (r'in (\d+) minutes?', lambda m: datetime.now() + timedelta(minutes=int(m.group(1)))),
            (r'in (\d+) hours?', lambda m: datetime.now() + timedelta(hours=int(m.group(1)))),
            (r'in (\d+) days?', lambda m: datetime.now() + timedelta(days=int(m.group(1)))),
            (r'tomorrow', lambda m: datetime.now() + timedelta(days=1)),
            (r'today', lambda m: datetime.now()),
            (r'next week', lambda m: datetime.now() + timedelta(weeks=1)),
        ]
        
        due_lower = due_str.lower()
        for pattern, func in relative_patterns:
            match = re.match(pattern, due_lower)
            if match:
                dt = func(match)
                return dt.replace(tzinfo=timezone.utc).isoformat()
        
        return None
    
    def add(self, title, description="", due=None, priority="normal", category="general", tags=None):
        """Add a new task."""
        try:
            tasks = self._load_tasks()
            
            task_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Parse due date
            due_parsed = self._parse_due_date(due) if due else None
            
            task = {
                "id": task_id,
                "title": title,
                "description": description,
                "due": due_parsed,
                "priority": priority.lower() if priority in ["low", "normal", "high", "urgent"] else "normal",
                "category": category,
                "tags": tags or [],
                "created": timestamp,
                "updated": timestamp,
                "completed": False,
                "completed_at": None
            }
            
            tasks[task_id] = task
            self._save_tasks(tasks)
            
            return {
                "success": True,
                "action": "add",
                "task_id": task_id,
                "title": title,
                "due": due_parsed,
                "priority": task["priority"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_tasks(self, status="pending", category=None, priority=None, limit=50):
        """List tasks with filters."""
        try:
            tasks = self._load_tasks()
            
            filtered = []
            for task_id, task in tasks.items():
                # Filter by status
                if status == "pending" and task.get("completed", False):
                    continue
                if status == "completed" and not task.get("completed", False):
                    continue
                
                # Filter by category
                if category and task.get("category") != category:
                    continue
                
                # Filter by priority
                if priority and task.get("priority") != priority:
                    continue
                
                filtered.append({
                    "id": task_id,
                    "title": task.get("title", "Untitled"),
                    "due": task.get("due"),
                    "priority": task.get("priority", "normal"),
                    "category": task.get("category", "general"),
                    "completed": task.get("completed", False),
                    "tags": task.get("tags", [])
                })
            
            # Sort by due date (if exists), then priority
            priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
            filtered.sort(key=lambda x: (
                x.get("due") or "9999-12-31",  # No due = last
                priority_order.get(x.get("priority", "normal"), 2)
            ))
            
            return {
                "success": True,
                "count": len(filtered),
                "tasks": filtered[:limit]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def complete(self, task_id):
        """Mark task as completed."""
        try:
            tasks = self._load_tasks()
            
            if task_id not in tasks:
                return {"success": False, "error": f"Task not found: {task_id}"}
            
            tasks[task_id]["completed"] = True
            tasks[task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            tasks[task_id]["updated"] = datetime.now(timezone.utc).isoformat()
            
            self._save_tasks(tasks)
            
            return {
                "success": True,
                "action": "complete",
                "task_id": task_id,
                "title": tasks[task_id].get("title")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete(self, task_id):
        """Delete a task."""
        try:
            tasks = self._load_tasks()
            
            if task_id not in tasks:
                return {"success": False, "error": f"Task not found: {task_id}"}
            
            deleted_title = tasks[task_id].get("title")
            del tasks[task_id]
            self._save_tasks(tasks)
            
            return {
                "success": True,
                "action": "delete",
                "task_id": task_id,
                "title": deleted_title
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update(self, task_id, title=None, description=None, due=None, priority=None, category=None):
        """Update task fields."""
        try:
            tasks = self._load_tasks()
            
            if task_id not in tasks:
                return {"success": False, "error": f"Task not found: {task_id}"}
            
            task = tasks[task_id]
            
            if title is not None:
                task["title"] = title
            if description is not None:
                task["description"] = description
            if due is not None:
                task["due"] = self._parse_due_date(due)
            if priority is not None:
                task["priority"] = priority
            if category is not None:
                task["category"] = category
            
            task["updated"] = datetime.now(timezone.utc).isoformat()
            
            self._save_tasks(tasks)
            
            return {
                "success": True,
                "action": "update",
                "task_id": task_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def due_soon(self, hours=24):
        """Get tasks due within specified hours."""
        try:
            tasks = self._load_tasks()
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=hours)
            
            due_tasks = []
            for task_id, task in tasks.items():
                if task.get("completed", False):
                    continue
                
                due_str = task.get("due")
                if due_str:
                    try:
                        due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                        if now <= due_dt <= cutoff:
                            due_tasks.append({
                                "id": task_id,
                                "title": task.get("title"),
                                "due": due_str,
                                "priority": task.get("priority", "normal"),
                                "hours_remaining": round((due_dt - now).total_seconds() / 3600, 1)
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Sort by due date
            due_tasks.sort(key=lambda x: x.get("due", ""))
            
            return {
                "success": True,
                "hours": hours,
                "count": len(due_tasks),
                "tasks": due_tasks
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def overdue(self):
        """Get overdue tasks."""
        try:
            tasks = self._load_tasks()
            now = datetime.now(timezone.utc)
            
            overdue_tasks = []
            for task_id, task in tasks.items():
                if task.get("completed", False):
                    continue
                
                due_str = task.get("due")
                if due_str:
                    try:
                        due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                        if due_dt < now:
                            overdue_tasks.append({
                                "id": task_id,
                                "title": task.get("title"),
                                "due": due_str,
                                "priority": task.get("priority", "normal"),
                                "hours_overdue": round((now - due_dt).total_seconds() / 3600, 1)
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Sort by most overdue
            overdue_tasks.sort(key=lambda x: x.get("due", ""))
            
            return {
                "success": True,
                "count": len(overdue_tasks),
                "tasks": overdue_tasks
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search(self, query):
        """Search tasks by title or description."""
        try:
            tasks = self._load_tasks()
            query_lower = query.lower()
            
            matches = []
            for task_id, task in tasks.items():
                title = task.get("title", "").lower()
                description = task.get("description", "").lower()
                
                if query_lower in title or query_lower in description:
                    matches.append({
                        "id": task_id,
                        "title": task.get("title"),
                        "completed": task.get("completed", False),
                        "due": task.get("due"),
                        "priority": task.get("priority", "normal")
                    })
            
            return {
                "success": True,
                "query": query,
                "matches_count": len(matches),
                "tasks": matches
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stats(self):
        """Get task statistics."""
        try:
            tasks = self._load_tasks()
            
            total = len(tasks)
            completed = sum(1 for t in tasks.values() if t.get("completed", False))
            pending = total - completed
            
            # By priority
            by_priority = {}
            by_category = {}
            
            for task in tasks.values():
                if not task.get("completed", False):
                    prio = task.get("priority", "normal")
                    by_priority[prio] = by_priority.get(prio, 0) + 1
                    
                    cat = task.get("category", "general")
                    by_category[cat] = by_category.get(cat, 0) + 1
            
            # Overdue count
            overdue_count = self.overdue().get("count", 0)
            
            return {
                "success": True,
                "total": total,
                "completed": completed,
                "pending": pending,
                "overdue": overdue_count,
                "by_priority": by_priority,
                "by_category": by_category
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "list")
        
        if action == "add":
            return self.add(
                input_data.get("title", "Untitled"),
                input_data.get("description", ""),
                input_data.get("due"),
                input_data.get("priority", "normal"),
                input_data.get("category", "general"),
                input_data.get("tags", [])
            )
        elif action == "list":
            return self.list_tasks(
                input_data.get("status", "pending"),
                input_data.get("category"),
                input_data.get("priority"),
                input_data.get("limit", 50)
            )
        elif action == "complete":
            return self.complete(input_data.get("task_id", ""))
        elif action == "delete":
            return self.delete(input_data.get("task_id", ""))
        elif action == "update":
            return self.update(
                input_data.get("task_id", ""),
                input_data.get("title"),
                input_data.get("description"),
                input_data.get("due"),
                input_data.get("priority"),
                input_data.get("category")
            )
        elif action == "due_soon":
            return self.due_soon(input_data.get("hours", 24))
        elif action == "overdue":
            return self.overdue()
        elif action == "search":
            return self.search(input_data.get("query", ""))
        elif action == "stats":
            return self.stats()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return TaskManagerSkill().execute(input_data)


if __name__ == "__main__":
    skill = TaskManagerSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    
    # Test add
    print("\nAdding test tasks:")
    result1 = skill.add("Prepare presentation", "Q4 review slides", "tomorrow", "high", "work")
    print(json.dumps(result1, indent=2))
    
    result2 = skill.add("Buy groceries", "Milk, bread, eggs", "in 2 hours", "normal", "personal")
    print(json.dumps(result2, indent=2))
    
    if result1.get("success"):
        # Test list
        print("\nListing pending tasks:")
        print(json.dumps(skill.list_tasks(), indent=2)[:500] + "...")
        
        # Test stats
        print("\nTask stats:")
        print(json.dumps(skill.stats(), indent=2))
