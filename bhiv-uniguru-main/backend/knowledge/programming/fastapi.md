# FastAPI

## Introduction
FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. Created by Sebastián Ramírez and released in 2018, it has quickly become one of the most popular backend frameworks in the Python ecosystem due to its speed, developer experience, and automatic documentation generation.

## Definition
FastAPI is an asynchronous web framework built on top of Starlette (for web routing and handling) and Pydantic (for data validation and serialization). It leverages Python type hints to declare request parameters and body payloads, which enables automatic data validation, serialization, and interactive API documentation.

## History
FastAPI was created by Sebastián Ramírez to solve problems he encountered while using other frameworks like Flask and Django. He wanted a framework that offered automatic data validation, excellent editor support (autocompletion), and performance comparable to NodeJS or Go. Finding no existing solution that met all these criteria, he built FastAPI by combining Starlette and Pydantic.

## Features
- **High Performance**: On par with NodeJS and Go (thanks to Starlette and Uvicorn). It is one of the fastest Python frameworks available.
- **Fast to Code**: Increases the speed to develop features by about 200% to 300%.
- **Fewer Bugs**: Reduces about 40% of human (developer) induced errors by leveraging type hints and automated validation.
- **Intuitive**: Great editor support. Completion everywhere. Less time debugging.
- **Easy**: Designed to be easy to use and learn. Less time reading docs.
- **Short**: Minimize code duplication. Multiple features from each parameter declaration.
- **Robust**: Get production-ready code. With automatic interactive documentation.
- **Standards-Based**: Based on (and fully compatible with) the open standards for APIs: OpenAPI (previously known as Swagger) and JSON Schema.

## Architecture
FastAPI's architecture relies heavily on two foundational libraries:
1. **Starlette**: Handles the web parts (routing, WebSockets, requests, responses). It provides the asynchronous foundation.
2. **Pydantic**: Handles the data parts (validation, serialization, documentation generation) using Python type hints.

FastAPI acts as the glue that ties these components together, providing a seamless developer experience with dependency injection and OpenAPI generation.

## Working
When a request hits a FastAPI application, the following happens:
1. **Routing**: FastAPI matches the URL path and HTTP method to the corresponding path operation function.
2. **Data Extraction & Validation**: It extracts path parameters, query parameters, headers, and the JSON body, then uses Pydantic to validate and convert them to the correct Python types based on the function's type hints.
3. **Dependency Injection**: It resolves any dependencies required by the endpoint (like database sessions or authentication checks).
4. **Execution**: The endpoint function executes the core business logic.
5. **Serialization**: The returned Python object is serialized back into a JSON response by Pydantic.

## Components
- **Path Operations**: The functions that handle requests for specific URLs (e.g., `@app.get("/")`).
- **Pydantic Models**: Classes used to define the structure and validation rules for request and response payloads.
- **Dependency Injection System**: A built-in system to declare shared logic, database connections, and authentication routines that endpoints can easily consume.
- **Swagger UI and ReDoc**: Built-in interactive documentation portals.
- **Uvicorn / Hypercorn**: ASGI servers required to serve the FastAPI application.

## Advantages
- **Exceptional Speed**: Asynchronous support allows it to handle thousands of concurrent requests efficiently.
- **Automatic Documentation**: Instantly generates Swagger UI and ReDoc pages without extra configuration.
- **Type Safety**: Heavy reliance on type hints means IDEs catch errors before runtime.
- **Built-in Validation**: Pydantic ensures data integrity out of the box.
- **Modern**: Fully embraces `async/await` syntax.

## Disadvantages
- **Relatively New Ecosystem**: While growing rapidly, it has fewer third-party plugins and mature extensions compared to Django.
- **Learning Curve**: Requires a solid understanding of asynchronous programming in Python and type hinting.
- **No Built-in ORM**: Unlike Django, FastAPI does not come with a built-in database ORM, requiring developers to choose and integrate their own (like SQLAlchemy).

## Real-world Applications
- **Microservices**: Ideal for building lightweight, fast microservices in a distributed architecture.
- **Machine Learning Serving**: The go-to framework for deploying machine learning models as APIs because it efficiently handles heavy computation and async requests.
- **Data Pipelines**: Building robust endpoints to ingest and validate large amounts of structured data.

## Code Examples

### 1. Minimal FastAPI Application
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

### 2. Path and Query Parameters
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

### 3. Request Body with Pydantic
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items/")
def create_item(item: Item):
    item_dict = item.dict()
    if item.tax:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict
```

## Best Practices
- **Use Asynchronous Handlers**: Define endpoints with `async def` when performing I/O bound operations (like database calls) to maximize throughput.
- **Organize with APIRouter**: Split large applications into multiple modules using `APIRouter` to maintain a clean project structure.
- **Leverage Dependencies**: Use FastAPI's dependency injection for repetitive tasks like verifying user tokens or opening database sessions.
- **Return Pydantic Models**: Define `response_model` in the route decorator to ensure outbound data is correctly filtered and serialized.

## Common Mistakes
- **Blocking the Event Loop**: Using synchronous I/O operations (like `time.sleep` or standard `requests`) inside an `async def` endpoint. This blocks the entire server. If you must use synchronous code, define the endpoint with `def` instead of `async def`.
- **Ignoring Type Hints**: Failing to provide type hints disables FastAPI's validation and documentation features.
- **Running in Production without Uvicorn Workers**: Forgetting to configure multiple workers or using Gunicorn as a process manager in production, limiting the app to a single CPU core.

## Interview Questions
1. **What is the difference between Starlette, Pydantic, and FastAPI?**
   *Answer*: Starlette provides the ASGI web routing and async capabilities. Pydantic provides data validation and serialization using type hints. FastAPI combines both and adds dependency injection, OpenAPI generation, and a cohesive developer experience.
2. **How does FastAPI handle synchronous endpoints?**
   *Answer*: If an endpoint is defined with `def` instead of `async def`, FastAPI runs it in an external threadpool. This ensures that a blocking synchronous operation does not freeze the main asynchronous event loop.
3. **What is Dependency Injection in FastAPI?**
   *Answer*: It's a way to declare things that an endpoint needs to work (e.g., database sessions, user auth). FastAPI automatically executes these dependencies and injects the results into the endpoint function, promoting code reuse and modularity.

## FAQs
- **Do I have to write async code to use FastAPI?**
  No, you can write standard synchronous code using `def`, and FastAPI will run it safely in a threadpool.
- **How do I run a FastAPI application?**
  You need an ASGI server like Uvicorn. Command: `uvicorn main:app --reload`.
- **Does FastAPI come with a database?**
  No, FastAPI is unopinionated about databases. You can use any library you prefer, such as SQLAlchemy, databases, or Tortoise ORM.

## Summary
FastAPI represents the modern era of Python web development. By leveraging Python type hints, it provides a highly productive developer experience with automatic validation and documentation. Its incredible performance makes it a strong competitor to frameworks in Go and Node.js. While it lacks the "batteries-included" approach of Django, its flexibility, speed, and design make it the premier choice for building APIs and microservices in Python.
