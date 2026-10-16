from pathlib import Path
from src.bridge.mock_bridge import MockAEBridge
from src.bridge.dispatcher import AEBridgeDispatcher


def test_mock_bridge_execution(tmp_path: Path):
    bridge = MockAEBridge(output_dir=tmp_path)
    sample_jsx = """(function() {
    app.beginUndoGroup("Test");
    var comp = app.project.items.addComp("Title_Scene", 1920, 1080, 1.0, 5.0, 30.0);
    comp.layers.addText("Hello World");
    app.endUndoGroup();
})();"""

    result = bridge.execute(sample_jsx, script_name_prefix="test_script")
    assert result["status"] == "success"
    assert result["mode"] == "mock_simulation"

    saved_file = Path(result["saved_script_path"])
    assert saved_file.exists()
    assert "Title_Scene" in saved_file.read_text(encoding="utf-8")


def test_dispatcher_status():
    dispatcher = AEBridgeDispatcher()
    status = dispatcher.get_status()
    assert "active_mode" in status
    assert status["active_mode"] in ("mock", "live")
