from setuptools import setup

setup(
    name="moira_rest_api",
    version="1.0.0",
    description="REST API for Moira using Webathena",
    author="Gabriel Rodríguez",
    author_email="rgabriel@mit.edu",
    license="MIT",
    py_modules=["api", "decorators", "make_ccache", "util"],
    # TODO: might the name(s) conflict?
    # In theory we should only need to export one (api right now)
    # But we need to `import decorators`
    # Maybe something like https://fortierq.github.io/python-import/ is what we need?
    # Maybe subfolders?
)