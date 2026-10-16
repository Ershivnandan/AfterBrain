class WorkerPrompts:
    """Prompt engineering templates tailored for Qwen and After Effects ExtendScript."""

    SYSTEM_TEMPLATE = """You are an expert Adobe After Effects Motion Designer, 2D Character Animator, and ExtendScript (JSX) Automation Engineer.

Your job is to convert user requests into clean, production-grade After Effects ExtendScript (.jsx).

### KEY TECHNICAL RULES FOR EXTENDSCRIPT:
1. ExtendScript is based on ECMAScript 3 (ES3). Do NOT use ES6+ features like let, const, arrow functions, or template literals. Use var for all variables.
2. ALWAYS wrap the entire execution in an undo group so the user can undo the entire operation with a single Ctrl+Z:
   app.beginUndoGroup("Action Name");
   try { /* logic */ } catch(e) { /* error */ } finally { app.endUndoGroup(); }
3. Target the active composition:
   var comp = app.project.activeItem;
   if (!(comp && comp instanceof CompItem)) {
       comp = app.project.items.addComp("AI_Scene", 1920, 1080, 1.0, 10.0, 30.0);
       comp.openInViewer();
   }
4. When setting keyframes:
   prop.setValueAtTime(timeInSeconds, value);
5. For smooth animations, apply easing:
   prop.setInterpolationTypeAtKeyframe(keyIndex, KeyframeInterpolationType.BEZIER);
6. For 2D Character Animation with Puppet Tool:
   - Puppet Pins are located under: layer.property("Effects").property("ADBE Puppet").property(1).property(1).property(1)
   - Pin position can be keyframed or given an expression.
7. Return ONLY executable ExtendScript code wrapped in ```jsx ... ``` blocks. Include clear inline comments.

__CHARACTER_CONTEXT__
"""

    CHARACTER_ANIMATION_TEMPLATE = """The user wants to animate a character named '__CHAR_NAME__'.
Request: __USER_PROMPT__

Target character details:
- Layer Name in AE: __LAYER_NAME__
- Description: __DESCRIPTION__
- Personality / Acting Style: __PERSONALITY__
- Rig Type: __RIG_TYPE__
- Available Pins/Joints: __PIN_MAPPING__

Write complete, valid ExtendScript (.jsx) that animates this character according to the request and reflects their personality and acting style. Ensure proper keyframing or expressions are applied. Wrap everything in an undo group.
"""

    GENERAL_ANIMATION_TEMPLATE = """The user wants to create or animate elements in After Effects.
Request: __USER_PROMPT__

Write complete, self-contained ExtendScript (.jsx) that implements this animation.
Create the composition if none exists, set up layers, properties, keyframes, and smooth bezier easing.
Return the code wrapped in ```jsx ... ```.
"""

    @classmethod
    def get_system_prompt(cls, character_context: str) -> str:
        return cls.SYSTEM_TEMPLATE.replace("__CHARACTER_CONTEXT__", character_context)

    @classmethod
    def get_character_prompt(
        cls,
        character_name: str,
        user_prompt: str,
        layer_name: str,
        rig_type: str,
        pin_mapping: str,
        description: str = "",
        personality: str = ""
    ) -> str:
        text = cls.CHARACTER_ANIMATION_TEMPLATE
        text = text.replace("__CHAR_NAME__", character_name)
        text = text.replace("__USER_PROMPT__", user_prompt)
        text = text.replace("__LAYER_NAME__", layer_name)
        text = text.replace("__DESCRIPTION__", description or "N/A")
        text = text.replace("__PERSONALITY__", personality or "N/A")
        text = text.replace("__RIG_TYPE__", rig_type)
        text = text.replace("__PIN_MAPPING__", str(pin_mapping))
        return text

    @classmethod
    def get_general_prompt(cls, user_prompt: str) -> str:
        return cls.GENERAL_ANIMATION_TEMPLATE.replace("__USER_PROMPT__", user_prompt)
