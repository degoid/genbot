import os
import time
import json
import types
import requests
import gradio as gr
from openai import OpenAI
from datetime import datetime
from sqlalchemy import Column, TEXT
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel, Session, create_engine

class Conversation(SQLModel, table=True):

    __tablename__: str = "conversation"

    user_question: str = Field(sa_column=Column(TEXT))
    ia_answer: str = Field(sa_column=Column(TEXT))
    thread_id: str = Field(sa_column=Column(TEXT))
    date_created: datetime = Field(
        primary_key=True,
        default=datetime.now(),
        nullable=False,
    )


class DatabaseAdmin():
    def __init__(
            self,
            user,
            pwd,
            ip,
            table,
            db_type,
            client_encoding=None,
            debug=False
            ):

        try:
            if client_encoding:
                self.engine = create_engine(f"{db_type}://{user}:{pwd}@{ip}/{table}", client_encoding='utf8')    
            else:
                self.engine = create_engine(f"{db_type}://{user}:{pwd}@{ip}/{table}")    
            SQLModel.metadata.create_all(self.engine)
            self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            if debug: print(f"[Database] - Successfully connected to {db_type}://{user}:{pwd}@{ip}/{table}")
        except Exception as e:
            print(f"[Database] - Error trying to connect to {db_type}://{user}:{pwd}@{ip}/{table}")
            print(f"[Database] - {e}")


    def save_conversation(self, question, answer, thread_id):
        bot = Conversation(
            user_question=question,
            ia_answer=answer,
            thread_id=thread_id,
            date_created=datetime.utcnow(),
        )
        try:
            with Session(self.engine) as session:
                session.add(bot)
                session.commit()
        except Exception as e:
            print(f"[Database] - {e}")
            raise e


class FunctionsBuilder:

    def __init__(self):
        self.URL = None
        self.functions_list = []

    def __init__(self, url, swagger_json):
        self.URL = url
        self.load_dynamic_functions_from_swagger(swagger_json)
        self.load_openai_functions_structure_from_swagger(swagger_json)

    def get_method_name(self, details, http_method, path):
        method_name = details.get('operationId', http_method + path.replace('/', '_'))
        return method_name.replace('-','_').lower()
        
    def load_dynamic_functions_from_swagger(self, swagger_json):
        """
        Loads functions dynamically based on the Swagger 2.0 JSON definitions.
        """
        for path, methods in swagger_json['paths'].items():
            for http_method, details in methods.items():
                # Construct the method name from operationId or create a fallback
                method_name = self.get_method_name(details, http_method, path)
                # Create a dynamic method
                dynamic_method = self.create_method_from_swagger(http_method, path, details.get('parameters', []))
                # Attach the method to the class with the method name
                setattr(self, method_name, types.MethodType(dynamic_method, self))
            
    def load_openai_functions_structure_from_swagger(self, swagger_json):
        functions_list = []

        # Add the retrieval_function as the first item in the list
        functions_list.append({
            "type": "retrieval"
        })

        for path, methods in swagger_json['paths'].items():
            for http_method, details in methods.items():
                # Prepare the base structure of the function dictionary
                function_dict = {
                    "type": "function",
                    "function": {
                        "name": self.get_method_name(details, http_method, path),
                        "description": details.get("description"),
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }

                # Check if parameters are defined and process them
                if "parameters" in details:
                    for param in details["parameters"]:
                        # Assuming parameters are in path or body as per Swagger 2.0
                        if param.get("in") == "path" or param.get("in") == "body":
                            prop_name = param.get("name")
                            function_dict["function"]["parameters"]["properties"][prop_name] = {
                                "type": str(param.get("type", "string")),  # Default to string if type is not specified
                                "description": param.get("description")
                            }
                            if param.get("required", False):
                                function_dict["function"]["parameters"]["required"].append(prop_name)

                functions_list.append(function_dict)

        self.functions_list = functions_list

    
    def create_method_from_swagger(self, http_method, path, parameters):
        """
        Creates a dynamic method based on the endpoint information from Swagger.
        """
        def dynamic_method(self, **kwargs):
            # Replace path parameters with actual values provided in kwargs
            url = self.URL + path
            for param in parameters:
                if param['in'] == 'path':
                    url = url.replace('{' + param['name'] + '}', str(kwargs[param['name']]))

            # Separate the query parameters from the body parameters
            query_params = {param['name']: kwargs[param['name']] for param in parameters if param['in'] == 'query' and param['name'] in kwargs}
            body_params = {param['name']: kwargs[param['name']] for param in parameters if param['in'] == 'body' and param['name'] in kwargs}

            # Make the HTTP request based on the method
            if http_method == 'get':
                response = requests.get(url, params=query_params)
            elif http_method == 'post':
                response = requests.post(url, json=body_params)
            elif http_method == 'delete':
                response = requests.delete(url, json=body_params)
            elif http_method == 'put':
                response = requests.put(url, json=body_params)
            else:
                response = None  # or raise an exception

            return response.json() if response and response.status_code == 200 else None

        return dynamic_method


    def get_functions_list(self):
        return self.functions_list
            

class Manager:
    def __init__(
        self,  
        model="gpt-3.5-turbo-16k",
        debug=False
    ):
        self.client = OpenAI()
        self.model = model
        self.debug = debug
        self.assistant_id = None
        self.assistant = None
        self.functions = None
        
    def create_assistant(self, name, instructions, functions, file_ids):

        self.name = name
        self.instructions = instructions
        self.file_ids = file_ids
        self.functions = functions
 
        if self.debug: print(f"[Manager] - Creating new Assistant...")
        
        self.assistant = self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=functions.get_functions_list(),
            model=self.model,
            file_ids=file_ids
        )
        self.assistant_id = self.assistant.id   
        if self.debug: print(f"[Manager] - Created new Assistant with id: {self.assistant_id}")
        return self.assistant_id 


    def retrieve_assistant(self, name, instructions, functions, file_ids, assistant_id):

        self.name = name
        self.instructions = instructions
        self.file_ids = file_ids
        self.functions = functions

        if self.debug: print(f"[Manager] - Pulled assistant with assistant id: {assistant_id}")
        self.assistant_id = assistant_id
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        return self.assistant_id 

    def create_thread(self):
        return self.client.beta.threads.create()

    def add_message_to_thread(self, role, thread_id, content):
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )

    def run_assistant(self, thread_id, instructions):
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id,
            instructions=instructions
        )
        return run

    def get_latest_response(self, thread_id):
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)

        msg = messages.data[0]
        role = msg.role
        content = msg.content[0].text.value
        return {
            'role': role,
            'content':content
        }
            
    def wait_for_completion(self, thread_id, run_id):
        while True:
            time.sleep(5)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run_status.status == 'completed':
                if self.debug: print("[Manager] - Finished assistant execution!")
                break
            elif run_status.status == 'requires_action':
                if self.debug: print("Function Calling ...")
                self.call_required_functions(run_status.required_action.submit_tool_outputs.model_dump(), thread_id, run_id)
            else:
                if self.debug: print("[Manager] - Waiting for the Assistant to process...")


    def call_required_functions(self, required_actions,  thread_id, run_id):
        tool_outputs = []

        for action in required_actions["tool_calls"]:
            func_name = action['function']['name']
            arguments = json.loads(action['function']['arguments'])
            


            # Prepare the function to call
            func_to_call = getattr(self.functions, func_name, None)

            # Check if function exists
            if not func_to_call:
                if self.debug: print(f"[Manager] - Function does not exist: {func_name}")
                raise ValueError(f"[Manager] - Unknown function: {func_name}")

            if self.debug: print("[Manager] - Function called: ", func_name, arguments)

            # For functions that don't require special handling, arguments are used as-is
            # Dynamically call the function with unpacked arguments
            output = func_to_call(**arguments)
            tool_outputs.append({
                "tool_call_id": action['id'],
                "output": str(output)
            })

        if self.debug: print("[Manager] - Submitting outputs back to the Assistant...")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )



class Genbot():
    
    def __init__(
        self, 
        genbot_name, 
        openai_key,
        model = "gpt-3.5-turbo-1106",
        debug=False

    ):
        os.environ['OPENAI_API_KEY'] = openai_key

        self.assistant_id = None
        self.thread_id = None
        self.database = None
        self.functions = FunctionsBuilder()
        self.genbot_name = genbot_name
        self.manager = Manager(model, debug)
        self.debug = debug
      
    def load_swagger_functions(self, url, swagger_json):
        self.functions = FunctionsBuilder(url, swagger_json)

    def load_database(self, user, pwd, ip, table, db_type, client_encoding=None):
        self.database = DatabaseAdmin(user, pwd, ip, table, db_type, client_encoding)
        
    def initiate_new_genbot(
        self,
        assistant_id, 
        prompt, 
        instructions, 
    ):

        if assistant_id:
            self.assistant_id = self.manager.retrieve_assistant(
                name=self.genbot_name,
                instructions=prompt,
                functions=self.functions,
                file_ids=[], 
                assistant_id=assistant_id
            )
            self.final_instructions = f" {prompt} - {instructions} "
        else:
            self.assistant_id = self.manager.create_assistant(
                name=self.genbot_name,
                instructions=prompt,
                functions=self.functions,
                file_ids=[],
            )
            self.final_instructions = f" {prompt} -  {instructions} "     
    
    def restart_bot(self):
        self._new_thread()
    
    def run(self, question):
        if self.assistant_id:
            if not self.thread_id:
                self._new_thread()
            self.manager.add_message_to_thread(
                role="user",
                thread_id=self.thread_id,
                content=question
            )
            run = self.manager.run_assistant(thread_id=self.thread_id, instructions=self.final_instructions)
            self.manager.wait_for_completion(self.thread_id, run.id)
            message = self.manager.get_latest_response(self.thread_id)
            answer = message['content']

            if self.database:
                self.database.save_conversation(question=question, answer=answer, thread_id=self.thread_id)

            return answer
        else:
            print("[Genbot] - Genbot not initiated. Please run 'initiate_new_genbot' to start a new thread")
            return None
        
    def run_on_gradio(self):
        self.restart_bot()
        with gr.Blocks() as gradio_launch:
            chatbot = gr.Chatbot(label="Genbot test chat")
            msg = gr.Textbox()
            clear = gr.ClearButton([msg, chatbot])
            msg.submit(self._create_gradio_conversation, [msg, chatbot], [msg, chatbot])
        gradio_launch.launch()

    def _new_thread(self):
        if self.assistant_id:
            self.thread_id = self.manager.create_thread().id
            if self.debug:
                print(f"[Genbot] - started a new thread with id {self.thread_id }")
        else:
            print("[Genbot] - Genbot not initiated. Please run 'initiate_new_genbot' to start a new thread")


    def _create_gradio_conversation(self, query, chat_history):
        try: 
            result = self.run(query)
            chat_history.append((query, result))
            return "", chat_history
        except Exception as e:
            chat_history.append((query, e))
            return "", chat_history

        
        