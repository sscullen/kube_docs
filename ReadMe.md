# Kube Docs

Documentation to create Dockerized versions of Python applications that can be run on a Kubernetes cluster. Documentation starts with basic Docker and Kubernetes concepts before going into detailed examples of real world applications.

This is meant to be a Kubernetes crash course covering the most basic essentials.

## Documentation Info

These docs are built with Sphinx and are meant to be deployed to Github pages, although the built HTML can be deployed anywhere.

Install the requirements (Python3.7 preferred):

```
pip install -r requirements.txt
```

To build the HTML docs:

```
./docs/make html
```

Install MiKTex on Windows. https://miktex.org/download

To build the PDF docs:

```
./docs/make latex
```

The first run will take a while, install packages as it prompts you.

When finished, run `pdflatex` on `target` in the `docs\build\latex` directory.

```
pdflatex .\docs\build\latex
```

You will have to run `pdflatex` multiple times to properly generate the figures and Table of Contents, at least twice in my experience.

