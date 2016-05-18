from distutils.core import setup
import os

setup(name="LiPyc",
        version="0.1.0",
        description="",
        author="Laurent Prosperi",
        author_email="laurent.prosperi@ens-cachan.fr",
        url="",
        platforms="",
        license="",
        package_dir = {"lipyc": "src"},
        packages=["lipyc", "lipyc.panels"],
        requires=["PIL", "tkinter"],
        data_files=[
            ("", ["album_default.png", "file_default.png"]),
        ]
    )
