import platform, time

# Notes: Presenter console should be disabled in LibreOffice Impress

class PresentationHandler():

    def __init__(self):
        # Start LibreOffice service manager
        self.pres_loaded = False
        self.pres_started = False
        self.slide_index = 0

        if platform.system() == "Windows":
            import win32com.client
            self.lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
            self.lo_service_mgr._FlagAsMethod("Bridge_GetStruct")
            self.desktop = self.lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")

    def load_presentation(self, uri):
        if platform.system() == "Windows":
            self.pres_doc = self.desktop.loadComponentFromUrl(uri, "_blank", 0, ())
            self.pres_obj = self.pres_doc.Presentation
            pres_wdw = self.desktop.getCurrentFrame().getContainerWindow()
            pres_wdw.setVisible(False)
        self.pres_loaded = True
        self.slide_index = 0

    def unload_presentation(self):
        if platform.system() == "Windows":
            self.pres_doc.close(True)
        self.pres_started = False
        self.pres_loaded = False

    def start_presentation(self):
        if platform.system() == "Windows":
            self.pres_obj.start()
            while not self.pres_obj.isRunning():
                time.sleep(1)
            self.controller = self.pres_obj.getController()
        self.pres_started = True
        pass

    def stop_presentation(self):
        if platform.system() == "Windows":
            self.pres_obj().end()
        self.pres_started = False
        pass

    def load_slide(self, index):
        if self.pres_loaded:
            if platform.system() == "Windows":
                if self.slide_index + 1 == index:
                    self.controller.gotoNextSlide()
                elif self.slide_index - 1 == index:
                    self.controller.gotoPreviousSlide()
                else:
                    self.controller.gotoSlideIndex(index)
            self.slide_index = index
    
    def next_effect(self):
        if self.pres_started:
            if platform.system() == "Windows":
                self.controller.gotoNextEffect()
                return self.controller.getCurrentSlideIndex()
            else:
                return -1
        else:
            return -1

    def previous_effect(self):
        if self.pres_started:
            if platform.system() == "Windows":
                self.controller.gotoPreviousEffect()
                return self.controller.getCurrentSlideIndex()
            else:
                return -1
        else:
            return -1
