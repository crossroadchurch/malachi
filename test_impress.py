import os, platform

if platform.system() == "Windows":
    import win32com.client

    lo_service_manager = win32com.client.Dispatch("com.sun.star.ServiceManager")
    lo_service_manager._FlagAsMethod("Bridge_GetStruct")

    hidden = lo_service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
    hidden.Name = "Hidden"
    hidden.Value = True

    desktop = lo_service_manager.CreateInstance("com.sun.star.frame.Desktop")
    # document = desktop.loadComponentFromUrl("file:///C:/Users/graha/Documents/GitHub/malachi/presentations/test1.odp", "_blank", 0, ())
    
    # arg_0 = lo_service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
    # arg_1 = lo_service_manager.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
    # arg_1.Name = "MediaType"
    # arg_1.Value = "images/jpeg"
    # args = [arg_0, arg_1]
    # exporter = lo_service_manager.CreateInstance("com.sun.star.drawing.GraphicExportFilter")
    # page_total = document.getDrawPages().getCount()
    # for i in range(page_total):
    #     page = document.getDrawPages().getByIndex(i)
    #     arg_0.Name = "URL"
    #     arg_0.Value = "file:///C:/Users/graha/Documents/GitHub/malachi/out/" + str(i) + ".jpg"
    #     exporter.setSourceDocument(page)
    #     exporter.filter(args)
    # document.close(True)

    document = desktop.loadComponentFromUrl("file:///C:/Users/graha/Documents/GitHub/malachi/presentations/test2.odp", "_blank", 0, ())
    presentation = document.Presentation
    presentation.start()
    while not presentation.isRunning():
        time.sleep(1)
    # controller = presentation.getController()
    # controller.gotoNextSlide()
    # presentation.end()
    document.close(True)