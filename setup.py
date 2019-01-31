import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jupytex",
    version="0.0.3",
    author="Angus Hollands",
    author_email="goosey15@gmail.com",
    description="Jupyter execution of TeX code environments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agoose77/jupytex",
    packages=setuptools.find_packages(),
    package_data={
        'jupytex.data': ['*', '.*']
    },
    entry_points={'console_scripts': [
            'jupytex=jupytex.__main__:main',
        ],
    },
    install_requires=['colorama', 'jupyter_client', 'jupyter', 'importlib_resources'],
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Framework :: Jupyter",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: LaTeX"
    ],
)
