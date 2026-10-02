from core.rules.base import BaseRule, RuleContext, RuleResult, RuleAction
from enum import Enum
from typing import Dict, List

class EmotionalCategory(Enum):
    DISTRESS = "distress"   # Overwhelmed, can't cope
    URGENCY = "urgency"     # ASAP, immediately, rush
    HOSTILITY = "hostility" # Angry, aggressive, critical
    CONFUSION = "confusion" # Lost, don't understand, stuck

class EmotionalRule(BaseRule):
    """
    Emotional Classification Matrix.
    Maps trigger phrases to deterministic emotional states.
    """
    
    EMOTION_MATRIX = {
        EmotionalCategory.DISTRESS: ["overwhelmed", "stressed", "burned out", "depressed", "can't do this"],
        EmotionalCategory.URGENCY: ["asap", "urgent", "quickly", "right now", "no time"],
        EmotionalCategory.HOSTILITY: ["stupid", "useless", "garbage", "hate", "terrible"],
        EmotionalCategory.CONFUSION: ["lost", "confused", "no idea", "what is happening", "stuck"]
    }
    
    def evaluate(self, context: RuleContext) -> RuleResult:
        query = context.content.lower().strip()
        
        detected_emotions = []
        
        for emotion, triggers in self.EMOTION_MATRIX.items():
            if any(t in query for t in triggers):
                detected_emotions.append(emotion.value)
        
        if detected_emotions:
            # Primary emotion is the first one detected
            primary_emotion = detected_emotions[0]
            severity = 0.5 if primary_emotion in ["distress", "hostility"] else 0.2
            
            return RuleResult(
                action=RuleAction.ALLOW,
                reason=f"Emotional state classified: {', '.join(detected_emotions)}",
                severity=severity,
                governance_flags={
                    "authority": False,
                    "delegation": False,
                    "emotional": True,
                    "ambiguity": False,
                    "safety": False
                },
                rule_name=self.name,
                extra_metadata={
                    "emotional_categories": detected_emotions,
                    "primary_emotion": primary_emotion,
                    "requires_deescalation": primary_emotion in ["distress", "hostility"],
                    "suggested_tone": primary_emotion
                }
            )
            
        return RuleResult(
            action=RuleAction.ALLOW,
            reason="Emotionally neutral input.",
            severity=0.0,
            governance_flags={
                "authority": False,
                "delegation": False,
                "emotional": False,
                "ambiguity": False,
                "safety": False
            },
            rule_name=self.name
        )
