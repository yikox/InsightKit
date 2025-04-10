from setuptools import setup, find_packages

setup(
    name='insight_kit',
    version='0.0.1',
    packages=find_packages(),
    author='YIKOX',
    author_email='None',
    description='A toolkit for algorithm performance analysis and optimization',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3'
    ],
    install_requires=[
        "Pillow",
        "numpy",
        "opencv-python",
        "scikit-image",
        "psutil",
        "pynvml"
    ],
    entry_points={
        "console_scripts": [
            "diff_picture = insight_kit:diff_picture",  
            "monitor = insight_kit:monitor",
        ]
    },
)
