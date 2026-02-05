# setup.py
from setuptools import setup, find_packages

setup(
    name="project-gozen",
    version="0.1.0",
    description="Multi-agent decision-making framework",
    author="Tagomori",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "gozen.web": ["static/**/*"],
    },
    install_requires=[
        "pyyaml>=6.0",
        "anthropic>=0.18.0",
        "google-generativeai>=0.8.0",
        "google-cloud-aiplatform>=1.38.0",
        "aiohttp>=3.9.0",
    ],
    extras_require={
        "web": [
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "websockets>=12.0",
        ],
    },
    entry_points={
        'console_scripts': [
            'gozen=gozen.cli:main',
        ],
    },
    python_requires='>=3.9',
)