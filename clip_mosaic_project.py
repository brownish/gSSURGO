import arcpy, os
from arcpy import env
arcpy.CheckOutExtension("Spatial")
tableOrder = [
            "MUPOLYGON",
            "mapunit",
            "component",
            "chorizon",
            "chstructgrp",
            "chtexturegrp",
            "chtexture",
            "coforprod",
            "cogeomordesc",
            "comonth",
            "copmgrp",
            "muaoverlap",
            "legend",
            "SAPOLYGON",
            "sacatalog",
            "FEATLINE",
            "FEATPOINT"
]


def say(out_text):
    """Prints the output and adds an ArcGIS-readable message"""
    print out_text
    arcpy.AddMessage(out_text)


def create_gdb(ws, name, version):
    """Creates a file geodatabase in the input workspace using the name and version provided"""
    env.overwriteOutput = True
    out_path = os.path.join(ws, name + '.gdb')
    if arcpy.Exists(out_path):
        message = "%s exists. Deleting!" % out_path
        arcpy.Delete_management(out_path)
        say(message)
    else:
        message = "%s does not exist." % out_path
        say(message)

    message = "Creating %s." % out_path
    say(message)
    arcpy.CreateFileGDB_management(ws, name, version)
    return out_path


def define_output_gdb_projection(gdb, coords):
    env.workspace = gdb
    message = "Redefining output GDB's projection"
    say(message)
    for fc in arcpy.ListFeatureClasses():
        arcpy.DefineProjection_management(fc, coords)
    for raster in arcpy.ListRasters():
        arcpy.DefineProjection_management(raster, coords)


def copy_template_gdb(gdb, name, out_ws):
    out_path = os.path.join(out_ws, name + '.gdb')
    message = 'Copying %s to %s' % (name, out_ws)
    say(message)
    if arcpy.Exists(out_path):
        message = "%s already exists. Deleting." % out_path
        say(message)
        arcpy.Delete_management(out_path)
    else:
        pass
    arcpy.Copy_management(gdb, out_path)
    return out_path


def prepare_output_gdb(in_gdb, out_ws, out_name, out_coords):
    message = 'Preparing output geodatabase'
    say(message)
    out_gdb = copy_template_gdb(in_gdb, out_name, out_ws)
    define_output_gdb_projection(out_gdb, out_coords)
    return out_gdb


def build_where_clause_from_list(table, field, valueList):
    """Takes a list of values and constructs a SQL WHERE clause to select those values within a given field and table."""

    # Add DBMS-specific field delimiters
    fieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(table).path, field)

    # Determine field type
    fieldType = arcpy.ListFields(table, field)[0].type

    # Add single-quotes for string field values
    if str(fieldType) == 'String':
        valueList = ["'%s'" % value for value in valueList]

    # Format WHERE clause in the form of an IN statement
    whereClause = "%s IN(%s)" % (fieldDelimited, ', '.join(map(str, valueList)))
    return whereClause


def selectRelatedRecords(sourceLayer, targetLayer, sourceField, targetField):
    # 10.1 compatible:
    sourceIDs = set([row[0] for row in arcpy.da.SearchCursor(sourceLayer, sourceField)])
    # 10.0 compatible:
    #sourceIDs = set([row.getValue(sourceField) for row in arcpy.SearchCursor(sourceLayer, "", "", sourceField)])
    whereClause = build_where_clause_from_list(targetLayer, targetField, sourceIDs)
    if len(sourceIDs) == 0:
        check = 0
        message = "%s is empty...skipping" % (sourceLayer)
        say(message)
    else:
        check = 1
    if int(arcpy.GetCount_management(targetLayer).getOutput(0)) == 0:
        check = 0
        message = "%s is empty...skipping" % (targetLayer)
        say(message)

    if check == 1:
        arcpy.AddMessage("Selecting related records")
##        print "Selecting related records using WhereClause:{0}".format(whereClause)
        arcpy.SelectLayerByAttribute_management(targetLayer, "NEW_SELECTION", whereClause)
    else:
        pass


def appendSelectedRecords(inLayer, targetTable):
    count = str(arcpy.GetCount_management(inLayer).getOutput(0))
    if arcpy.Exists(targetTable):
        message = "%s found! Appending...%s rows" % (targetTable, count)
        say(message)
        arcpy.Append_management(inLayer, targetTable, "TEST")
    else:
        message = "%s not found! Copying...%s rows" % (targetTable, count)
        say(message)
        arcpy.CopyRows_management(inLayer, targetTable)
    arcpy.Delete_management(inLayer)


def getListofValues(layer, field):
    values = set([row[0] for row in arcpy.da.SearchCursor(layer, field)])
    #values = set([row.getValue(field) for row in arcpy.SearchCursor(layer, "", "", field)])
    return values


def appendGDB(inGDB, targetGDB):
    env.workspace = inGDB
    tables = arcpy.ListTables()
    fcs = arcpy.ListFeatureClasses()
    for table in tables:
        targetTable = os.path.join(targetGDB, table)
        if arcpy.Exists(targetTable):
            pass
        else:
            continue
        arcpy.Append_management(table, targetTable)
    for fc in fcs:
        targetFC = os.path.join(targetGDB, fc)
        if arcpy.Exists(targetFC):
            pass
        else:
            continue
        arcpy.Append_management(fc, targetFC)

#---------------------------------------------------
# VALIDATION TOOLS

#   These tools check data.
#---------------------------------------------------


def is_not_empty(dataset):
    if int(arcpy.GetCount_management(dataset).getOutput(0)) != 0:
        return True
    else:
        return False
#---------------------------------------------------
# CLIP TOOLS

#   These tools are used to loop through a workspace and clip the contents to an output workspace.
#---------------------------------------------------


def checkClipFC(inDataset, clipFC):
    """Check the clip extent used to clip all datasets in the following functions. If the clip FC is in a different coordinate system than the dataset to be clipped, False is returned. If they are the same, True is returned."""
    inDesc = arcpy.Describe(inDataset)
    inSR = inDesc.spatialReference
    clipDesc = arcpy.Describe(clipFC)
    clipSR = clipDesc.spatialReference
    if inSR != clipSR:
        arcpy.env.outputCoordinateSystem = clipSR
    else:
        pass
    return arcpy.env.outputCoordinateSystem


def clipFCs(in_ws, clipFC, out_ws):
    """Clip all features in the input workspace and save them to the output workspace"""
    env.workspace = in_ws
    env.overwriteOutput = True
    in_fcs = arcpy.ListFeatureClasses()
    for fc in in_fcs:
        if is_not_empty(fc):
            arcpy.env.outputCoordinateSystem = checkClipFC(fc, clipFC)
            message = "Clipping", fc
            say(message)
            arcpy.Clip_analysis(fc, clipFC, os.path.join(out_ws, fc))
        else:
            message = fc, "is empty! Skipping..."
            say(message)
            if fc in tableOrder:
                tableOrder.remove(fc)
            else:
                pass
            continue


def clipRasters(in_ws, clipFC, out_ws):
    """Clip all rasters in the input workspace and save them to the output workspace"""
    env.workspace = in_ws
    env.overwriteOutput = True
    in_rasters = arcpy.ListRasters()
    for raster in in_rasters:
        checkClipFC(raster, clipFC)
        message = 'Clipping %s to %s' % (raster, os.path.join(out_ws, raster))
        say(message)
        out_extract_raster = arcpy.sa.ExtractByMask(raster, clipFC)
        #arcpy.Mosaic_management(out_extract_raster, r'H:\GIS Data\scratch\soil\SDM_State_WI_scratch.gdb\MuRaster_10m', "FIRST","FIRST", "", "", "NONE")
        out_extract_raster.save(os.path.join(out_ws, raster))

#---------------------------------------------------
# PROJECT TOOLS

#   These tools are used to loop through a workspace and project the contents to the output workspace.
#---------------------------------------------------


def projectFCs(in_ws, out_coords, out_ws):
    env.workspace = in_ws
    env.overwriteOutput = True
    in_fcs = arcpy.ListFeatureClasses()
    for fc in in_fcs:
        if is_not_empty(fc):
            message = 'Projecting %s to %s.' % (fc, os.path.join(out_ws, fc))
            say(message)
            arcpy.Project_management(fc, os.path.join(out_ws, fc), out_coords)
        else:
            message = '%s is empty. Skipping.' % fc
            say(message)


def projectRasters(in_ws, out_coords, out_ws):
    env.workspace = in_ws
    env.overwriteOutput = True
    in_rasters = arcpy.ListRasters()
    for raster in in_rasters:
        print "Projecting", raster, os.path.join(out_ws, raster)
        arcpy.ProjectRaster_management(raster, os.path.join(out_ws, raster), out_coords)

#---------------------------------------------------
# COPY TOOLS

#   These tools are used to loop through a workspace and copy the contents from one workspace to another.
#---------------------------------------------------


def copy_rasters(in_ws, out_ws):
    env.workspace = in_ws
    in_rasters = arcpy.ListRasters()
    for raster in in_rasters:
        message = 'Copying %s.' % raster
        say(message)
        arcpy.CopyRaster_management(raster, os.path.join(out_ws, raster))

#---------------------------------------------------
# APPEND TOOLS

#   These tools are used to loop through a workspace and append the contents to identically named output files in an output workspace.
#---------------------------------------------------


def append_fcs(in_ws, out_ws):
    env.workspace = in_ws
    in_fcs = arcpy.ListFeatureClasses()
    for fc in in_fcs:
        if is_not_empty(fc):
            message = 'Appending %s.' % fc
            say(message)
            arcpy.Append_management(fc, os.path.join(out_ws, fc), "NO_TEST")
        else:
            message = '%s is empty. Skipping.' % fc
            say(message)


def mosaicRasters(in_ws, out_ws):
    env.workspace = in_ws
    in_rasters = arcpy.ListRasters()
    for raster in in_rasters:
        message = "Mosaicking %s to %s" % (raster, os.path.join(out_ws, raster))
        say(message)
        arcpy.Mosaic_management([os.path.join(out_ws, raster), raster], os.path.join(out_ws, raster), "LAST", "LAST", "", "", "NONE")


def mosaic_rasters_to_output_gdb(in_workspaces, out_workspace):
    arcpy.env.workspace = out_workspace
    dict = {}
    for raster in arcpy.ListRasters():
        rasters = []
        rasters.append(os.path.join(out_workspace, raster))
        for workspace in in_workspaces:
            rasters.append(os.path.join(workspace, raster))
        dict[raster] = rasters
    for key, values in dict.iteritems():
        message = 'Mosaicking %s with %s' % (values[0], values[1:])
        say(message)
        arcpy.Mosaic_management(values, os.path.join(out_workspace, key), "LAST", "", "", "", "NONE")
    return dict


def clipWS(in_ws, clipFC, out_ws):
    print "Clipping all feature classes in", in_ws
    clipFCs(in_ws, clipFC, out_ws)
    print "Clipping all rasters in", in_ws
    clipRasters(in_ws, clipFC, out_ws)


def append_tables(in_ws, out_ws):
    env.workspace = in_ws
    for table in arcpy.ListTables():
        if is_not_empty(table):
            message = 'Appending %s.' % table
            say(message)
            print os.path.join(out_ws, table)
            arcpy.Append_management(table, os.path.join(out_ws, table), "NO_TEST")
        else:
            message = '%s is empty. Skipping.' % table
            say(message)


def append_ws(in_ws, out_ws):
    arcpy.env.extent = 'MAXOF'
    print "Appending all feature classes in", in_ws
    append_fcs(in_ws, out_ws)
    append_tables(in_ws, out_ws)
    print "Mosaicking all rasters in", in_ws
    #mosaicRasters(in_ws, out_ws)


def extract_selected_rows(in_table_name, in_gdb, copy_gdb, out_gdb):
    tableDict = {
        "MUPOLYGON":[("mapunit","mukey")],
        "mapunit":[("legend","lkey"),("component","mukey"),("muaggatt","mukey"),("muaoverlap","mukey"),("mucropyld","mukey"),("mutext","mukey"), ("Lookup_Mukey","mukey")],
        "component":[("chorizon","cokey"),("cocanopycover","cokey"),("cocropyld","cokey"),("codiagfeatures","cokey"),("coecoclass","cokey"),("coeplants","cokey"),("coerosionacc","cokey"),("coforprod","cokey"),("cogeomordesc","cokey"),("cohydriccriteria","cokey"),("cointerp","cokey"),("comonth","cokey"),("copmgrp","cokey"),("copwindbreak","cokey"),("corestrictions","cokey"),("cosurffrags","cokey"),("cotaxfmmin","cokey"),("cotaxmoistcl","cokey"),("cotext","cokey"),("cotreestomng","cokey"),("cotxfmother", "cokey")],
        "chorizon":[("chaashto","chkey"),("chconsistence", "chkey"),("chdesgnsuffix","chkey"),("chfrags","chkey"),("chpores","chkey"),("chstructgrp","chkey"),("chtext","chkey"),("chtexturegrp","chkey"),("chunified","chkey")],
        "chstructgrp":[("chstruct","chstructgrpkey")],
        "chtexturegrp":[("chtexture","chtgkey")],
        "chtexture":[("chtexturemod","chtkey")],
        "coforprod":[("coforprodo","cofprodkey")],
        "cogeomordesc":[("cosurfmorphgc","cogeomdkey"),("cosurfmorphhpp","cogeomdkey"),("cosurfmorphmr","cogeomdkey"),("cosurfmorphss","cogeomdkey")],
        "comonth":[("cosoilmoist","comonthkey"),("cosoiltemp","comonthkey")],
        "copmgrp":[("copm","copmgrpkey")],
        "muaoverlap":[("laoverlap","lareaovkey")],
        "legend":[("laoverlap","lkey"),("legendtext","lkey")],
        "SAPOLYGON":[("sacatalog","areasymbol")],
        "sacatalog":[("sainterp","sacatalogkey")],
        "FEATLINE":[("featdesc","featkey")],
        "FEATPOINT":[("featdesc","featkey")],
    }
    in_table_path = os.path.join(in_gdb, in_table_name)
    if in_table_name in tableDict.iterkeys():
        print '---------------------------'
        in_layer = 'in_layer'
        if arcpy.Describe(in_table_path).dataType == 'FeatureClass':
            arcpy.MakeFeatureLayer_management(in_table_path, in_layer)
        else:
            arcpy.MakeTableView_management(in_table_path, in_layer)
        for copy_table_name, value in tableDict[in_table_name]:
            copy_table = os.path.join(copy_gdb, copy_table_name)
            print copy_table_name, copy_table, '---------------------------------------------'
            copy_layer = 'copy_layer'
            if arcpy.Describe(copy_table).dataType == 'FeatureClass':
                arcpy.MakeFeatureLayer_management(copy_table, copy_layer)
            else:
                arcpy.MakeTableView_management(copy_table, copy_layer)
            selectRelatedRecords(in_layer, copy_layer, value, value)
            appendSelectedRecords(copy_layer, os.path.join(out_gdb, copy_table_name))
        arcpy.Delete_management(in_layer)
    else:
        pass


def copy_related_rows(in_gdb, copy_gdb, out_gdb):
    tableOrder = [
            "MUPOLYGON",
            "mapunit",
            "component",
            "chorizon",
            "chstructgrp",
            "chtexturegrp",
            "chtexture",
            "coforprod",
            "cogeomordesc",
            "comonth",
            "copmgrp",
            "muaoverlap",
            "legend",
            "SAPOLYGON",
            "sacatalog",
            "FEATLINE",
            "FEATPOINT"
        ]

    for table in tableOrder:
        print table, os.path.join(in_gdb, table)
        if arcpy.Exists(os.path.join(in_gdb, table)):
            extract_selected_rows(table, in_gdb, copy_gdb, out_gdb)
        else:
            pass


def project_gdb(in_gdb, out_coords, scratch_ws, out_gdb):
    scratch_gdb_name = os.path.splitext(os.path.basename(in_gdb))[0] + '_scratch'
    scratch_gdb_path = os.path.join(scratch_ws, scratch_gdb_name + '.gdb')
    create_gdb(scratch_ws, scratch_gdb_name, '10.0')
    projectFCs(in_gdb, out_coords, scratch_gdb_path)
    projectRasters(in_gdb, out_coords, out_gdb)
    append_fcs(scratch_gdb_path, out_gdb)
    append_tables(in_gdb, out_gdb)
    mosaicRasters(scratch_gdb_path, out_gdb)


def project_mn_gdb(in_gdb, out_coords, scratch_ws, out_gdb):
    scratch_gdb_name = os.path.splitext(os.path.basename(in_gdb))[0] + '_scratch'
    scratch_gdb_path = os.path.join(scratch_ws, scratch_gdb_name + '.gdb')
    create_gdb(scratch_ws, scratch_gdb_name, '10.0')
    projectFCs(in_gdb, out_coords, scratch_gdb_path)

    # CHANGED FROM out_gdb to scratch_gdb_path
    #projectRasters(in_gdb, out_coords, scratch_gdb_path)

    append_fcs(scratch_gdb_path, out_gdb)
    append_tables(in_gdb, out_gdb)


def clip_gdb(in_gdb, clip_fc, scratch_ws):
    scratch_gdb_name = os.path.splitext(os.path.basename(in_gdb))[0] + '_scratch'
    scratch_gdb_path = os.path.join(scratch_ws, scratch_gdb_name + '.gdb')
    create_gdb(scratch_ws, scratch_gdb_name, '10.0')
    clipFCs(in_gdb, clip_fc, scratch_gdb_path)
    copy_related_rows(scratch_gdb_path, in_gdb, scratch_gdb_path)
    #clipRasters(in_gdb, clip_fc, scratch_gdb_path)
    return scratch_gdb_path





mn_gdb = arcpy.GetParameterAsText(0)
adj_gdbs = arcpy.GetParameterAsText(1)
clip_fc = arcpy.GetParameterAsText(2)
outcoords = arcpy.GetParameterAsText(3)
template_gdb = arcpy.GetParameterAsText(4)
temp_ws = arcpy.GetParameterAsText(5)
out_ws = arcpy.GetParameterAsText(6)
outgdb_name = arcpy.GetParameterAsText(7)
delete_temp_gdbs = arcpy.GetParameter(8)

arcpy.env.outputCoordinateSystem = outcoords
#arcpy.env.parallelProcessingFactor = '100%'
arcpy.env.mask = clip_fc

scratch_gdbs = []
mn_scratch_gdb_name = os.path.splitext(os.path.basename(mn_gdb))[0] + '_scratch'
mn_scratch_gdb = os.path.join(temp_ws, mn_scratch_gdb_name + '.gdb')
scratch_gdbs.append(mn_scratch_gdb)

outgdb_path = os.path.join(out_ws, outgdb_name + '.gdb')
prepare_output_gdb(template_gdb, out_ws, outgdb_name, outcoords)
project_mn_gdb(mn_gdb, outcoords, temp_ws, outgdb_path)


for gdb in adj_gdbs.split(';'):
    in_gdb = gdb.replace("'", '')
    scratch_gdb_name = os.path.splitext(os.path.basename(in_gdb))[0] + '_scratch'
    scratch_gdb_path = os.path.join(temp_ws, scratch_gdb_name + '.gdb')
    scratch_gdbs.append(scratch_gdb_path)
    message = 'Starting %s' % in_gdb
    say(message)
    clip_gdb(in_gdb, clip_fc, temp_ws)
    append_ws(scratch_gdb_path, outgdb_path)

if delete_temp_gdbs is True:
    message = 'Deleting temporary data.'
    say(message)
    for gdb in scratch_gdbs:
        message = 'Deleting %s.' % gdb
        say(gdb)
        arcpy.Delete_management(gdb)
