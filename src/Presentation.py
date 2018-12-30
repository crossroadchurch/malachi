# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R0912 # Too many branches
# pylint: disable=R0914 # Too many local variables
# pylint: disable=R0915 # Too many statements
# pylint: disable=R1702 # Too many nested blocks

"""Represent a Presentation object in Malachi."""

import json
import os
import hashlib
import platform
import pathlib
import time
import mss
import mss.tools
from MalachiExceptions import InvalidPresentationUrlError

class Presentation():
    """Represent a Presentation object in Malachi."""

    def __init__(self, url):
        """
        Create a Presentation from a specified URL.

        Arguments:
        url -- the URL of the presentation, relative to the root Malachi
        directory, e.g. "./presentations.test.odp"

        Possible exceptions:
        InvalidPresentationUrlError -- raised if the file specified by url
        does not exist
        """
        if os.path.isfile(url):
            self.url = url
        else:
            raise InvalidPresentationUrlError(url)
        self.slides = []
        self.title = os.path.basename(url)
        self.update_slides()

    @classmethod
    def get_main_sequence(cls, o_page):
        """Return the main sequence animation node for this page"""
        main_sequence = 4
        o_nodes = o_page.AnimationNode.createEnumeration()
        while o_nodes.hasMoreElements():
            o_node = o_nodes.nextElement()
            if Presentation.get_node_type(o_node) == main_sequence:
                return o_node
        return None

    @classmethod
    def get_node_type(cls, o_node):
        """Return the type of this node"""
        for o_data in o_node.UserData:
            if o_data.Name == "node-type":
                return o_data.Value
        return None

    def update_slides(self):
        """
        Update the slides that Malachi will use for displaying this Presentation
        to clients that are not the main screen.  There will be one slide for each
        animation/transition in the presentation that requires a mouse click.  The
        slide will contain the URL of a thumbnail image with a screen shot of the
        presentation after the animation/transition has occurred.  Thumbnail images
        are saved in a subdirectory of ./thumbnails, with the subdirectory name
        being generated from a MD5 hash of the presentation.
        """
        # Generate md5 hash of presentation file - stackoverflow.com/questions/3431825
        hash_md5 = hashlib.md5()
        with open(self.url, 'rb') as pres_file:
            for chunk in iter(lambda: pres_file.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()

        # Check whether a folder with this hash exists
        if not os.path.isdir("./thumbnails/" + str(file_hash)):
            # Create and populate thumbnail folder
            os.mkdir("./thumbnails/" + str(file_hash))

            if platform.system() == "Windows":
                import win32com.client
                lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
                desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")

            elif platform.system() == "Linux":
                # pylint: disable=E0401 # Linux specific module import
                import uno
                # pylint: enable=E0401
                local = uno.getComponentContext()
                resolver = local.ServiceManager.createInstanceWithContext(
                    "com.sun.star.bridge.UnoUrlResolver", local)
                context = resolver.resolve(
                    "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
                desktop = context.ServiceManager.createInstanceWithContext(
                    "com.sun.star.frame.Desktop", context)

            if platform.system() == "Windows" or platform.system() == "Linux":
                document = desktop.loadComponentFromURL(
                    pathlib.Path(os.path.abspath(self.url)).as_uri(), "_blank", 0, ())
                o_pages = document.getDrawPages()
                total_effects = 0

                for i in range(o_pages.getCount()):
                    o_page = o_pages.getByIndex(i)
                    total_effects += 1
                    # Disable automatic slide transition to allow preview to occur
                    o_page.Change = 0
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
                                            total_effects += 1

                pres_obj = document.getPresentation()
                # Force display to use main monitor, so we know where to screen shot
                pres_obj.setPropertyValue("Display", 1)
                pres_obj.start()
                while not pres_obj.isRunning():
                    time.sleep(1)
                controller = pres_obj.getController()

                pres_wdw = desktop.getCurrentFrame().getContainerWindow()
                pres_bounds = pres_wdw.getPosSize() # Has X, Y, Width and Height properties
                aspect_ratio = o_pages.getByIndex(0).Width / o_pages.getByIndex(0).Height
                if (pres_bounds.Width / pres_bounds.Height) >= aspect_ratio:
                    # Black bars on left / right
                    scp_height = pres_bounds.Height
                    scp_width = scp_height * aspect_ratio
                    scp_y = pres_bounds.Y
                    scp_x = ((pres_bounds.Width - scp_width) / 2) + pres_bounds.X
                else: # Black bars on top / bottom
                    scp_width = pres_bounds.Width
                    scp_height = scp_width / aspect_ratio
                    scp_x = pres_bounds.X
                    scp_y = ((pres_bounds.Height - scp_height) / 2) + pres_bounds.Y
                monitor_area = {
                    "top": int(scp_y), "left": int(scp_x),
                    "width": int(scp_width), "height": int(scp_height)}

                # Iterate through presentation effects in reverse order to avoid
                # having to wait for effects to complete before taking screenshot
                controller.gotoLastSlide()
                controller.gotoNextSlide()
                sct = mss.mss()

                for idx in range(total_effects):
                    time.sleep(0.5)
                    controller.gotoPreviousEffect()
                    # pylint: disable=W0612 # Unused variable (load_check)
                    # load_check is updated to ensure the slide is fully loaded before we take
                    # a screenshot of it, so it is used even if this is not recognised by pylint
                    load_check = controller.getCurrentSlideIndex()
                    # pylint: enable=W0612
                    time.sleep(0.5)
                    thumb_path = pathlib.Path(os.path.join(os.path.abspath("./thumbnails/" + \
                        str(file_hash))), str(total_effects - idx - 1).zfill(3) + ".png")
                    sct_img = sct.grab(monitor_area)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(thumb_path))

                pres_obj.end()
                document.close(False) # Close document, discarding changes

        for thumb_file in os.listdir("./thumbnails/" + str(file_hash)):
            self.slides.append("./thumbnails/" + str(file_hash) + "/" + thumb_file)


    def get_title(self):
        """Return the title of this Presentation, which is its filename"""
        return self.title

    # pylint: disable=W0613 # capo is unused due to OOP coding of to_JSON method
    def to_JSON(self, capo):
        """
        Return a JSON object containing all the data needed to display this BiblePassage
        to a client.
        """
        return json.dumps({
            "type":"presentation",
            "title":self.title,
            "slides":self.slides}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Presentation for saving in a service plan."""
        return json.dumps({"type": "presentation", "url": self.url})

    @classmethod
    def get_all_presentations(cls):
        """Return a list of all presentation URLs in the ./presentations directory."""
        urls = ['./presentations/' + f for f in os.listdir('./presentations')
                if f.endswith('.odp') or f.endswith('.ppt') or f.endswith('.pptx')]
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    pass
