import win32com.client, os

lo_service_mgr = win32com.client.Dispatch("com.sun.star.ServiceManager")
lo_service_mgr._FlagAsMethod("Bridge_GetStruct")

hidden_param = lo_service_mgr.Bridge_GetStruct("com.sun.star.beans.PropertyValue")
hidden_param.Name = "Hidden"
hidden_param.Value = True

desktop = lo_service_mgr.CreateInstance("com.sun.star.frame.Desktop")
document = desktop.loadComponentFromUrl("file:///C:/Users/graha/Documents/GitHub/malachi/presentations/test1.odp", "_blank", 0, [hidden_param])

oPages = document.getDrawPages()

for i in range(oPages.getCount()):
    o = oPages.getByIndex(i)
    e = o.AnimationNode.createEnumeration()
    while e.hasMoreElements():  #https://gist.github.com/maffoo/977752
        print("blob")
        elt = e.nextElement()
        for d in elt.UserData:
            print(d.Name)
            print(d.Value)
            print(elt)
            anim_enum = elt.createEnumeration()
            while anim_enum.hasMoreElements():
                print("anim")
                anim_enum.nextElement()
    print("Slide: " + str(i) + ", Effect: " + str(o.Effect) + ", Change: " + str(o.Change) + ", Duration: " + str(o.Duration))
    for j in range(o.getCount()):
        s = o.getByIndex(j)
        print("  Object: " + str(j) + ", Effect: " + str(s.Effect) + ", Order: " + str(s.PresentationOrder) + ", Speed: " + str(s.Speed))
        print(s.IsPresentationObject)

    # page 595