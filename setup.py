from setuptools import setup

setup(name='submitter',
      version='0.1',
      description='Simple SGE job submitter.',
      url='https://github.com/BillyLiggins/Submitter',
      author='Billy Liggins',
      author_email='billyliggins@gmail.com',
      license='MIT',
      packages=['submitter'],
      scripts=['bin/submitter'],
      zip_safe=False)
