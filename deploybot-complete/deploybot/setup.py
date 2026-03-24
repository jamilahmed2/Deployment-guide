from setuptools import setup, find_packages

setup(
    name="deploybot",
    version="1.0.0",
    description="Production-grade SSH deployment automation for developers",
    author="DeployBot",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "paramiko>=3.4.0",
        "typer[all]>=0.12.0",
        "rich>=13.7.0",
        "pyyaml>=6.0.1",
        "jinja2>=3.1.4",
        "cryptography>=42.0.0",
        "questionary>=2.0.1",
        "python-dotenv>=1.0.0",
        "scp>=0.15.0",
    ],
    entry_points={
        "console_scripts": [
            "deploybot=cli:app",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Environment :: Console",
        "Topic :: System :: Systems Administration",
    ],
)
