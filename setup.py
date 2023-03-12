from setuptools import setup

setup(
    name="moira_rest_api",
    version="1.0.0",
    description="REST API for Moira using Webathena",
    author="Gabriel Rodríguez",
    author_email="rgabriel@mit.edu",
    license="MIT",
    py_modules=["api"], # TODO: might it conflict? doesn't matter if venv though
)