from setuptools import find_packages, setup

with open("README.rst") as f:
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
    python_requires=">=3.7",
    install_requires=[
        "geopandas",
        "matplotlib",
        "netCDF4",
        "numba",
        "numpy",
        "pandas",
        "scipy",
        "timml",
        "ttim",
        "xarray>=0.15",
    ],
    extras_require={
        "dev": [
            "black",
            "pytest",
            "pytest-cov",
            "sphinx",
            "pydata_sphinx_theme",
        ],
    },
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Hydrology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    keywords="groundwater modeling",
)
