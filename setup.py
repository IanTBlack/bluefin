import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
	
	
setuptools.setup(
    name="bluefin", # Replace with your own username
    version="0.0.1",
    author="Ian Black",
    author_email="blackia@oregonstate.edu",
    description="Modules for controlling Bluefin 1.5 kWh batteries over RS-485.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
    install_requires=[
        'pyserial'  #https://pypi.org/project/pyserial/
        ],
)