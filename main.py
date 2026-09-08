import uvicorn 

if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000 , reload=True ) # app.app folder and file inside that Folder host:Domain port : which port 
    