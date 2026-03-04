#!/usr/bin/env python3
"""
notes skill - Personal note taking with tags, search, and organization.
Uses JSON file storage in ~/.evo_notes/
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
import uuid


def get_info():
    return {
        "name": "notes",
        "version": "v1",
        "description": "Personal notes with tags, search, and organization. Stored in ~/.evo_notes/",
        "capabilities": ["notes", "organization", "search", "tags"],
        "actions": ["add", "list", "search", "get", "delete", "update", "tag"]
    }


def health_check():
    try:
        notes_dir = Path.home() / ".evo_notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


class NotesSkill:
    """Personal note management with tags and search."""
    
    def __init__(self):
        self.notes_dir = Path.home() / ".evo_notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.notes_dir / "notes.json"
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure notes storage file exists."""
        if not self.notes_file.exists():
            self._save_notes({})
    
    def _load_notes(self):
        """Load all notes from storage."""
        try:
            with open(self.notes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_notes(self, notes):
        """Save all notes to storage."""
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump(notes, f, indent=2, ensure_ascii=False, default=str)
    
    def add(self, title, content, tags=None):
        """Add a new note."""
        try:
            notes = self._load_notes()
            
            note_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now(timezone.utc).isoformat()
            
            note = {
                "id": note_id,
                "title": title,
                "content": content,
                "tags": tags or [],
                "created": timestamp,
                "updated": timestamp
            }
            
            notes[note_id] = note
            self._save_notes(notes)
            
            return {
                "success": True,
                "action": "add",
                "note_id": note_id,
                "title": title,
                "tags_count": len(note["tags"])
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_notes(self, tag=None, limit=50):
        """List all notes, optionally filtered by tag."""
        try:
            notes = self._load_notes()
            
            result = []
            for note_id, note in notes.items():
                if tag and tag not in note.get("tags", []):
                    continue
                result.append({
                    "id": note_id,
                    "title": note.get("title", "Untitled"),
                    "tags": note.get("tags", []),
                    "created": note.get("created", ""),
                    "updated": note.get("updated", ""),
                    "preview": note.get("content", "")[:100]
                })
            
            # Sort by updated date (newest first)
            result.sort(key=lambda x: x.get("updated", ""), reverse=True)
            
            return {
                "success": True,
                "count": len(result),
                "notes": result[:limit]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get(self, note_id):
        """Get a single note by ID."""
        try:
            notes = self._load_notes()
            
            if note_id not in notes:
                return {"success": False, "error": f"Note not found: {note_id}"}
            
            note = notes[note_id]
            return {
                "success": True,
                "note": note
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search(self, query, search_content=True):
        """Search notes by title and optionally content."""
        try:
            notes = self._load_notes()
            query_lower = query.lower()
            
            matches = []
            for note_id, note in notes.items():
                title = note.get("title", "").lower()
                content = note.get("content", "").lower() if search_content else ""
                tags = [t.lower() for t in note.get("tags", [])]
                
                # Check title
                if query_lower in title:
                    matches.append(note)
                    continue
                
                # Check content
                if search_content and query_lower in content:
                    matches.append(note)
                    continue
                
                # Check tags
                if any(query_lower in tag for tag in tags):
                    matches.append(note)
                    continue
            
            # Sort by updated date
            matches.sort(key=lambda x: x.get("updated", ""), reverse=True)
            
            return {
                "success": True,
                "query": query,
                "matches_count": len(matches),
                "notes": [{"id": n["id"], "title": n["title"], "tags": n.get("tags", [])} for n in matches[:20]]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update(self, note_id, title=None, content=None, tags=None):
        """Update an existing note."""
        try:
            notes = self._load_notes()
            
            if note_id not in notes:
                return {"success": False, "error": f"Note not found: {note_id}"}
            
            note = notes[note_id]
            
            if title is not None:
                note["title"] = title
            if content is not None:
                note["content"] = content
            if tags is not None:
                note["tags"] = tags
            
            note["updated"] = datetime.now(timezone.utc).isoformat()
            
            self._save_notes(notes)
            
            return {
                "success": True,
                "action": "update",
                "note_id": note_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete(self, note_id):
        """Delete a note."""
        try:
            notes = self._load_notes()
            
            if note_id not in notes:
                return {"success": False, "error": f"Note not found: {note_id}"}
            
            del notes[note_id]
            self._save_notes(notes)
            
            return {
                "success": True,
                "action": "delete",
                "note_id": note_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_tag(self, note_id, tag):
        """Add a tag to a note."""
        try:
            notes = self._load_notes()
            
            if note_id not in notes:
                return {"success": False, "error": f"Note not found: {note_id}"}
            
            note = notes[note_id]
            tags = note.get("tags", [])
            
            if tag not in tags:
                tags.append(tag)
                note["tags"] = tags
                note["updated"] = datetime.now(timezone.utc).isoformat()
                self._save_notes(notes)
            
            return {
                "success": True,
                "action": "add_tag",
                "note_id": note_id,
                "tag": tag
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_tags(self):
        """List all unique tags."""
        try:
            notes = self._load_notes()
            
            all_tags = set()
            for note in notes.values():
                all_tags.update(note.get("tags", []))
            
            return {
                "success": True,
                "tags": sorted(list(all_tags)),
                "count": len(all_tags)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "list")
        
        if action == "add":
            return self.add(
                input_data.get("title", "Untitled"),
                input_data.get("content", ""),
                input_data.get("tags", [])
            )
        elif action == "list":
            return self.list_notes(
                input_data.get("tag"),
                input_data.get("limit", 50)
            )
        elif action == "search":
            return self.search(
                input_data.get("query", ""),
                input_data.get("search_content", True)
            )
        elif action == "get":
            return self.get(input_data.get("note_id", ""))
        elif action == "update":
            return self.update(
                input_data.get("note_id", ""),
                input_data.get("title"),
                input_data.get("content"),
                input_data.get("tags")
            )
        elif action == "delete":
            return self.delete(input_data.get("note_id", ""))
        elif action == "add_tag":
            return self.add_tag(
                input_data.get("note_id", ""),
                input_data.get("tag", "")
            )
        elif action == "list_tags":
            return self.list_tags()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return NotesSkill().execute(input_data)


if __name__ == "__main__":
    skill = NotesSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    
    # Test add
    print("\nAdding test note:")
    result = skill.add("Meeting Notes", "Discussed Q4 goals and budget", ["work", "meeting"])
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        note_id = result["note_id"]
        
        # Test list
        print("\nListing notes:")
        print(json.dumps(skill.list_notes(), indent=2)[:500] + "...")
        
        # Test search
        print("\nSearching for 'meeting':")
        print(json.dumps(skill.search("meeting"), indent=2))
