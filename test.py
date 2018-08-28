import win32com.client, os, pathlib, time
import mss, mss.tools

ANIM_ON_CLICK = 1
ANIM_WITH_PREVIOUS = 2
ANIM_AFTER_PREVIOUS = 3

lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
lo_service_mgr._FlagAsMethod("Bridge_GetStruct")
desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")
document = desktop.loadComponentFromURL("file:///C:/Users/graha/Documents/GitHub/malachi/presentations/test3.odp", "_blank", 0, ())

oPages = document.getDrawPages()

def getMainSequence(oPage):
    MAIN_SEQUENCE = 4
    oNodes = oPage.AnimationNode.createEnumeration()
    while oNodes.hasMoreElements():
        oNode = oNodes.nextElement()
        if getNodeType(oNode) == MAIN_SEQUENCE:
            return oNode
    return None

def getNodeType(oNode):
    for oData in oNode.UserData:
        if oData.Name == "node-type":
            return oData.Value
    return None

# effect_counts = [] # Number of click-activated events on each slide
total_effects = 0

for i in range(oPages.getCount()):
    print("\nSLIDE = " + str(i))
    oPage = oPages.getByIndex(i)
    total_effects += 1
    print("Slide transition for slide: " + str(i) + ", Effect: " + str(oPage.Effect) + ", Change: " + str(oPage.Change) + ", Duration: " + str(oPage.Duration))

    # Disable automatic slide transition to allow preview to occur
    oPage.Change = 0

    for j in range(oPage.getCount()):
        s = oPage.getByIndex(j)
        print("  Object: " + str(j) + ", Effect: " + str(s.Effect) + ", Order: " + str(s.PresentationOrder) + ", Speed: " + str(s.Speed) + ", Pres Obj?: " + str(s.IsPresentationObject))

    slide_effects = 0
    # Get main sequence for oPage
    main_seq = getMainSequence(oPage)
    if main_seq != None:
        click_nodes = main_seq.createEnumeration()
        while click_nodes.hasMoreElements():
            click_node = click_nodes.nextElement()
            group_nodes = click_node.createEnumeration()
            while group_nodes.hasMoreElements():
                group_node = group_nodes.nextElement()
                effect_nodes = group_node.createEnumeration()
                while effect_nodes.hasMoreElements():
                    effect_node = effect_nodes.nextElement()
                    for d in effect_node.UserData:
                        if d.Name == 'node-type' and d.Value == ANIM_ON_CLICK:
                            total_effects += 1

pres_obj = document.getPresentation()
pres_obj.setPropertyValue("Display", 1) # Force display to use main monitor, so we know where to screen shot
pres_obj.start()
while not pres_obj.isRunning():
    time.sleep(1)
controller = pres_obj.getController()

pres_wdw = desktop.getCurrentFrame().getContainerWindow()
pres_bounds = pres_wdw.getPosSize() # Has X, Y, Width and Height properties
aspect_ratio = oPages.getByIndex(0).Width / oPages.getByIndex(0).Height
if (pres_bounds.Width / pres_bounds.Height) >= aspect_ratio: # Black bars on left / right
    scp_height = pres_bounds.Height
    scp_width = scp_height * aspect_ratio
    scp_y = pres_bounds.Y
    scp_x = ((pres_bounds.Width - scp_width) / 2) + pres_bounds.X
else: # Black bars on top / bottom
    scp_width = pres_bounds.Width
    scp_height = scp_width / aspect_ratio
    scp_x = pres_bounds.X
    scp_y = ((pres_bounds.Height - scp_height) / 2) + pres_bounds.Y
monitor_area = {"top": int(scp_y), "left": int(scp_x), "width": int(scp_width), "height": int(scp_height)}

controller.gotoLastSlide()
controller.gotoNextSlide()
sct = mss.mss()

for idx in range(total_effects):
    time.sleep(0.5)
    controller.gotoPreviousEffect()
    load_check =  controller.getCurrentSlideIndex() # Ensures a slide is fully loaded before we start screenshots of it
    thumb_path = pathlib.Path(os.path.join(os.path.abspath("./out/")), str(total_effects - idx - 1).zfill(3) + ".png")
    sct_img = sct.grab(monitor_area)
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(thumb_path))

document.close(True) # Close document, discarding changes