from flask import Flask, jsonify, request
 
app = Flask(__name__)
posts = []
 
 
@app.get("/posts")
def list_posts():
    return jsonify(posts)
 
 
@app.post("/posts")
def create_post():
    data = request.get_json()
    post = {"id": len(posts) + 1, "title": data["title"], "content": data["content"]}
    posts.append(post)
    return jsonify(post), 201
 
 
if __name__ == "__main__":
    app.run(debug=True)