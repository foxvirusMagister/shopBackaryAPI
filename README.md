# API for College project

## **Dependencies**
### python > 13
### uv

*This API is used with postgresql*

## **How to use**
1. Clone this repository.
`git clone https://github.com/foxvirusMagister/shopBackaryAPI.git`
2. Download dependencies.
`uv sync`
3. Copy .env.example to .env and change values in it.
4. Start the API, replace port to yours, and ip if you want.
`uvicorn main:app --host 0.0.0.0 --port PORT`

## **How to use dockerimage**
1. Clone this repository.
`git clone https://github.com/foxvirusMagister/shopBackaryAPI.git`
2. Build docker image
`docker build -t NAME .`
3. Copy and configury .env.example file to .env
4. Run container
`docker run -p 9000:8080 --env-file .env NAME --host 0.0.0.0 --port 8080`
or
`docker run --env-file .env NAME -p 9000:9000`
5. Open http://localhost:9000/products or something like http://YourIp:9000/products

*-p {host port:container port}*
*--host {listening ip}*
*--port {container port}*
