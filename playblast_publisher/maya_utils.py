from maya import cmds
from maya import mel

def scene_path():
    """The full path of the open scene, or "" if it was never saved."""
    return cmds.file(query=True, sceneName=True) or ""

# listing cameras
def list_cameras():
    """Camera names, with persp last. Skips Maya's built-in top/front/side cameras."""
    shot_cameras = []
    for shape in cmds.ls(type="camera"):
        # cameras have "shape" which is lens under a "transform" which is position
        transform = cmds.listRelatives(shape, parent=True)[0]
        is_builtin = cmds.camera(shape, query=True, startupCamera=True)
    if not is_builtin:
        shot_cameras.append(transform)
    shot_cameras.sort()
    shot_cameras.append("persp")
    return shot_cameras
        
def frame_range():
    """The frames highlighted on the timeline, or the whole playback range."""
    slider = mel.eval("$tmp = $gPlayBackSlider")
    
    if cmds.timeControl(slider, query=True, rangeVisible=True):
        start, end = cmds.timeControl(slider, query=True, rangeArray=True)
        return int(start), int(end) - 1
    
    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    return int(start), int(end)

def scene_fps():
    """Frames per second, e.g. 24.0. currentTimeUnitToFPS is a MEL procedure built into Maya."""
    return mel.eval("currentTimeUnitToFPS()")

def movie_supported():
    """True if this computer's Maya can write movie files."""
    formats = cmds.playblast(query=True, format=True) or []
    return "qt" in formats

def find_viewport():
    """The viewport (Maya calls it a model panel) to playblast from."""
    # viewport the artist last clicked
    focused = cmds.getPanel(withFocus=True)
    if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
        return focused
    # first viewport that's visible on screen
    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
        raise RuntimeError("No viewport is visible. Show a perspective view and try again.")

def playblast(prefix, camera, start, end, width, height, movie):
    """Playblast through a camera, then put the artist's viewport camera back."""
    panel = find_viewport()
    original_camera = cmds.modelPanel(panel, query=True, camera=True)
    cmds.lookThru(panel, camera)
    
    try:
        if movie:
            file_format, compression = "qt", "H.264"
        else:
            file_format, compression = "image", "png"
        return cmds.playblast(
            filename=str(prefix),
            format=file_format,
            compression=compression,
            startTime=start,
            endTime=end,
            widthHeight=(width, height),
            percent=100,
            quality=100,
            editorPanelName=panel,
            offScreen=True,
            showOrnaments=False,
            viewer=False,
            forceOverwrite=False,
        )
    finally:
        cmds.lookThru(panel, original_camera)
    
