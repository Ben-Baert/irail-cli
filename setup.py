from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='irail',
      version='0.0.3',
      description='CLI to the iRail API',
      long_description="""
      Options:

        - Liveboard
        - Itinerary
        - Vehicle (planned)
      """,
      url='http://github.com/Ben-Baert/iRail',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'License :: OSI Approved :: MIT License',
          'Topic :: Utilities'],
      author='Ben Baert',
      author_email='benbaert@tuta.io',
      license='MIT',
      packages=['irail', 'irail.commands'],
      install_requires=['requests', 'click'],
      include_package_data=True,
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      entry_points='''
              [console_scripts]
              irail=irail.cli:cli
              ''',
      zip_safe=False)
