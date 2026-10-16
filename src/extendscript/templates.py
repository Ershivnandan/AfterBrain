class ExtendScriptTemplates:
    """Provides reusable, tested After Effects ExtendScript patterns and expressions."""

    # Industry-standard Inertial Bounce expression
    BOUNCE_EXPRESSION = """
// Inertial Bounce Expression
var amp = 0.05;
var freq = 4.0;
var decay = 5.0;
var n = 0;
var numKeys = numKeys;
if (numKeys > 0) {
    n = nearestKey(time).index;
    if (key(n).time > time) { n--; }
}
if (n == 0) {
    t = 0;
} else {
    t = time - key(n).time;
}
if (n > 0 && t < 1) {
    var v = velocityAtTime(key(n).time - thisComp.frameDuration/10);
    value + v*amp*Math.sin(freq*t*2*Math.PI)/Math.exp(decay*t);
} else {
    value;
}
"""

    @staticmethod
    def create_comp(
        name: str = "Main_Comp",
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        duration: float = 10.0,
    ) -> str:
        return f"""
var comp = app.project.items.addComp("{name}", {width}, {height}, 1.0, {duration}, {fps});
comp.openInViewer();
"""

    @staticmethod
    def add_kinetic_title(
        text: str,
        start_time: float = 0.5,
        duration: float = 1.0,
        font_size: int = 90,
        with_bounce: bool = True,
    ) -> str:
        bounce_code = (
            f'textLayer.property("Transform").property("Scale").expression = `{ExtendScriptTemplates.BOUNCE_EXPRESSION}`;'
            if with_bounce
            else ""
        )
        return f"""
// Add Kinetic Title
var textLayer = comp.layers.addText("{text}");
var textProp = textLayer.property("Source Text");
var textDocument = textProp.value;
textDocument.fontSize = {font_size};
textDocument.justification = ParagraphJustification.CENTER_JUSTIFY;
textProp.setValue(textDocument);

// Center position
textLayer.property("Position").setValue([comp.width / 2, comp.height / 2]);

// Scale animation
var scaleProp = textLayer.property("Scale");
scaleProp.setValueAtTime({start_time}, [0, 0]);
scaleProp.setValueAtTime({start_time + duration}, [100, 100]);
{bounce_code}
"""

    @staticmethod
    def wrap_undo(script_body: str, group_name: str = "AI Animation") -> str:
        """Wraps any ExtendScript code in an undo group for single-undo safety."""
        return f"""(function() {{
    app.beginUndoGroup("{group_name}");
    try {{
        {script_body}
        return JSON.stringify({{ status: "success", action: "{group_name}" }});
    }} catch(err) {{
        return JSON.stringify({{ status: "error", message: err.toString(), line: err.line }});
    }} finally {{
        app.endUndoGroup();
    }}
}})();
"""
