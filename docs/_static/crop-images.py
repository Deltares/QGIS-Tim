from pathlib import Path

from PIL import Image

dst = Path("./cropped")
dst.mkdir(exist_ok=True)


for path in [
    "c:\src\qgis-tim\docs\_static\qgis-add-geometry.png",
    "c:\src\qgis-tim\docs\_static\qgis-advanced-digitizing-toolbar.png",
    "c:\src\qgis-tim\docs\_static\qgis-attribute-table.png",
    "c:\src\qgis-tim\docs\_static\qgis-browser-layers-active.png",
    "c:\src\qgis-tim\docs\_static\qgis-openstreetmap.png",
    "c:\src\qgis-tim\docs\_static\qgis-plugin-menu.png",
    "c:\src\qgis-tim\docs\_static\qgis-plugins.png",
    "c:\src\qgis-tim\docs\_static\qgis-project-crs.png",
    "c:\src\qgis-tim\docs\_static\qgis-project-properties.png",
    "c:\src\qgis-tim\docs\_static\qgis-toggle-editing.png",
    "c:\src\qgis-tim\docs\_static\qgis-views-browser.png",
    "c:\src\qgis-tim\docs\_static\qgis-views-layers.png",
]:
    img = Image.open(path)
    w, h = img.size
    out = img.crop((0, h - 1024, 1680, h))
    out.save(dst / Path(path).name)
