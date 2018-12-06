from setuptools import setup

setup(name='submitter',
      version='0.4',
      description='Simple SGE job submitter.',
      url='https://github.com/BillyLiggins/Submitter',
      author='Billy Liggins',
      author_email='billyliggins@gmail.com',
      license='MIT',
      packages=['submitter'],
      package_dir={'submitter': 'submitter'},
      package_data={'': ['config/config.ini']},
      scripts=['bin/submitter'],
      install_requires=[
          'logzero',
      ],
      zip_safe=False
      )
