HOLA

# Genbot

Genbot is a Python package that integrates OpenAI's GPT models with a SQL-based conversation history logging feature. It allows for dynamic interaction with GPT models while saving the conversation threads to a database for future retrieval. Additionally, Genbot supports loading and calling functions dynamically based on Swagger JSON definitions, making it a versatile tool for developing advanced AI-driven applications.

## Features

- Integration with OpenAI GPT models for generating responses.
- Conversation logging to SQL databases.
- Dynamic function loading and execution based on Swagger JSON.
- Gradio interface for easy interaction and testing.

## Installation

To install Genbot, run the following command in your terminal:

```bash
pip install git+https://github.com/mlangone13/genbot.git
```


## Quick Start

1. **Set Up Environment Variables**: Make sure to set your OpenAI API key in your environment variables:

```bash
export OPENAI_API_KEY='your_openai_api_key'
```

2. **Basic Usage**: Here's a quick example to get started with Genbot:

```python
from genbot.genbot import Genbot

# Initialize Genbot with your OpenAI API key and model choice
genbot = Genbot(genbot_name="MyGenbot", openai_key="your_openai_api_key", model="gpt-3.5-turbo-1106")

# Load Swagger functions (if needed)
genbot.load_swagger_functions(url="your_swagger_url", swagger_json=your_swagger_json)

# Load database configuration (table MUST exist)
genbot.load_database(user="db_user", pwd="db_password", ip="db_ip", table="db_table", db_type="db_type", autosave_db=False, client_encoding='optional_your_client_encoding')

# Initiate a new Genbot session
# If assistant_id is None, new assistant will be created in your OpenAI account.
# Otherwise you will pull the assistant from OpenAI and load new instructions to it.
genbot.initiate_new_genbot(assistant_id=None, prompt="Your assistant's prompt", instructions="Your assistant's instructions")

# Run Genbot with a user question
question = "Hello, Genbot!"
response = genbot.run(question=question)
genbot.save_conversation(question, response)
print(response)
```

3. **Using Gradio for Interaction**: You can also run Genbot with a Gradio interface for an interactive experience:

```python
genbot.run_on_gradio()
```

Make sure you run 'initiate_new_genbot' function before running on Gradio.

## Configuration

The `Genbot` class accepts several parameters for configuration:

- `genbot_name`: Name of your Genbot instance.
- `openai_key`: Your OpenAI API key.
- `model`: The model identifier for the OpenAI GPT model you wish to use.
- `debug`: Set to `True` for additional debug information.

## Database Support

Genbot currently supports SQL databases for logging conversation history. Ensure your database is accessible and properly configured before initiating Genbot. Table is created automatically but you need to set up the Database before starting Genbot.

## Contributing

We welcome contributions! If you'd like to improve Genbot or add features, please feel free to fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
