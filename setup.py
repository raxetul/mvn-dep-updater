import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mvn-dep-updater",
    version="0.0.1",
    author="Tugay ÇALYAN, Emrah URHAN",
    author_email="tugaycalyan@hacettepe.edu.tr, raxetul@gmail.com",
    description="A local dependency version updater for Apache Maven and Gitlab",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/raxetul/mvn-dep-updater",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    entry_points={
        'console_scripts': ['mvn-dep-updater=mvn_dep_updater.main:main'],
    },
    install_requires=[
          'GitPython',
          'python-gitlab'
    ],
)
