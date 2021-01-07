from setuptools import setup, find_packages

setup(name='smartdoor',
      version='1.0',
      description='Smart door APi for iio-tsutsui lab',
      author='Koyo Munechika',
      author_email='munechika.koyo@torus.nr.titech.ac.jp',
      url='https://github.com/munechika-koyo/smartdoor',
      install_requires=['RPi.GPIO', 'nfcpy', 'requests', 'pyyaml'],
      packages=find_packages(),
      include_package_data=True)
