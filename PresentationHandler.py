import platform, time

# Notes: Presenter console should be disabled in LibreOffice Impress

class PresentationHandler():

    def __init__(self):
        # Start LibreOffice service manager
        self.pres_loaded = False
        self.pres_started = False
        self.effect_index = 0
        self.effect_counts = []

        if platform.system() == "Windows":
            import win32com.client
            lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
            self.desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")

        elif platform.system() == "Linux":
            import uno
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
            self.desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)


    def load_presentation(self, uri):
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_doc = self.desktop.loadComponentFromURL(uri, "_blank", 0, ())
            self.pres_obj = self.pres_doc.Presentation
            pres_wdw = self.desktop.getCurrentFrame().getContainerWindow()
            pres_wdw.setVisible(False)

        # Record how many click-driven effects there are per slide
        self.effect_counts = []
        oPages = self.pres_doc.getDrawPages()
        ANIM_ON_CLICK = 1
        for i in range(oPages.getCount()):
            oPage = oPages.getByIndex(i)
            slide_effects = 0
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
                                    slide_effects += 1
            self.effect_counts.append(slide_effects)

        self.pres_loaded = True
        self.effect_index = 0

    def unload_presentation(self):
        if platform.system() == "Windows" or platform.system() == "Linux":
            if self.pres_obj.isRunning():
                self.pres_obj.end()
            self.pres_doc.close(False)
        self.pres_started = False
        self.pres_loaded = False

    def start_presentation(self):
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_obj.start()
            while not self.pres_obj.isRunning():
                time.sleep(1)
            self.controller = self.pres_obj.getController()
        self.pres_started = True
        pass

    def stop_presentation(self):
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_obj().end()
        self.pres_started = False
        pass

    def load_effect(self, index):
        if self.pres_loaded:
            if platform.system() == "Windows" or platform.system() == "Linux":
                if self.effect_index + 1 == index:
                    self.controller.gotoNextEffect()
                elif self.effect_index - 1 == index:
                    self.controller.gotoPreviousEffect()
                else:
                    # Calculate which slide we need to go to, then which effect in that slide
                    prev_count = 0
                    fx_count = self.effect_counts[0]
                    i = 0
                    while fx_count < index:
                        prev_count = fx_count
                        i += 1
                        fx_count += self.effect_counts[i] + 1 # don't forget the slide transition
                    # Effect occurs on slide i or its transition to slide i+1
                    if fx_count == index:
                        self.controller.gotoSlideIndex(i+1)
                    else:
                        self.controller.gotoSlideIndex(i)
                        for i in range(index - prev_count):
                            self.controller.gotoNextEffect()
                self.effect_index = index

    def next_effect(self):
        if self.pres_started:
            if platform.system() == "Windows" or platform.system() == "Linux":
                self.controller.gotoNextEffect()
                self.effect_index += 1
                # return self.controller.getCurrentSlideIndex()
                return self.effect_index
            else:
                return -1
        else:
            return -1

    def previous_effect(self):
        if self.pres_started:
            if platform.system() == "Windows" or platform.system() == "Linux":
                self.controller.gotoPreviousEffect()
                self.effect_index -= 1
                # return self.controller.getCurrentSlideIndex()
                return self.effect_index
            else:
                return -1
        else:
            return -1

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