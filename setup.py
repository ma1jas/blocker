from setuptools import setup, find_packages

setup(
    name='blocker',
    description=(
        "Generates class registers from students' GCSE and A-level options "
        "that are as balanced as possible"
        ),
    keywords=['timetable', 'school', 'block', 'options'],
    url='https://github.com/ma1jas/blocker',
    author='John Stark',
    author_email='starkey7@gmail.com',
    version='0.0.0',
    license='GPL-3',
    packages=find_packages(),
    install_requires=['click'],
    extras_require={},
    entry_points={
        'console_scripts': ['blocker = blocker.blocker:main']
    },
)
