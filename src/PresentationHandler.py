# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R0902 # Limit on number of instance attributes
# pylint: disable=R0914 # Too many local variables
# pylint: disable=R1702 # Too many nested blocks
# pylint: disable=R1705 # Unnecessary "else" after "return".  Disabled for code readability

"""
Control the display of Presentations using LibreOffice.
The Presenter console should be disable in LibreOffice Impress to
ensure that this is not used to control the presentation instead.
"""

import platform
import time
from Presentation import Presentation

class PresentationHandler():
    """
    Control the display of Presentations using LibreOffice.
    The Presenter console should be disable in LibreOffice Impress to
    ensure that this is not used to control the presentation instead.
    """

    def __init__(self):
        # Start LibreOffice service manager
        self.pres_loaded = False
        self.pres_started = False
        self.effect_index = 0
        self.effect_counts = []
        self.pres_doc = None
        self.pres_obj = None
        self.controller = None

        if platform.system() == "Windows":
            import win32com.client
            lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
            self.desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")

        elif platform.system() == "Linux":
            # pylint: disable=E0401 # Linux specific module import
            import uno
            # pylint: enable=E0401
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", local)
            context = resolver.resolve(
                "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
            self.desktop = context.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", context)


    def load_presentation(self, uri):
        """
        Load a specified presentation and calculate the number of
        click-driven effects there are for each of its slides.

        uri -- the URL of the presentation to be loaded.
        """
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_doc = self.desktop.loadComponentFromURL(uri, "_blank", 0, ())
            self.pres_obj = self.pres_doc.Presentation
            self.pres_obj.setPropertyValue("Display", 2) # Force display to use secondary monitor
            pres_wdw = self.desktop.getCurrentFrame().getContainerWindow()
            pres_wdw.setVisible(False)

        # Record how many click-driven effects there are per slide
        self.effect_counts = []
        o_pages = self.pres_doc.getDrawPages()
        for i in range(o_pages.getCount()):
            o_page = o_pages.getByIndex(i)
            slide_effects = 0
            # Get main sequence for oPage
            main_seq = Presentation.get_main_sequence(o_page)
            if main_seq is not None:
                click_nodes = main_seq.createEnumeration()
                while click_nodes.hasMoreElements():
                    click_node = click_nodes.nextElement()
                    group_nodes = click_node.createEnumeration()
                    while group_nodes.hasMoreElements():
                        group_node = group_nodes.nextElement()
                        effect_nodes = group_node.createEnumeration()
                        while effect_nodes.hasMoreElements():
                            effect_node = effect_nodes.nextElement()
                            for effect_data in effect_node.UserData:
                                if effect_data.Name == 'node-type' and \
                                    effect_data.Value == 1: # Animate on click
                                    slide_effects += 1
            self.effect_counts.append(slide_effects)

        self.pres_loaded = True
        self.effect_index = 0

    def unload_presentation(self):
        """
        Unload the current presentation from LibreOffice, stopping
        it if necessary
        """
        if platform.system() == "Windows" or platform.system() == "Linux":
            if self.pres_obj.isRunning():
                self.pres_obj.end()
            self.pres_doc.close(False)
        self.pres_started = False
        self.pres_loaded = False

    def start_presentation(self):
        """Start the currently loaded presentation in LibreOffice."""
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_obj.start()
            while not self.pres_obj.isRunning():
                time.sleep(1)
            self.controller = self.pres_obj.getController()
        self.pres_started = True

    def stop_presentation(self):
        """End the currently running presentation in LibreOffice."""
        if platform.system() == "Windows" or platform.system() == "Linux":
            self.pres_obj().end()
        self.pres_started = False

    def load_effect(self, index):
        """
        Go to a specified effect in this presentation.

        index -- the effect index to be loaded.
        """
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
        """
        Advance to the next effect in this presentation.
        Returns -1 if the presentation is not started or an unsupported
        OS is being used; otherwise returns the new index of the current
        effect (after the animated effect has completed).
        """
        if self.pres_started:
            if platform.system() == "Windows" or platform.system() == "Linux":
                before_index = self.controller.getCurrentSlideIndex()
                self.controller.gotoNextEffect()
                self.effect_index += 1
                after_index = self.controller.getCurrentSlideIndex()
                if after_index != before_index:
                    # Starting new slide, so resync self.effect_index
                    fx_count = 0
                    for i in range(after_index):
                        fx_count += self.effect_counts[i] + 1
                    self.effect_index = fx_count
                return self.effect_index
            else:
                return -1
        else:
            return -1

    def previous_effect(self):
        """
        Advance to the previous effect in this presentation.
        Returns -1 if the presentation is not started or an unsupported
        OS is being used; otherwise returns the new index of the current
        effect (after the animated effect has completed).
        """
        if self.pres_started:
            if platform.system() == "Windows" or platform.system() == "Linux":
                before_index = self.controller.getCurrentSlideIndex()
                self.controller.gotoPreviousEffect()
                self.effect_index -= 1
                after_index = self.controller.getCurrentSlideIndex()
                if after_index != before_index:
                    # Starting new slide, so resync self.effect_index
                    fx_count = 0
                    for i in range(after_index):
                        fx_count += self.effect_counts[i] + 1
                    self.effect_index = fx_count - 1
                return self.effect_index
            else:
                return -1
        else:
            return -1
