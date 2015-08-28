#gSSURGO

Tools for manipulating and analyzing gSSURGO soils data in with python and ArcGIS.
Note: No longer clips, projects, or merges the rasters. Fix coming.
- - -


###Clip, Project, and Merge gSSURGO GDBs
####Script Tool Parameter Instructions
1. Minnesota Geodatabase
The path to the freshly downloaded gSSURGO geodatabase for the state of Minnesota. The name doesn’t matter but will be used as the temporary geodatabase name.

2. Adjacent Geodatabases
The paths to the gSSURGO geodatabases for the states adjacent to Minnesota. Again, names don’t matter.

3. Clip Feature Class
The path to the feature class or shapefile used to clip the adjacent states’ data. This feature class should contain only one feature. The file’s coordinate system should be the same as the output coordinate system.

4. Output Coordinate System
The coordinate system you want all the output data to be projected into.

5. Template GDB
This is a copy of a gSSURGO geodatabase with no data (just the schema-tables, feature classes, relationship classes, etc.). It can be created by right-clicking any complete gSSURGO geodatabase and exporting to an XML workspace document. When the dialog box pops up, choose “schema only” and specify the output .xml file. Create a new geodatabase (name does not matter), right click on it, and import an XML workspace document, again choosing “schema only” and specifying the newly created .xml file.

6. Temp Workspace
The folder you would like the temporary geodatabases to be created in. One geodatabase is created for each geodatabase from steps one and two.

7. Output Workspace
The folder you want the final geodatabase to be created in.

8. Output Geodatabase Name
The name you want the final geodatabase to have.

9. Delete Temporary Geodatabase?
The temporary geodatabases will be deleted if this box is checked. It is unchecked by default so you can check out exactly what is being brought over from each adjacent database (each temp geodatabase is about 200MB).
