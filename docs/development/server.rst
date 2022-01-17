QGIS and conda interpreters
===========================

Communicating between Python interpreters
-----------------------------------------

One of the difficulties of this specific project lies within combining:

* QGIS and its Python interpreter
* A Python package (``gistim``) that effectively requires a conda Python
  distribution

The Python data ecosystem "GIS-stack" (rasterio, geopandas) does not combine
well with QGIS Python interpreter and, numba (a JIT compiler) does not seem to
run at all within the QGIS at all. Trying to install QGIS via conda results in
not being able to run Python in QGIS at all when I last tried.

These are likely not small issues, since QGIS and e.g. rasterio may depend on the
same libaries (GDAL), but not the same version of it; or perhaps require subtly
different environmental variables.

Fortunately, we can fully separate the interpreters, but still communicate
interactively using the Python standard library modules. There's a ``TimServer``
running in the conda environment, which listens to a specific port. The examples
on the bottom of the Python (3) `socketserver documentation
<https://docs.python.org/3/library/socketserver.html>`_ show the basic
principle:

.. code:: Python

    import socketserver
    
    class MyTCPHandler(socketserver.BaseRequestHandler):
        def handle(self):
            self.data = self.request.recv(1024).strip()
            print("{} wrote:".format(self.client_address[0]))
            print(self.data)
            self.request.sendall(self.data.upper())
    
    if __name__ == "__main__":
        HOST, PORT = "localhost", 9999
        with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
            server.serve_forever()

That is, we start a server type (``socketserver.TCPServer`` here), and create
a handler that handles the incoming requests (``MyTCPHandler``).

On the client side (the QGIS plugin in our case), it's as simple as:

.. code:: Python

    import socket

    HOST, PORT = "localhost", 9999
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(bytes(data + "\n", "utf-8"))
        received = str(sock.recv(1024), "utf-8"))

Starting the conda interpreter
------------------------------

Before a Python interpreter inside of a conda environment can run properly, the
environment must be "activated". From the the `conda docs
<https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#activating-an-environment>`_:

    Activating environments is essential to making the software in the
    environments work well. Activation entails two primary functions: adding
    entries to PATH for the environment and running any activation scripts that
    the environment may contain. These activation scripts are how packages can
    set arbitrary environment variables that may be necessary for their
    operation. You can also use the config API to set environment variables.

This is copied to the ``%APPDATA%`` directory as well. It is called by the
QGIS interpreter every time before it attempts to start the conda interpreter.

In overview:

1. During configuration of ``gistim``, the environmental variables are stored in
   a configuration file.
2. When the server is started from QGIS, the environmental variables are loaded
   and a new subprocess is started with these variables.
3. Finally the external (conda) interpreter is called to start up the
   ``TimServer``.
4. After a little setup (a few seconds), the server is ready to receive calls
   from the QGIS plugin.
