from app.schemas import PostResponse
from fastapi import FastAPI , HTTPException
from app.schemas import PostCreate

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
def get_posts(limit: int = None):
    if limit is not None and limit <= len(list(text_posts)):
        return dict(list(text_posts.items())[:limit]) #need to return a DIcut 
    else:
        return text_posts


@app.get("/posts/{id}")
def get_post_by_id(id:int):
    if id not in text_posts:
        raise HTTPException(status_code=404 , detail="Post Not Found" )
    return text_posts[id]

@app.post("/posts") 
def create_post(post:PostCreate) -> PostResponse: # which type will it return 
    new_post = PostResponse(id=max(text_posts.keys())+1,title=post.title,content=post.content)
    text_posts[new_post.id] = new_post
    return new_post 

@app.delete("/posts/{id}")
def delet_post(id:int):
    if id not in text_posts:
        raise HTTPException(status_code=404 , detail="Post Not Found" )
    text_posts.pop(id)
    return {"message":f"The Post with id {id} has been deleted successfully"}