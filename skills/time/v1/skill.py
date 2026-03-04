#!/usr/bin/env python3
"""
time skill - Pokazuje aktualną godzinę i datę
"""
from datetime import datetime
from typing import Dict, Any


def get_info() -> Dict[str, Any]:
    """Zwraca metadane skilla."""
    return {
        "name": "time",
        "version": "v1",
        "description": "Pokazuje aktualną godzinę, datę i czas",
        "author": "CoreSkill AI",
        "actions": ["current_time", "current_date", "current_datetime"],
        "parameters": {
            "format": {
                "type": "string",
                "description": "Format wyjścia",
                "default": "text",
                "enum": ["text", "json"]
            }
        }
    }


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Zwraca aktualną godzinę i datę.
    
    Args:
        params: {"format": "text"} lub {"format": "json"}
    
    Returns:
        {"success": True, "result": {"time": "...", "date": "..."}}
    """
    fmt = params.get("format", "text")
    
    try:
        now = datetime.now()
        
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d.%m.%Y")
        weekday = now.strftime("%A")
        
        # Polish weekdays
        weekdays_pl = {
            "Monday": "poniedziałek",
            "Tuesday": "wtorek",
            "Wednesday": "środa",
            "Thursday": "czwartek",
            "Friday": "piątek",
            "Saturday": "sobota",
            "Sunday": "niedziela"
        }
        weekday_pl = weekdays_pl.get(weekday, weekday)
        
        result = {
            "time": time_str,
            "date": date_str,
            "weekday": weekday_pl,
            "timestamp": now.isoformat()
        }
        
        if fmt == "json":
            return {
                "success": True,
                "result": result
            }
        else:
            # Human readable format in Polish
            message = f"🕐 Jest godzina {time_str}, {weekday_pl} {date_str}"
            return {
                "success": True,
                "result": result,
                "message": message
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Spróbuj ponownie"
        }


def health_check() -> Dict[str, Any]:
    """Sprawdza health skilla."""
    try:
        result = execute({"format": "json"})
        if result["success"]:
            return {
                "status": "ok",
                "message": "Time skill działa poprawnie"
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Unknown error")
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    print("Testowanie time skill...")
    result = execute({"format": "text"})
    print(f"Wynik: {result}")
