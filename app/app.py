from fastapi import FastAPI , HTTPException


app = FastAPI()

text_posts = {
    1: {
        "title": "My first post",
        "content": "Hello from FastAPI!"
    },
    2: {
        "title": "Learning FastAPI",
        "content": "FastAPI is great for building APIs."
    },
    3: {
        "title": "Python",
        "content": "Python makes backend development fun."
    }
}


@app.get("/posts")
def get_posts():
    return text_posts


@app.get("/posts/{id}")
def get_post_by_id(id:int):
    if id not in text_posts:
        return HTTPException(status_code=404 , detail="Post Not Found" )
    return text_posts[id]