test API for shop.

## **Dependencies**
### python > 13
### uv

***
*This API is used with postgresql*

## **How to use**
---
1. Clone this repository.
`git clone https://github.com/foxvirusMagister/shopBackaryAPI.git`
2. Download dependencies.
`uv sync`
3. Copy .env.example to .env and change values in it.
4. Start the API, replace port to yours, and ip if you want.
`uvicorn main:app --host 0.0.0.0 --port PORT`