from setuptools import setup, find_packages


setup(
    name="pytfe",
    version="0.0.1",
    packages=find_packages(),
    keywords=("device", "mobile", "cpu", "gpu"),
    install_requires=[],
    package_data={
        "": ["*.py", "*.json", "*.csv"],
    },
    include_package_data=True,
)
