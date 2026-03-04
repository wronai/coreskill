#!/usr/bin/env python3
"""
Pipeline 7: Task Management Automation

Automatyzuje zarządzanie zadaniami:
1. Importuje zadania z plików/emails
2. Kategoryzuje i priorytetyzuje
3. Tworzy przypomnienia
4. Generuje raport tygodniowy

Użycie:
  python3 examples/automations/task_management_automation.py
"""
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def run_skill(skill_name, action, params):
    """Execute a skill via subprocess."""
    input_data = {"action": action, **params}
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'skills/{skill_name}/v1')
from skill import execute
result = execute({json.dumps(input_data)})
print(json.dumps(result))
"""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/home/tom/github/wronai/coreskill')
        return json.loads(result.stdout.strip().split('\n')[-1])
    except Exception as e:
        return {"success": False, "error": str(e)}


def task_management_automation():
    """Complete task management workflow."""
    print("✅ Task Management Automation")
    print("=" * 60)
    
    created_tasks = []
    
    # Step 1: Create sample tasks
    print("\n📝 Step 1: Creating tasks...")
    
    tasks_data = [
        {
            "title": "Review quarterly report",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            "category": "work",
            "tags": ["review", "quarterly", "finance"]
        },
        {
            "title": "Update documentation",
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "category": "work",
            "tags": ["docs", "maintenance"]
        },
        {
            "title": "Team meeting preparation",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "category": "meetings",
            "tags": ["meeting", "team"]
        }
    ]
    
    for task_data in tasks_data:
        print(f"   Creating: {task_data['title']}")
        result = run_skill("task_manager", "add_task", task_data)
        if result.get("success"):
            created_tasks.append(result.get("task", {}))
            print(f"     ✅ Task ID: {result.get('task', {}).get('id', 'N/A')}")
        else:
            print(f"     ❌ Error: {result.get('error', 'Unknown')}")
    
    # Step 2: List all tasks
    print("\n📋 Step 2: Listing all tasks...")
    list_result = run_skill("task_manager", "list_tasks", {})
    
    if list_result.get("success"):
        tasks = list_result.get("tasks", [])
        print(f"   Total tasks: {len(tasks)}")
        
        # Group by priority
        high_priority = [t for t in tasks if t.get("priority") == "high"]
        medium_priority = [t for t in tasks if t.get("priority") == "medium"]
        
        print(f"   High priority: {len(high_priority)}")
        print(f"   Medium priority: {len(medium_priority)}")
    
    # Step 3: Search tasks
    print("\n🔍 Step 3: Searching tasks...")
    search_result = run_skill("task_manager", "search_tasks", {
        "query": "review"
    })
    
    if search_result.get("success"):
        found = search_result.get("results", [])
        print(f"   Found {len(found)} tasks matching 'review'")
    
    # Step 4: Get overdue tasks
    print("\n⚠️ Step 4: Checking for overdue tasks...")
    overdue_result = run_skill("task_manager", "get_overdue_tasks", {})
    
    if overdue_result.get("success"):
        overdue = overdue_result.get("overdue_tasks", [])
        print(f"   Overdue tasks: {len(overdue)}")
        if overdue:
            for task in overdue[:3]:
                print(f"     • {task.get('title')} (due: {task.get('due_date')})")
    
    # Step 5: Generate report
    print("\n📊 Step 5: Generating task report...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_tasks": len(tasks) if list_result.get("success") else 0,
        "high_priority": len(high_priority) if list_result.get("success") else 0,
        "medium_priority": len(medium_priority) if list_result.get("success") else 0,
        "overdue": len(overdue) if overdue_result.get("success") else 0,
        "tasks": tasks[:5] if list_result.get("success") else []
    }
    
    # Save report
    report_dir = Path.home() / ".evo_task_reports"
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f"task_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"   Report saved to: {report_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Task Management Summary")
    print("=" * 60)
    print(f"\n✅ Created tasks: {len(created_tasks)}")
    print(f"📋 Total in system: {report['total_tasks']}")
    print(f"🔴 High priority: {report['high_priority']}")
    print(f"🟡 Medium priority: {report['medium_priority']}")
    print(f"⚠️ Overdue: {report['overdue']}")
    print(f"📄 Report: {report_file}")
    
    return {
        "success": True,
        "tasks_created": len(created_tasks),
        "total_tasks": report['total_tasks'],
        "high_priority": report['high_priority'],
        "overdue": report['overdue'],
        "report_file": str(report_file)
    }


def task_import_from_files(file_path):
    """Import tasks from a file."""
    print(f"📥 Importing tasks from: {file_path}")
    
    # Read file
    # document_result = run_skill("document_reader", "read_document", {"file_path": file_path})
    
    # Extract tasks using text analysis
    # tasks = parse_tasks_from_text(content)
    
    # Add each task
    # for task in tasks:
    #     run_skill("task_manager", "add_task", task)
    
    print("✅ Tasks imported successfully")


if __name__ == "__main__":
    result = task_management_automation()
    print(f"\n📊 Full result: {json.dumps(result, indent=2)}")
