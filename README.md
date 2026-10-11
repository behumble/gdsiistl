# gdsiistl

[English](README.md) | [한국어](README.ko.md)

Converts GDSII files to STL files.

This project is a fork of [dteal/gdsiistl](https://github.com/dteal/gdsiistl). We thank the original author and have great respect for their work.

---

GDSII files are often large, complex 2D designs for integrated circuits and MEMS chips. 3D visualization of the designs can be very useful, but this is tricky due to the complexity of the files. This is a simple script that extrudes selected layers of the GDSII files into 3D and outputs them as separate 3D STL files for visualization in an external program.

# Quick start

Install Git. If you do not have uv, follow the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). Then, in a terminal, clone this repository and install the dependencies:

```sh
git clone https://github.com/behumble/gdsiistl
cd gdsiistl
uv sync --locked
```

The `.python-version` file selects Python 3.12. uv can download it if it is not installed, and `uv sync --locked` creates a local `.venv` with the versions recorded in `uv.lock`.

Run the included example from the repository directory:

```sh
uv run --locked gdsiistl.py convert example/example.gds example/layerstack.json
```

This creates `example/example.gds_substrate.stl`, `example/example.gds_soi.stl`, and `example/example.gds_metal.stl` using the names and heights in the JSON file.

# Usage

First, create a layerstack draft from your GDSII file:

```sh
uv run --locked gdsiistl.py draft-layers path/to/file.gds
```

This writes `path/to/file.gds.layerstack.json` and stops without producing STL files. The draft lists every layer/datatype pair that contains polygon geometry. It keeps an existing draft intact instead of overwriting it. Open the JSON in a text editor and change `name` if you want meaningful output names. The default `zmin` and `zmax` put layers in numeric order, one GDS user unit thick. They work for an illustrative 3D view without editing. GDSII does **not** contain physical layer order or thickness, so edit the z values only when you need physical dimensions.

Then convert, passing both files explicitly:

```sh
uv run --locked gdsiistl.py convert path/to/file.gds path/to/file.gds.layerstack.json
```

The included [example/layerstack.json](example/layerstack.json) contains:

```json
{
  "1/0": {"zmin": 0, "zmax": 550, "name": "substrate"},
  "3/0": {"zmin": 552, "zmax": 592, "name": "soi"},
  "6/0": {"zmin": 592, "zmax": 593, "name": "metal"}
}
```

Each key is `layer/datatype` from the GDS, not a label or data type. Keep the key unchanged unless you intend to select a different existing GDS pair; an unknown pair is rejected. Heights use the GDS user unit. Only listed pairs are exported. [Blender](https://www.blender.org/) can import the STL files for viewing and rendering.

## Note

Due to a limitation of the library used to triangulate the polygonal boundaries of the GDSII geometry, the polygon borders (i.e., all geometry) are shifted slightly (by a hardcoded delta of about 0.01 units, or 10 nanometers in standard micron units) before export. Furthermore, due to another related limitation/bug (not yet completely understood; see source code comments), extra triangles are sometimes created covering holes in polygons.

So the output mesh is not guaranteed to be watertight, perfectly dimensioned, or retain all polygon holes, but it should be arbitrarily close and err on the side of extra triangles, so a program (e.g., Blender) can edit the mesh by deleting faces and produce a negligibly-far-from perfect visualization.


