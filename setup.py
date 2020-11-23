from setuptools import setup


setup(
    name="sobek",
    description="functions for sobek-models",
    author="D. Tollenaar",
    author_email="daniel@d2hydro.nl",
    url="http://daniel@d2hydro.nl",
    license="MIT",
    setup_requires=["setuptools_scm"],
    python_requires=">=3.6",
    packages=["sobek"],
    package_dir={"sobek": "sobek"},
    zip_safe=False,
    scripts=[
             "scripts/viewer.py",
             "scripts/upload_test.py"],
    keywords="sobek",
)
