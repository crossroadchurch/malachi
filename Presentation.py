import json, os, hashlib, platform, pathlib, time
import mss, mss.tools
from MalachiExceptions import InvalidPresentationUrlError

class Presentation():

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./presentations/test.odp"
        if os.path.isfile(url):
            self.url = url
        else:
            raise InvalidPresentationUrlError(url)
        self.slides = []
        self.title = os.path.basename(url)
        self.update_slides()
        return

    def get_main_sequence(self, oPage):
        MAIN_SEQUENCE = 4
        oNodes = oPage.AnimationNode.createEnumeration()
        while oNodes.hasMoreElements():
            oNode = oNodes.nextElement()
            if self.get_node_type(oNode) == MAIN_SEQUENCE:
                return oNode
        return None

    def get_node_type(self, oNode):
        for oData in oNode.UserData:
            if oData.Name == "node-type":
                return oData.Value
        return None

    def update_slides(self):
        # Generate md5 hash of presentation file - stackoverflow.com/questions/3431825
        hash_md5 = hashlib.md5()
        with open(self.url, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()

        # Check whether a folder with this hash exists
        if not os.path.isdir("./thumbnails/" + str(file_hash)):
            # Create and populate thumbnail folder
            os.mkdir("./thumbnails/" + str(file_hash))

            ANIM_ON_CLICK = 1
            ANIM_WITH_PREVIOUS = 2
            ANIM_AFTER_PREVIOUS = 3

            if platform.system() == "Windows":
                import win32com.client
                lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
                desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")

            elif platform.system() == "Linux":
                import uno
                local = uno.getComponentContext()
                resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
                context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
                desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)

            if platform.system() == "Windows" or platform.system() == "Linux":
                document = desktop.loadComponentFromURL(pathlib.Path(os.path.abspath(self.url)).as_uri(), "_blank", 0, ())
                oPages = document.getDrawPages()
                total_effects = 0

                for i in range(oPages.getCount()):
                    oPage = oPages.getByIndex(i)
                    total_effects += 1
                    # Disable automatic slide transition to allow preview to occur
                    oPage.Change = 0
                    # Get main sequence for oPage
                    main_seq = self.get_main_sequence(oPage)
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

                # Iterate through presentation effects in reverse order to avoid having to wait for effects to complete before taking screenshot
                controller.gotoLastSlide()
                controller.gotoNextSlide()
                sct = mss.mss()

                for idx in range(total_effects):
                    time.sleep(0.5)
                    controller.gotoPreviousEffect()
                    load_check =  controller.getCurrentSlideIndex() # Ensures a slide is fully loaded before we start screenshots of it
                    time.sleep(0.5)
                    thumb_path = pathlib.Path(os.path.join(os.path.abspath("./thumbnails/" + str(file_hash))), str(total_effects - idx - 1).zfill(3) + ".png")
                    sct_img = sct.grab(monitor_area)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(thumb_path))

                pres_obj.end()
                document.close(False) # Close document, discarding changes

        for f in os.listdir("./thumbnails/" + str(file_hash)):
            self.slides.append("./thumbnails/" + str(file_hash) + "/" + f)


    def get_title(self):
        return self.title

    def to_JSON(self, capo):
        return json.dumps({"type":"presentation", "title":self.title, "slides":self.slides}, indent=2)
    
    def __str__(self):
        return self.get_title()
    
    def save_to_JSON(self):
        return json.dumps({"type": "presentation", "url": self.url})

    @classmethod
    def load_from_JSON(cls, json_data):
        # Precondition json_data["type"] == "presentation"
        json_obj = json.loads(json_data)
        # TODO: Exception handling - pass upstream
        return Presentation(json_data["url"])

    @classmethod
    def get_all_presentations(cls):
        urls = ['./presentations/' + f for f in os.listdir('./presentations')
                if f.endswith('.odp') or f.endswith('.ppt') or f.endswith('.pptx')]
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    # p = Presentation('./test1.odp')
    # print(Presentation.get_all_presentations())
    pass