from setuptools import setup

setup(
    name='genbot',
    version='0.1.0',    
    description='A general bot package to run any GPT model from OpenAI',
    url='https://github.com/mlangone13/genbot',
    author='Miguel Langone',
    author_email='mlangone13Gmail.com',
    license='BSD 2-clause',
    packages=['genbot'],
    install_requires=[ 'tiktoken',
                        'gradio',
                        'requests',
                        'setuptools',
                        'faiss-cpu',
                        'openai==1.3.4',
                        'mysql-connector-python',
                        'pymysql',
                        'sqlalchemy-stubs',
                        'sqlmodel',
                        'SQLAlchemy'
                        ],

    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)