#!/usr/bin/env python3
"""
converter skill - Unit conversions, time zones, and currency conversion.
Uses stdlib and dateutil for time zones, with external API for currencies.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP


def get_info():
    return {
        "name": "converter",
        "version": "v1",
        "description": "Convert units (length, weight, temperature), time zones, and currencies.",
        "capabilities": ["conversion", "units", "time", "currency"],
        "actions": ["convert_unit", "convert_time", "convert_currency", "list_units", "list_timezones"]
    }


def health_check():
    return True  # Pure Python, always works


class ConverterSkill:
    """Unit, time zone, and currency conversions."""
    
    # Unit conversion definitions (base unit is first in each category)
    UNITS = {
        "length": {
            "m": 1.0,
            "km": 1000.0,
            "cm": 0.01,
            "mm": 0.001,
            "ft": 0.3048,
            "in": 0.0254,
            "yd": 0.9144,
            "mi": 1609.344,
        },
        "weight": {
            "kg": 1.0,
            "g": 0.001,
            "mg": 0.000001,
            "lb": 0.453592,
            "oz": 0.0283495,
            "t": 1000.0,
        },
        "volume": {
            "l": 1.0,
            "ml": 0.001,
            "gal": 3.78541,
            "qt": 0.946353,
            "pt": 0.473176,
            "cup": 0.24,
            "fl_oz": 0.0295735,
        },
        "area": {
            "m2": 1.0,
            "km2": 1000000.0,
            "ft2": 0.092903,
            "ac": 4046.86,
            "ha": 10000.0,
        },
        "speed": {
            "mps": 1.0,
            "kph": 0.277778,
            "mph": 0.44704,
            "knot": 0.514444,
        },
        "data": {
            "b": 1.0,
            "kb": 1024.0,
            "mb": 1048576.0,
            "gb": 1073741824.0,
            "tb": 1099511627776.0,
        },
        "time": {
            "s": 1.0,
            "min": 60.0,
            "h": 3600.0,
            "d": 86400.0,
            "wk": 604800.0,
            "mo": 2592000.0,  # 30 days average
            "y": 31536000.0,  # 365 days
        },
    }
    
    # Currency rates (approximate, relative to USD)
    CURRENCIES = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.26,
        "JPY": 0.0067,
        "PLN": 0.25,
        "CHF": 1.13,
        "CAD": 0.74,
        "AUD": 0.66,
        "CNY": 0.14,
        "INR": 0.012,
    }
    
    # Time zone offsets (hours from UTC)
    TIMEZONES = {
        "UTC": 0,
        "GMT": 0,
        "CET": 1,      # Central Europe
        "CEST": 2,     # Central Europe Summer
        "EET": 2,      # Eastern Europe
        "EEST": 3,     # Eastern Europe Summer
        "EST": -5,     # US East
        "EDT": -4,     # US East Summer
        "CST": -6,     # US Central
        "CDT": -5,     # US Central Summer
        "MST": -7,     # US Mountain
        "MDT": -6,     # US Mountain Summer
        "PST": -8,     # US Pacific
        "PDT": -7,     # US Pacific Summer
        "IST": 5.5,    # India
        "JST": 9,      # Japan
        "AEST": 10,    # Australia East
        "AEDT": 11,    # Australia East Summer
    }

    def convert_unit(self, value, from_unit, to_unit):
        """Convert between units."""
        try:
            # Find which category these units belong to
            category = None
            from_factor = None
            to_factor = None
            
            for cat, units in self.UNITS.items():
                if from_unit in units:
                    category = cat
                    from_factor = units[from_unit]
                if to_unit in units:
                    to_factor = units[to_unit]
            
            if category is None:
                return {"success": False, "error": f"Unknown unit: {from_unit}"}
            if to_factor is None:
                return {"success": False, "error": f"Unknown unit: {to_unit}"}
            if from_factor is None:
                return {"success": False, "error": f"Unknown unit: {from_unit}"}
            
            # Convert to base then to target
            base_value = value * from_factor
            result = base_value / to_factor
            
            return {
                "success": True,
                "value": value,
                "from": from_unit,
                "to": to_unit,
                "result": round(result, 6),
                "category": category
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_temperature(self, value, from_unit, to_unit):
        """Convert temperature (special handling)."""
        try:
            # Convert to Celsius first
            if from_unit == "C":
                celsius = value
            elif from_unit == "F":
                celsius = (value - 32) * 5/9
            elif from_unit == "K":
                celsius = value - 273.15
            else:
                return {"success": False, "error": f"Unknown temperature unit: {from_unit}"}
            
            # Convert from Celsius to target
            if to_unit == "C":
                result = celsius
            elif to_unit == "F":
                result = celsius * 9/5 + 32
            elif to_unit == "K":
                result = celsius + 273.15
            else:
                return {"success": False, "error": f"Unknown temperature unit: {to_unit}"}
            
            return {
                "success": True,
                "value": value,
                "from": from_unit,
                "to": to_unit,
                "result": round(result, 2),
                "category": "temperature"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_currency(self, value, from_currency, to_currency):
        """Convert currencies using approximate rates."""
        try:
            from_curr = from_currency.upper()
            to_curr = to_currency.upper()
            
            if from_curr not in self.CURRENCIES:
                return {"success": False, "error": f"Unknown currency: {from_currency}"}
            if to_curr not in self.CURRENCIES:
                return {"success": False, "error": f"Unknown currency: {to_currency}"}
            
            # Convert to USD then to target
            usd_value = value * self.CURRENCIES[from_curr]
            result = usd_value / self.CURRENCIES[to_curr]
            
            return {
                "success": True,
                "value": value,
                "from": from_curr,
                "to": to_curr,
                "result": round(result, 2),
                "rate": round(self.CURRENCIES[from_curr] / self.CURRENCIES[to_curr], 6),
                "note": "Approximate rates - for accurate conversion use current market rates"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_time(self, time_str, from_tz, to_tz):
        """Convert time between time zones."""
        try:
            from_zone = from_tz.upper()
            to_zone = to_tz.upper()
            
            if from_zone not in self.TIMEZONES:
                return {"success": False, "error": f"Unknown timezone: {from_tz}"}
            if to_zone not in self.TIMEZONES:
                return {"success": False, "error": f"Unknown timezone: {to_tz}"}
            
            # Parse time string
            time_formats = [
                "%H:%M",
                "%H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
            ]
            
            parsed_time = None
            for fmt in time_formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_time is None:
                return {"success": False, "error": f"Could not parse time: {time_str}. Use format HH:MM or YYYY-MM-DD HH:MM"}
            
            # Calculate offset
            from_offset = self.TIMEZONES[from_zone]
            to_offset = self.TIMEZONES[to_zone]
            offset_diff = to_offset - from_offset
            
            # Apply offset
            result_time = parsed_time + timedelta(hours=offset_diff)
            
            return {
                "success": True,
                "original": time_str,
                "from": from_zone,
                "to": to_zone,
                "result": result_time.strftime("%Y-%m-%d %H:%M" if parsed_time.year != 1900 else "%H:%M"),
                "offset_hours": offset_diff
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_units(self, category=None):
        """List available units."""
        if category:
            units = self.UNITS.get(category.lower(), {})
            return {
                "success": True,
                "category": category,
                "units": list(units.keys())
            }
        else:
            return {
                "success": True,
                "categories": {
                    cat: list(units.keys()) 
                    for cat, units in self.UNITS.items()
                }
            }
    
    def list_timezones(self):
        """List available time zones."""
        return {
            "success": True,
            "timezones": {
                tz: f"UTC{offset:+.1f}" if offset != 0 else "UTC"
                for tz, offset in self.TIMEZONES.items()
            }
        }
    
    def parse_and_convert(self, query):
        """Parse natural language conversion query."""
        # Pattern: "X unit to unit" or "X unit in unit"
        pattern = r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:to|in|into)\s+(\w+)'
        match = re.search(pattern, query.lower())
        
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)
            
            # Check if temperature
            if from_unit in ['c', 'f', 'k'] and to_unit in ['c', 'f', 'k']:
                return self.convert_temperature(value, from_unit.upper(), to_unit.upper())
            
            return self.convert_unit(value, from_unit, to_unit)
        
        return {"success": False, "error": "Could not parse conversion query. Format: '10 m to ft' or '20 C to F'"}
    
    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "convert_unit")
        
        if action == "convert_unit":
            # Check if it's a temperature conversion
            from_unit = input_data.get("from", "").upper()
            to_unit = input_data.get("to", "").upper()
            
            if from_unit in ['C', 'F', 'K'] and to_unit in ['C', 'F', 'K']:
                return self.convert_temperature(
                    input_data.get("value", 0),
                    from_unit,
                    to_unit
                )
            return self.convert_unit(
                input_data.get("value", 0),
                input_data.get("from", ""),
                input_data.get("to", "")
            )
        elif action == "convert_currency":
            return self.convert_currency(
                input_data.get("value", 0),
                input_data.get("from", "USD"),
                input_data.get("to", "EUR")
            )
        elif action == "convert_time":
            return self.convert_time(
                input_data.get("time", ""),
                input_data.get("from", "UTC"),
                input_data.get("to", "UTC")
            )
        elif action == "parse":
            return self.parse_and_convert(input_data.get("query", ""))
        elif action == "list_units":
            return self.list_units(input_data.get("category"))
        elif action == "list_timezones":
            return self.list_timezones()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return ConverterSkill().execute(input_data)


if __name__ == "__main__":
    skill = ConverterSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    
    # Test conversions
    tests = [
        {"action": "convert_unit", "value": 10, "from": "m", "to": "ft"},
        {"action": "convert_unit", "value": 25, "from": "C", "to": "F"},
        {"action": "convert_currency", "value": 100, "from": "USD", "to": "EUR"},
        {"action": "convert_time", "time": "14:00", "from": "CET", "to": "EST"},
        {"action": "parse", "query": "5 km to miles"},
    ]
    
    for test in tests:
        print(f"\n{test}:")
        print(json.dumps(skill.execute(test), indent=2, ensure_ascii=False))
