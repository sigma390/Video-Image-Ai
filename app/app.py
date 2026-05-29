from fastapi import FastAPI


app = FastAPI()



@app.get('/hello')
def hello():
    return {"messsage":"Hello here"}#json , hence we return either a dict or a Pydantic Object
