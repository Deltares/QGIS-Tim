from setuptools import find_packages, setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="gistim",
    description="GIS utilities for Tim(ML) Analytic Element modeling",
    long_description=long_description,
    url="https://gitlab.com/deltares/imod/qgis-tim",
    author="Huite Bootsma",
    author_email="huitebootsma@gmail.com",
    license="MIT",
    packages=find_packages(),
    package_dir={"gistim": "gistim"},
    test_suite="gistim/test",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    python_requires=">=3.6",
    install_requires=[
        "affine",
        "geopandas",
        "matplotlib",
        "numba",
        "numpy",
        "pandas",
        "scipy",
        "timml",
        "xarray>=0.15",
    ],
    extras_require={
        "dev": [
            "black",
            "nbstripout",
            "pytest",
            "pytest-cov",
            "pytest-benchmark",
            "sphinx",
            "sphinx_rtd_theme",
        ],
        "optional": [
            "rasterio>=1",
            "netCDF4",
        ],
    },
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Hydrology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    keywords="groundwater modeling",
)
