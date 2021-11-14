from gistim import timml_elements, ttim_elements

from .common import gridspec, model_specification
from .data_extraction import as_aquifer_aquitard, layer_statistics
from .tim_server import StatefulTimServer, TimHandler
from .ugrid import to_ugrid2d


def convert_to_script(inpath: str, outpath: str) -> None:
    timml_spec, ttim_spec = model_specification(inpath, {})
    timml_script = timml_elements.convert_to_script(timml_spec)
    ttim_script = ttim_elements.convert_to_script(ttim_spec)

    with open(outpath, "w") as f:
        f.write(timml_script)
        f.write("\n")
        f.write(ttim_script)
