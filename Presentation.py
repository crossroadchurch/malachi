import json, os, hashlib, platform, pathlib

class InvalidPresentationUrlError(Exception):
    def __init__(self, url):
        msg = "Could not find a presentation at that the url {url}".format(url=url)
        super(InvalidPresentationUrlError, self).__init__(msg)

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

            if platform.system() == "Windows":
                import win32com.client

                lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
                lo_service_mgr._FlagAsMethod("Bridge_GetStruct")

                hidden_param = lo_service_mgr.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
                hidden_param.Name = "Hidden"
                hidden_param.Value = True

                desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")
                document = desktop.loadComponentFromUrl(pathlib.Path(os.path.abspath(self.url)).as_uri(), "_blank", 0, [hidden_param])
                
                url_arg = lo_service_mgr.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
                type_arg = lo_service_mgr.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
                url_arg.Name = "URL"
                type_arg.Name = "MediaType"
                type_arg.Value = "images/png"
                export_args = [url_arg, type_arg]
                exporter = lo_service_mgr.CreateInstance("com.sun.star.drawing.GraphicExportFilter")
                page_total = document.getDrawPages().getCount()
                for i in range(page_total):
                    page = document.getDrawPages().getByIndex(i)
                    thumb_path = pathlib.Path(os.path.join(os.path.abspath("./thumbnails/" + str(file_hash))), str(i).zfill(3) + ".png").as_uri()
                    url_arg.Value = thumb_path
                    exporter.setSourceDocument(page)
                    exporter.filter(export_args)
                document.close(True)
            
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