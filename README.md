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
uv run --locked gdsiistl.py example/example.gds
```

It creates `example/example.gds_substrate.stl`, `example/example.gds_soi.stl`, and `example/example.gds_metal.stl`.

# Usage

To convert your own GDSII file, edit the `layerstack` dictionary near the top of `gdsiistl.py` to match its layers. The included example uses:

```python
layerstack = {
    # GDSII layer number: (bottom z, top z, output name)
    1: (0, 550, 'substrate'),
    3: (552, 592, 'soi'),
    6: (592, 593, 'metal'),
}
```

Replace the layer numbers with those in your GDSII file, set each layer's bottom and top heights in the file's user units, and choose names for the output files. Only layers listed in `layerstack` are exported.

Then run the script from the repository directory, replacing the path with your GDSII file:

```sh
uv run --locked gdsiistl.py path/to/file.gds
```

For a layer named `substrate`, the output is written next to the input file as `path/to/file.gds_substrate.stl`. [Blender](https://www.blender.org/) can import the STL files for viewing and rendering.

## Note

Due to a limitation of the library used to triangulate the polygonal boundaries of the GDSII geometry, the polygon borders (i.e., all geometry) are shifted slightly (by a hardcoded delta of about 0.01 units, or 10 nanometers in standard micron units) before export. Furthermore, due to another related limitation/bug (not yet completely understood; see source code comments), extra triangles are sometimes created covering holes in polygons.

So the output mesh is not guaranteed to be watertight, perfectly dimensioned, or retain all polygon holes, but it should be arbitrarily close and err on the side of extra triangles, so a program (e.g., Blender) can edit the mesh by deleting faces and produce a negligibly-far-from perfect visualization.


