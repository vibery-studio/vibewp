from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()
    # Remove comments and empty lines
    requirements = [r.strip() for r in requirements if r.strip() and not r.startswith("#")]

setup(
    name="vibewp",
    version="1.4.1",
    description="VPS WordPress Manager - CLI for managing WordPress sites on VPS",
    author="VibeWP Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vibewp=cli.main:app",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
