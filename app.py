from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import joblib
import numpy as np
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'a3fcb1f947ac4e3f8b7e4f9a12c7f40e'  # Secret key for session management

# Connect to MongoDB
client = MongoClient("mongodb+srv://arjun:gadget123@cluster0.ybe05.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['gadget']
users_collection = db['users']
posts_collection = db['posts']

# Load the gadget addiction model
model = joblib.load('gadget_addiction_model6.pkl')

# Questions for the quiz
questions = [
    "Do you use your phone to click pictures of class notes?",
    "Do you buy books/access books from your mobile?",
    "When your phone’s battery dies out, do you run for the charger?",
    "Do you worry about losing your cell phone?",
    "Do you take your phone to the bathroom?",
    "Do you use your phone in any social gathering (parties)?",
    "How often do you check your phone without any notification?",
    "Do you check your phone just before going to sleep/just after waking up?",
    "Do you keep your phone right next to you while sleeping?",
    "Do you check emails, missed calls, texts during class time?",
    "Do you find yourself relying on your phone when things get awkward?",
    "Are you on your phone while watching TV or eating food?",
    "Do you have a panic attack if you leave your phone elsewhere?",
    "For how long do you use your phone for playing games?",
]

# Login page
@app.route('/')
def login():
    session.clear()
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    email = request.form['email']
    password = request.form['password']
    user = users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}, "password": password})
    if user:
        session['user'] = email
        session['name'] = user['name']
        session['is_admin'] = user.get('role') == 'admin'
        return redirect(url_for('home'))
    return render_template('login.html', error="Invalid credentials. Please try again.")

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if users_collection.find_one({"email": email}):
            return render_template('signup.html', error="User already exists. Please login.")
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "quiz_results": [],
            "role": "user"  # Default role
        })
        return redirect(url_for('login'))
    return render_template('signup.html')

# Home page
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['name'], is_admin=session.get('is_admin'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Quiz page
@app.route('/quiz')
def quiz():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', questions=questions)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'user' not in session:
            return jsonify({'status': 'error', 'message': 'User not logged in.'})

        user_email = session['user']
        user_input = [request.form[f'question{i}'] for i in range(1, 15)]
        user_input = list(map(int, user_input))  # Ensure inputs are Python ints
        input_data = np.array(user_input).reshape(1, -1)
        prediction = int(model.predict(input_data)[0])  # Convert numpy.int64 to Python int

        stages = {
            0: {
                "label": "Low Level of Gadget Addiction",
                "description": (
                    "Your gadget usage is within a healthy range. You are able to balance screen time "
                    "with other daily activities such as work, exercise, and social interactions."
                ),
                "suggestions": (
                    "Great job maintaining a balanced lifestyle! Continue to set boundaries for your gadget usage "
                    "and allocate dedicated time for offline activities like reading, hobbies, or outdoor exercises. "
                    "Ensure you practice digital mindfulness by being intentional about your screen time."
                ),
            },
            1: {
                "label": "High Level of Gadget Usage",
                "description": (
                    "You are using gadgets frequently, and it may be starting to affect aspects of your daily life, "
                    "such as reduced productivity, shorter attention spans, or disrupted sleep patterns."
                ),
                "suggestions": (
                    "Consider setting limits for your gadget usage, especially during study hours and before bedtime. "
                    "Incorporate gadget-free periods into your day, like during meals or while spending time with family. "
                    "Use tools like screen-time trackers or app blockers to monitor and manage your usage effectively."
                ),
            },
            2: {
                "label": "Severe Level of Gadget Addiction",
                "description": (
                    "Your gadget usage has become excessive and is significantly disrupting important areas of your life, "
                    "including personal relationships, mental well-being, and physical health."
                ),
                "suggestions": (
                    "It's time to take proactive steps to regain control. Reach out for support from a trusted friend, "
                    "family member, or a professional counselor. Create a structured plan to reduce screen time and replace it "
                    "with fulfilling offline activities like exercising, socializing, or learning new skills. "
                    "Consider a digital detox by taking regular breaks from gadgets and setting no-screen zones at home."
                ),
            },
        }

        result = stages.get(prediction, {"label": "Unknown", "description": "Unknown", "suggestions": "Try again."})

        # Save the quiz result in the database
        quiz_result = {
            "date": datetime.now(),  # Fixed the datetime call
            "answers": user_input,
            "prediction": prediction  # Store Python int
        }

        users_collection.update_one(
            {"email": user_email},
            {"$push": {"quiz_results": quiz_result}}
        )

        return render_template('result.html', result=result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

    
# Default avatars pool
default_avatars = [
    "/static/img.jpg",
    "/static/img3.jpg",
    "/static/img4.jpg",
    "/static/img5.jpg",
    "/static/img6.jpg",
    "/static/img7.jpeg",
    "/static/img8.jpg",
"/static/img9.jpg",
    "/static/img10.jpg",
"/static/img11.jpg",
    "/static/img12.jpg",
"/static/img13.jpeg",
    "/static/img14.jpg",
"/static/img15.jpg",
    "/static/img16.jpg",


]

# Function to get avatar for a user
def get_avatar_for_user(user):
    avatar_index = hash(user) % len(default_avatars)
    return default_avatars[avatar_index]



@app.route('/community')
def community_page():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Fetch posts from the database, sorted by the most recent
    posts = list(posts_collection.find().sort("timestamp", -1))
    for post in posts:
        post['_id'] = str(post['_id'])  # Convert ObjectId to string for HTML
        post['avatar_url'] = get_avatar_for_user(post["user"])  # Assign avatar

    return render_template('community.html', posts=posts)


# Route to create a new post
@app.route('/community/create_post', methods=['POST'])
def create_post():
    if 'user' not in session:
        return redirect(url_for('login'))

    content = request.form.get('content')
    if content:
        # Create a new post document
        post = {
            "user": session['name'],   # Get the name of the logged-in user
            "content": content,        # The content of the post
            "timestamp": datetime.now(),  # Current timestamp
            "likes": 0,                # Initial like count
            "comments": [],            # Empty comments array
            "liked_by": []             # List to track users who liked the post
        }
        posts_collection.insert_one(post)  # Save the post to the database
    return redirect(url_for('community_page'))

# Route to like a post
@app.route('/community/like_post/<post_id>', methods=['POST'])
def like_post(post_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    user = session['name']

    # Check if the user already liked the post
    post = posts_collection.find_one({"_id": ObjectId(post_id), "liked_by": user})
    if post:
        return jsonify({"status": "error", "message": "You have already liked this post."}), 400

    # Increment like count and add user to 'liked_by'
    posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"likes": 1}, "$push": {"liked_by": user}}
    )
    return jsonify({"status": "success", "message": "Post liked."})

@app.route('/community/comment_post/<post_id>', methods=['POST'])
def comment_post(post_id):
    comment_content = request.form.get('comment')
    user = session.get('name', 'Anonymous')

    if not comment_content:
        return redirect(request.referrer)

    posts_collection.update_one(
        {'_id': ObjectId(post_id)},
        {'$push': {'comments': {'user': user, 'content': comment_content}}}
    )

    return redirect(request.referrer)  # Stay on the same page


@app.route('/community/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user' not in session:
        return redirect('/login')  # Redirect to login if the user is not logged in

    user = session['name']
    post = posts_collection.find_one({"_id": ObjectId(post_id)})

    if not post:
        return redirect(request.referrer or '/community')  # Redirect if the post doesn't exist

    if post['user'] != user:
        return redirect(request.referrer or '/community')  # Redirect if unauthorized

    # Delete the post
    posts_collection.delete_one({"_id": ObjectId(post_id)})

    # Redirect back to the referring page (previous page) or to the community home if unavailable
    return redirect(request.referrer or '/community')


@app.route('/community/my_topics', methods=['GET'])
def get_my_topics():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    user = session['name']
    # Fetch posts created by the logged-in user
    user_posts = list(posts_collection.find({"user": user}).sort("timestamp", -1))
    for post in user_posts:
        post['_id'] = str(post['_id'])  # Convert ObjectId to string for JSON
        post['avatar_url'] = get_avatar_for_user(post["user"])  # Assign avatar

    return render_template('my_topics.html', posts=user_posts)


@app.route('/community/view_my_topic/<post_id>', methods=['GET'])
def view_my_topic(post_id):
    post = posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"status": "error", "message": "Post not found"}), 404

    post['_id'] = str(post['_id'])  # Convert ObjectId to string for JSON
    return jsonify({"status": "success", "post": post})

@app.route('/community/trending', methods=['GET'])
def get_trending_posts():
    posts = list(posts_collection.find())
    trending_posts = []
    current_time = datetime.now()

    for post in posts:
        post_age = (current_time - post["timestamp"]).total_seconds() / 3600 if "timestamp" in post else float('inf')
        likes = post.get("likes", 0)
        comments = len(post.get("comments", []))
        trending_score = 2 * likes + 3 * comments - 0.5 * post_age
        post['_id'] = str(post['_id'])  # Convert ObjectId to string for HTML rendering
        post['avatar_url'] = get_avatar_for_user(post["user"])  # Assign avatar
        post['trending_score'] = trending_score
        trending_posts.append(post)

    trending_posts = sorted(trending_posts, key=lambda x: x['trending_score'], reverse=True)[:10]

    return render_template('trending_topics.html', posts=trending_posts)


@app.route('/previous')
def previous_results():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    user = users_collection.find_one({"email": user_email})
    
    if user and 'quiz_results' in user:
        results = [
            {
                "date": result["date"],
                "answers": result["answers"],
                "prediction": result["prediction"]
            } 
            for result in user['quiz_results']
        ]
    else:
        results = []

    return render_template('previous.html', results=results, enumerate=enumerate)

@app.route('/faqs')
def faqs_page():
    return render_template('faqs.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    reported_posts = list(posts_collection.find({"reports": {"$exists": True, "$not": {"$size": 0}}}))
    for post in reported_posts:
        post['_id'] = str(post['_id'])

    return render_template('admin_dashboard.html', reported_posts=reported_posts)


@app.route('/community/report_post/<post_id>', methods=['POST'])
def report_post(post_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"reports": session['name']}}  # Add the reporter's name to the 'reports' field
    )
    return redirect(request.referrer)


@app.route('/admin/delete_reported_post/<post_id>', methods=['POST'])  # Renamed the function
def delete_reported_post(post_id):
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    posts_collection.delete_one({"_id": ObjectId(post_id)})
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/quiz_results')
def admin_quiz_results():
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    # Fetch all users with their quiz results
    users = users_collection.find({"quiz_results": {"$exists": True, "$not": {"$size": 0}}})
    quiz_data = []

    for user in users:
        for quiz in user["quiz_results"]:
            quiz_data.append({
                "username": user["name"],
                "email": user["email"],
                "prediction": quiz["prediction"],
                "date": quiz["date"]
            })

    # Sort by date (most recent first)
    quiz_data = sorted(quiz_data, key=lambda x: x["date"], reverse=True)

    return render_template('admin_quiz_results.html', quiz_data=quiz_data)



if __name__ == '__main__':
    app.run(debug=True)
