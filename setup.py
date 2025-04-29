from setuptools import setup, find_packages

setup(
    name="sd1",
    version="1.0.0",
    author="Varun Israni",
    description="Film Production AI System",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "numpy",
        "pandas",
        "openai",
        "google-generativeai"
    ],
    python_requires=">=3.8",
) 