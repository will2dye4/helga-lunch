import os.path
from setuptools import setup, find_packages

from helga_lunch import __version__ as version


with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as f:
    requirements = f.readlines()


setup(
    name='helga-lunch',
    version=version,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    author='William Dye',
    author_email='william@williamdye.com',
    url='https://github.com/will2dye4/helga-lunch',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'helga_plugins': [
            'lunch = helga_lunch.plugin:lunch',
        ]
    },
    install_requires=requirements,
)

