#!/usr/bin/env python3
"""
Dynamic Configuration Generator for CoreSkill.

Uses LLM to generate missing or extend configuration dynamically.
This eliminates the need for extensive hardcoded defaults.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class ConfigGenerator:
    """
    Generates configuration dynamically using LLM when files are missing.
    
    Features:
    - Auto-generates intent training examples from skill descriptions
    - Creates provider tiers based on available skills
    - Generates topic maps dynamically
    - Extends configuration based on usage patterns
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.root = Path(__file__).resolve().parent.parent.parent
    
    def generate_intent_examples(self, skill_name: str, skill_desc: str, 
                                  count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate intent training examples for a new skill using LLM.
        
        Args:
            skill_name: Name of the skill (e.g., "network_info")
            skill_desc: Description of what the skill does
            count: Number of examples to generate
        
        Returns:
            List of training examples dicts
        """
        if not self.llm:
            # Fallback: generate basic examples without LLM
            return self._basic_examples(skill_name, count)
        
        prompt = f"""Generate {count} diverse Polish phrases that would trigger the skill "{skill_name}".

Skill description: {skill_desc}

Examples should be natural conversational Polish. Include variations like:
- Questions ("jaki mam...", "pokaż mi...")
- Commands ("sprawdź...", "wyświetl...")
- Casual phrasing ("chcę zobaczyć...", "potrzebuję...")

Return ONLY a JSON array:
[
  {{"phrase": "...", "lang": "pl"}},
  ...
]
"""
        try:
            response = self.llm.chat(
                [{"role": "system", "content": "Configuration generator. Return ONLY JSON."},
                 {"role": "user", "content": prompt}],
                temperature=0.7, max_tokens=500
            )
            
            # Extract JSON
            import re
            match = re.search(r'\[[^\]]+\]', response or "")
            if match:
                examples = json.loads(match.group())
                # Add action/skill fields
                for ex in examples:
                    ex["action"] = "use"
                    ex["skill"] = skill_name
                    ex["source"] = "llm_generated"
                return examples
        except Exception as e:
            print(f"[ConfigGen] LLM generation failed: {e}")
        
        return self._basic_examples(skill_name, count)
    
    def _basic_examples(self, skill_name: str, count: int) -> List[Dict[str, Any]]:
        """Generate basic examples without LLM."""
        templates = [
            f"użyj {skill_name}",
            f"uruchom {skill_name}",
            f"potrzebuję {skill_name}",
            f"chcę użyć {skill_name}",
            f"skorzystaj z {skill_name}",
            f"wykonaj {skill_name}",
        ]
        return [
            {
                "phrase": templates[i % len(templates)],
                "action": "use",
                "skill": skill_name,
                "lang": "pl",
                "source": "template_fallback"
            }
            for i in range(count)
        ]
    
    def extend_training_data(self, existing_examples: List[Dict], 
                             min_per_skill: int = 5) -> List[Dict]:
        """
        Automatically extend training data to ensure minimum examples per skill.
        
        Args:
            existing_examples: Current training examples
            min_per_skill: Minimum examples required per skill
        
        Returns:
            Extended list of examples
        """
        # Count examples per skill
        skill_counts = {}
        for ex in existing_examples:
            skill = ex.get("skill", "")
            if skill:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Find skills needing more examples
        extended = list(existing_examples)
        for skill, count in skill_counts.items():
            if count < min_per_skill:
                needed = min_per_skill - count
                new_examples = self.generate_intent_examples(
                    skill, f"Skill: {skill}", count=needed
                )
                extended.extend(new_examples)
        
        return extended
    
    def generate_topic_map(self, skills_dir: Path) -> Dict[str, str]:
        """
        Generate topic map dynamically based on skill descriptions.
        
        Analyzes skill meta.json files to categorize skills into topics.
        """
        topic_map = {
            "stt": "voice",
            "tts": "voice",
        }
        
        # Auto-detect from skill metadata
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_name = skill_dir.name
            meta_path = skill_dir / "meta.json"
            
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    tags = meta.get("tags", [])
                    
                    # Map tags to topics
                    if "web" in tags or "search" in tags:
                        topic_map[skill_name] = "web"
                    elif "git" in tags or "version_control" in tags:
                        topic_map[skill_name] = "git"
                    elif "system" in tags or "shell" in tags:
                        topic_map[skill_name] = "dev"
                    elif "network" in tags or "ip" in tags:
                        topic_map[skill_name] = "system"
                except Exception:
                    pass
        
        return topic_map
    
    def generate_provider_tiers(self, skills_dir: Path) -> Dict[str, Dict]:
        """
        Generate provider tier configuration from available providers.
        
        Analyzes provider meta.json to determine quality/speed tiers.
        """
        tiers = {}
        
        for cap_dir in skills_dir.iterdir():
            if not cap_dir.is_dir():
                continue
            
            providers_dir = cap_dir / "providers"
            if not providers_dir.exists():
                continue
            
            cap_name = cap_dir.name
            cap_tiers = {}
            
            for prov_dir in providers_dir.iterdir():
                if not prov_dir.is_dir():
                    continue
                
                prov_name = prov_dir.name
                meta_path = prov_dir / "meta.json"
                
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        cap_tiers[prov_name] = {
                            "tier": meta.get("tier", "standard"),
                            "quality": meta.get("quality_score", 5),
                            "speed": meta.get("speed_score", 5),
                        }
                    except Exception:
                        cap_tiers[prov_name] = {
                            "tier": "standard", "quality": 5, "speed": 5
                        }
            
            if cap_tiers:
                tiers[cap_name] = cap_tiers
        
        return tiers
    
    def ensure_config_files(self):
        """
        Ensure all required config files exist.
        Generates missing files using LLM or defaults.
        """
        config_dir = self.root / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Required files and their generators
        required = {
            "intent_training_default.json": self._generate_default_training,
            "system.json": self._generate_system_config,
        }
        
        for filename, generator in required.items():
            config_path = config_dir / filename
            if not config_path.exists():
                print(f"[ConfigGen] Generating missing config: {filename}")
                data = generator()
                config_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
    
    def _generate_default_training(self) -> Dict:
        """Generate minimal default training data."""
        return {
            "_meta": {
                "description": "Auto-generated intent training data",
                "version": "1.0",
                "generated": True
            },
            "examples": [
                {"phrase": "pogadajmy głosowo", "action": "use", "skill": "stt", "lang": "pl"},
                {"phrase": "powiedz coś", "action": "use", "skill": "tts", "lang": "pl"},
                {"phrase": "cześć", "action": "chat", "skill": "", "lang": "pl"},
            ]
        }
    
    def _generate_system_config(self) -> Dict:
        """Generate minimal system configuration."""
        return {
            "description": "Auto-generated system config",
            "version": "1.0.0",
            "limits": {"max_evo_iterations": 5},
            "cooldowns": {"rate_limit": 60, "demotion": 300},
            "llm": {"default_temperature": 0.7, "default_max_tokens": 4096},
            "intent": {"confidence_threshold": 0.40}
        }


# Singleton instance
_config_generator: Optional[ConfigGenerator] = None


def get_config_generator(llm_client=None) -> ConfigGenerator:
    """Get or create ConfigGenerator singleton."""
    global _config_generator
    if _config_generator is None:
        _config_generator = ConfigGenerator(llm_client)
    return _config_generator
