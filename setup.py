from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='irail-cli',
      version='0.0.1',
      description='CLI to the iRail API',
      long_description=readme(),
      url='http://github.com/Ben-Baert/iRail',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Programming Language :: Python :: 3.5',
          'License :: OSI Approved :: MIT License',
          'Topic :: Utilities'] 
      author='Ben Baert',
      author_email='benbaert@tuta.io',
      license='MIT',
      packages=['irail'],
      install_requires['requests' ],
      include_package_data=True,
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      zip_safe=False)

