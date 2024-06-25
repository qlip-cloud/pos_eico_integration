from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in pos_eico_integration/__init__.py
from pos_eico_integration import __version__ as version

setup(
	name='pos_eico_integration',
	version=version,
	description='POS EICO Integration',
	author='Mentum Group',
	author_email='aryrosa.fuentes@mentum.group',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
