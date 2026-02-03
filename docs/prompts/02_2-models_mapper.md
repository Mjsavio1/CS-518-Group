Models and Mapper
Please create Pydantic models and a mapper

context
User fields:
- id: str
- email
- username
- password
- role: "admin" or "user"

Architecture:
Controller-Service-Repository.  Mapper maps between user input (dicts), Pydantic User model objects, and pymongo database documents.

Tools and Testing
Please use Pydantic for models.  The Repository will use pymongo.
Please implement unit tests using unittest.

Output

src/class_demo/

user_service/

models.py
mapper.py




tests/user_service/
* test_mapper.py

Please add init.py files as needed for unittest discovery.