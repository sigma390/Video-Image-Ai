from fastapi import FastAPI


app = FastAPI()



@app.get('/hello')
def hello():
    return "Hey its Python api" #json , hence we return either a dict or a Pydantic Object
