__file__ = 'OffSystem_v1'
__date__ = '5/29/14'
__author__ = 'ABREZNIC'

import os, arcpy, xlwt, datetime, math

#date
now = datetime.datetime.now()
curMonth = now.strftime("%m")
curDay = now.strftime("%d")
curYear = now.strftime("%Y")
today = curYear + "_" + curMonth + "_" + curDay

#variables
qcfolder = "C:\\TxDOT\\QC\\OffSystem"
workspace = qcfolder + "\\" + today
where = """ RTE_CLASS = '2' OR RTE_CLASS = '3'  """
database = workspace + "\\Comanche_Copy.gdb"
roadways = database + "\\TXDOT_Roadways"
subfiles = database + "\\SUBFILES"
cities = database + "\\City"
districts = database + "\\District"

if not os.path.exists(workspace):
    os.makedirs(workspace)
else:
    arcpy.Delete_management(database)
    for file in os.listdir(workspace):
        thefile = os.path.join(workspace, file)
        os.remove(thefile)


txdotroads = "Database Connections\\Connection to Comanche.sde\\TPP_GIS.APP_TPP_GIS_ADMIN.Roadways\\TPP_GIS.APP_TPP_GIS_ADMIN.TXDOT_Roadways"
txdotsubs = "Database Connections\\Connection to Comanche.sde\\TPP_GIS.APP_TPP_GIS_ADMIN.SUBFILES"
txdotcity = "Database Connections\\Connection to Comanche.sde\\TPP_GIS.APP_TPP_GIS_ADMIN.City\\TPP_GIS.APP_TPP_GIS_ADMIN.City"
txdotdist = "Database Connections\\Connection to Comanche.sde\\TPP_GIS.APP_TPP_GIS_ADMIN.District\\TPP_GIS.APP_TPP_GIS_ADMIN.District"



def copylocal():
    arcpy.CreateFileGDB_management(workspace, "Comanche_Copy.gdb")
    arcpy.Copy_management(txdotsubs, subfiles)
    arcpy.Copy_management(txdotcity, cities)
    arcpy.Copy_management(txdotdist, districts)
    arcpy.SpatialJoin_analysis(txdotroads, districts, roadways)

def overlap():
    arcpy.Select_analysis(roadways, database + "\\FC_Streets", """ RTE_CLASS = '3' """)
    arcpy.Erase_analysis(database + "\\FC_Streets", cities, database + "\\FC_Streets_Errors")
    arcpy.Clip_analysis(roadways, cities, database + "\\City_Roads")
    arcpy.Select_analysis(database + "\\City_Roads", database + "\\County_Roads_Errors", """ RTE_CLASS = '2' """)

    arcpy.Merge_management([database + "\\County_Roads_Errors", database + "\\FC_Streets_Errors"], database + "\\MergedErrors")
    arcpy.SpatialJoin_analysis(database + "\\MergedErrors", districts, workspace + "\\City_OverlapErrors.shp")

    arcpy.Delete_management(database + "\\City_Roads")
    arcpy.Delete_management(database + "\\FC_Streets")
    arcpy.Delete_management(database + "\\County_Roads_Errors")
    arcpy.Delete_management(database + "\\FC_Streets_Errors")
    arcpy.Delete_management(database + "\\MergedErrors")

    errors = []
    cursor = arcpy.UpdateCursor(workspace + "\\City_OverlapErrors.shp")
    for row in cursor:
        geom = row.shape
        len = geom.length * .000621371
        row.setValue("RTE_LEN", len)
        cursor.updateRow(row)
        rowinfo = [row.RTE_ID, row.RTE_LEN, row.DIST_NM, row.DIST_NBR]
        errors.append(rowinfo)
    del cursor
    del row
    return errors

def routeopen():
    print where
    cursor = arcpy.SearchCursor(roadways, where)
    errors = []
    for row in cursor:
        errorinfo = []
        id = row.RTE_ID
        print str(row.OBJECTID) + "," + str(row.RTE_ID)
        if row.RTE_OPEN == 1:
            rte_subfiles = arcpy.SearchCursor(subfiles, "RTE_ID = '" + id + "'")
            for record in rte_subfiles:
                status = record.HIGHWAY_STATUS
                if status != 4:
                    errorinfo.append(id)
                    errorinfo.append(row.RTE_OPEN)
                    errorinfo.append(status)
                    errorinfo.append("RTE_OPEN = 1 requires HIGHWAY_STATUS = 4")
                    errorinfo.append(row.DIST_NM)
                    errorinfo.append(row.DIST_NBR)
                    errors.append(errorinfo)
                    print "ERROR: " + row.OBJECTID
                else:
                    pass
        elif row.RTE_OPEN == 0:
            rte_subfiles = arcpy.SearchCursor(subfiles, "RTE_ID = '" + id + "'")
            for record in rte_subfiles:
                status = record.HIGHWAY_STATUS
                if status != 0:
                    errorinfo.append(id)
                    errorinfo.append(row.RTE_OPEN)
                    errorinfo.append(status)
                    errorinfo.append("RTE_OPEN = 0 requires HIGHWAY_STATUS = 0")
                    errorinfo.append(row.DIST_NM)
                    errorinfo.append(row.DIST_NBR)
                    errors.append(errorinfo)
                    print "ERROR: " + row.OBJECTID
                else:
                    pass
        else:
            errorinfo.append(id)
            errorinfo.append(row.RTE_OPEN)
            errorinfo.append("N/A")
            errorinfo.append("RTE_OPEN must be 1 or 0")
            errorinfo.append(row.DIST_NM)
            errorinfo.append(row.DIST_NBR)
            errors.append(errorinfo)
            print "ERROR: " + row.OBJECTID
    print "got them all"
    return errors
    del cursor
    del row
    print str(errors)

def measurelength():
    cursor = arcpy.SearchCursor(roadways, where)
    errors = []
    for row in cursor:
        errorinfo = []
        id = row.RTE_ID
        geom = row.shape
        ext = geom.extent
        Mmin = round(ext.MMin, 3)
        Mmax = round(ext.MMax, 3)
        Mdiff = abs(Mmax - Mmin)
        wholelen = geom.length * .000621371
        shp_len = round(wholelen, 3)
        rte_len = row.RTE_LEN

        testlen = abs(shp_len - Mdiff)
        if testlen <= .003 and abs(rte_len - testlen) > .003:
            oid = row.OBJECTID
            print "Check out the RTE_LEN on this guy: " + str(oid)
            # cur = arcpy.UpdateCursor(txdotroads, "OBJECTID = " + oid)
            # for i in cur:
            #     i.setValue("RTE_LEN", wholelen)
            #     cur.updateRow(i)
        elif abs(shp_len - Mdiff) > .003:
            errorinfo.append(id)
            errorinfo.append(Mdiff)
            errorinfo.append(shp_len)
            errorinfo.append(rte_len)
            errorinfo.append(row.DIST_NM)
            errorinfo.append(row.DIST_NBR)
            errors.append(errorinfo)
        elif abs(rte_len - Mdiff) > .003:
            errorinfo.append(id)
            errorinfo.append(Mdiff)
            errorinfo.append(shp_len)
            errorinfo.append(rte_len)
            errorinfo.append(row.DIST_NM)
            errorinfo.append(row.DIST_NBR)
            errors.append(errorinfo)
        elif abs(shp_len - rte_len) > .003:
            errorinfo.append(id)
            errorinfo.append(Mdiff)
            errorinfo.append(shp_len)
            errorinfo.append(rte_len)
            errorinfo.append(row.DIST_NM)
            errorinfo.append(row.DIST_NBR)
            errors.append(errorinfo)
        else:
            pass
    print "all errors: " + str(errors)
    return errors
    del cursor
    del row
    print "cursor gone"

def subfilelength():
    dictionary = {}
    cursor = arcpy.SearchCursor(roadways, where)
    for row in cursor:
        id = row.RTE_ID
        len = row.RTE_LEN
        geom = row.shape
        ext = geom.extent
        Mmin = round(ext.MMin, 3)
        Mmax = round(ext.MMax, 3)
        if id not in dictionary.keys():
            dictionary[str(id)] = [len, Mmin, Mmax]
        else:
            currentrecord = dictionary[id]
            currentlength = currentrecord[0]
            currentmin = currentrecord[1]
            currentmax = currentrecord[2]
            newlen = currentlength + len
            if Mmin < currentmin:
                currentmin = Mmin
            if Mmax > currentmax:
                currentmax = Mmax
            dictionary[str(id)] = [newlen, currentmin, currentmax]
    del cursor
    del row
    errors = []
    for i in dictionary.keys():
        firstflag = 0
        sublength = 0
        linevalues = dictionary[i]
        linelen = linevalues[0]
        linemin = linevalues[1]
        linemax = linevalues[2]
        cursor = arcpy.SearchCursor(subfiles, "RTE_ID = '" + i + "'", "", "", "BMP A")
        for row in cursor:
            if firstflag == 0:
                bmp1 = row.BMP
                firstflag += 1
            bmp = row.BMP
            emp = row.EMP
            sublength += row.LEN_OF_SECTION
            dist = row.DISTRICT
            if abs((emp-bmp) - row.LEN_OF_SECTION) > .001:
                errorinfo = []
                errorinfo.append(i)
                errorinfo.append(dist)
                errorinfo.append(bmp1)
                errorinfo.append("")
                errorinfo.append(emp)
                errorinfo.append("")
                errorinfo.append(sublength)
                errorinfo.append("")
                errorinfo.append("BMP and EMP difference does not equal the LEN_OF_SECTION. OBJECTID: " + row.OBJECTID)
                errors.append(errorinfo)
        if abs(linelen - sublength) > .003:
            errorinfo = []
            errorinfo.append(i)
            errorinfo.append(dist)
            errorinfo.append(bmp1)
            errorinfo.append(linemin)
            errorinfo.append(emp)
            errorinfo.append(linemax)
            errorinfo.append(sublength)
            errorinfo.append(linelen)
            errorinfo.append("RTE_LEN does not equal SUBFILES total LEN_OF_SECTION")
            errors.append(errorinfo)
        if abs(linemin - bmp1) > .001:
            errorinfo = []
            errorinfo.append(i)
            errorinfo.append(dist)
            errorinfo.append(bmp1)
            errorinfo.append(linemin)
            errorinfo.append("")
            errorinfo.append("")
            errorinfo.append("")
            errorinfo.append("")
            errorinfo.append("Line minimum measure does not equal starting BMP")
            errors.append(errorinfo)
        if abs(linemax - emp) > .001:
            errorinfo = []
            errorinfo.append(i)
            errorinfo.append(dist)
            errorinfo.append("")
            errorinfo.append("")
            errorinfo.append(emp)
            errorinfo.append(linemax)
            errorinfo.append("")
            errorinfo.append("")
            errorinfo.append("Line maximum measure does not equal ending EMP")
            errors.append(errorinfo)
    return errors

def removevertices():
    errors = []
    spatialRef = arcpy.Describe(txdotroads).spatialReference
    cursor = arcpy.UpdateCursor(txdotroads, where)
    for row in cursor:
        errorinfo = []
        geom = row.shape
        allparts = geom.getPart()
        if allparts.count > 1:
            errorinfo.append(row.OBJECTID)
            errorinfo.append(row.RTE_ID)
            errorinfo.append(row.DIST_NM)
            errorinfo.append(row.DIST_NBR)
            errors.append(errorinfo)
        partAry = arcpy.Array()
        srtpnt = 0
        lastX = 0
        lastY = 0
        for part in allparts:
            ary = arcpy.Array()
            for pnt in part:
                if srtpnt == 0:
                    x = pnt.X
                    y = pnt.Y
                    m = pnt.M
                    nupnt = arcpy.Point(x, y, 0, m)
                    ary.add(nupnt)
                    lastX = x
                    lastY = y
                    srtpnt += 1
                else:
                    x = pnt.X
                    y = pnt.Y
                    m = pnt.M
                    newM = (math.sqrt((abs(x - lastX)) ** 2 + (abs(y - lastY)) ** 2))
                    newMiles = newM * .000621371
                    if newMiles >= .001 and pnt.ID != len(part):
                        nupnt = arcpy.Point(x, y, 0, m)
                        ary.add(nupnt)
                        lastX = x
                        lastY = y
                    elif newMiles < .001 and pnt.ID == len(part):
                        ary.remove(-1)
                        nupnt = arcpy.Point(x, y, 0, m)
                        ary.add(nupnt)
                    elif newMiles >= .001 and pnt.ID == len(part):
                        nupnt = arcpy.Point(x, y, 0, m)
                        ary.add(nupnt)
            partAry.add(ary)
        row.shape - arcpy.Polyline(partAry, spatialRef, False, True)
        cursor.updateRow(row)
    return errors


def assemblereport():
    print "Copying data local..."
    copylocal()
    book = xlwt.Workbook()
    print "Overlap Errors..."
    overlapsheet = book.add_sheet("City Boundary Overlap")
    line = 0
    overlapsheet.write(line, 0, "The following Route IDs are County Roads and FC Streets which cross a City Boundary as found in City_OverlapErrors.shp")
    line += 1
    overlapsheet.write(line, 0, "RTE_ID")
    overlapsheet.write(line, 1, "Overlap Length")
    overlapsheet.write(line, 2, "District Name")
    overlapsheet.write(line, 3, "District Number")
    line += 1
    overlaplist = overlap()
    for i in overlaplist:
        overlapsheet.write(line, 0, i[0])
        overlapsheet.write(line, 1, i[1])
        overlapsheet.write(line, 2, i[2])
        overlapsheet.write(line, 3, i[3])
        line += 1
        print line
    print "Route Open Errors..."
    opensheet = book.add_sheet("Route Open")
    line = 0
    opensheet.write(line, 0, "The following Route IDs contain an error between RTE_OPEN in TxDOT_Roadways and ROADWAY_STATUS in SUBFILES")
    line += 1
    opensheet.write(line, 0, "RTE_ID")
    opensheet.write(line, 1, "RTE_OPEN")
    opensheet.write(line, 2, "HIGHWAY_STATUS")
    opensheet.write(line, 3, "Description")
    opensheet.write(line, 4, "District Name")
    opensheet.write(line, 5, "District Number")
    line += 1
    print "starting routeopen()"
    openlist = routeopen()
    print "script done"
    for i in openlist:
        opensheet.write(line, 0, i[0])
        opensheet.write(line, 1, i[1])
        opensheet.write(line, 2, i[2])
        opensheet.write(line, 3, i[3])
        opensheet.write(line, 4, i[4])
        opensheet.write(line, 5, i[5])
        line += 1
        print line
    print "Geometry and Measure Errors..."
    geomsheet = book.add_sheet("Geometry and Measures")
    line = 0
    geomsheet.write(line, 0, "The following Route IDs contain an error between their measures' length, shape length, and RTE_LEN")
    line += 1
    geomsheet.write(line, 0, "RTE_ID")
    geomsheet.write(line, 1, "Measures' Length")
    geomsheet.write(line, 2, "Shape Length")
    geomsheet.write(line, 3, "RTE_LEN")
    geomsheet.write(line, 4, "District Name")
    geomsheet.write(line, 5, "District Number")
    line += 1
    geomlist = measurelength()
    for i in geomlist:
        geomsheet.write(line, 0, i[0])
        geomsheet.write(line, 1, i[1])
        geomsheet.write(line, 2, i[2])
        geomsheet.write(line, 3, i[3])
        geomsheet.write(line, 4, i[4])
        geomsheet.write(line, 5, i[5])
        line += 1
    print "Subfile Length Errors..."
    subsheet = book.add_sheet("Subfile Lengths")
    line = 0
    subsheet.write(line, 0, "The following Route IDs contain an error between their line and SUBFILES lengths")
    line += 1
    subsheet.write(line, 0, "RTE_ID")
    subsheet.write(line, 1, "District Number")
    subsheet.write(line, 2, "BMP")
    subsheet.write(line, 3, "Min Measure")
    subsheet.write(line, 4, "EMP")
    subsheet.write(line, 5, "Max Measure")
    subsheet.write(line, 6, "Subfile Len")
    subsheet.write(line, 7, "RTE_LEN")
    subsheet.write(line, 8, "Description")
    line += 1
    sublist = subfilelength()
    for i in sublist:
        subsheet.write(line, 0, i[0])
        subsheet.write(line, 1, i[1])
        subsheet.write(line, 2, i[2])
        subsheet.write(line, 3, i[3])
        subsheet.write(line, 4, i[4])
        subsheet.write(line, 5, i[5])
        subsheet.write(line, 6, i[6])
        subsheet.write(line, 7, i[7])
        subsheet.write(line, 8, i[8])
        line += 1
    # print "Multipart Errors..."
    # multisheet = book.add_sheet("Multipart Errors")
    # line = 0
    # multisheet.write(line, 0, "The following Object IDs are multipart features")
    # line += 1
    # multisheet.write(line, 0, "OBJECTID")
    # multisheet.write(line, 1, "RTE_ID")
    # multisheet.write(line, 2, "District Name")
    # multisheet.write(line, 3, "District Number")
    # line += 1
    # multilist = removevertices()
    # for i in multilist:
    #     multisheet.write(line, 0, i[0])
    #     multisheet.write(line, 1, i[1])
    #     multisheet.write(line, 2, i[2])
    #     multisheet.write(line, 3, i[3])
    #     line += 1
    book.save(workspace + "\\ErrorReport_" + today + ".xls")

now = datetime.datetime.now()
print "and away we go... " + str(now)
assemblereport()
now = datetime.datetime.now()
print "that's all folks!" + str(now)