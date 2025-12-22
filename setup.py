#!/usr/bin/env python
"""
Task Manager Application
A collaborative task and project management system built with Flask.
"""

from setuptools import setup, find_packages
import os

# Read version from VERSION file
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    with open(version_file, 'r') as f:
        return f.read().strip()

# Read the contents of README file
def get_long_description():
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        return f.read()

setup(
    name='task-manager-app',
    version=get_version(),
    description='A collaborative task and project management system',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Development Team',
    author_email='dev@taskmanager.com',
    url='https://github.com/RithishRamesh-dev/task-manager-app-autodev',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask==2.3.3',
        'Flask-SQLAlchemy==3.0.5',
        'Flask-Migrate==4.0.5',
        'Flask-JWT-Extended==4.5.3',
        'Flask-CORS==4.0.0',
        'Flask-Limiter==3.5.0',
        'Flask-SocketIO==5.3.6',
        'psycopg2-binary==2.9.7',
        'python-dotenv==1.0.0',
        'marshmallow==3.26.2',
        'bcrypt==4.0.1',
        'redis==5.0.0',
        'gunicorn==21.2.0',
    ],
    extras_require={
        'dev': [
            'pytest==7.4.2',
            'pytest-cov==4.1.0',
            'black==23.7.0',
            'flake8==6.0.0',
            'PyYAML==6.0.1',
        ]
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Framework :: Flask',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Groupware',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    entry_points={
        'console_scripts': [
            'task-manager=app:app',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/RithishRamesh-dev/task-manager-app-autodev/issues',
        'Source': 'https://github.com/RithishRamesh-dev/task-manager-app-autodev',
        'Documentation': 'https://github.com/RithishRamesh-dev/task-manager-app-autodev/wiki',
    },
)