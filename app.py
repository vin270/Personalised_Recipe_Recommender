import http.client
import json
from urllib.parse import quote
import logging
import sqlite3

import numpy as np
import pandas as pd
from sklearn.calibration import LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf

from flask import Flask, render_template, request, jsonify, redirect, url_for, session

import sys

print(sys.executable)


app = Flask(__name__)


app.secret_key = 'b_5#y2L"F4Q8z\n\xec]/'
RAPIDAPI_KEY = '61c1af29aemsh3760981ad1bf8a6p1ec6b4jsna57898205928'

@app.route('/')
def home():
    # Check if the user is logged in
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend_recipe():
    user_input = request.form['user_input']  

    conn = http.client.HTTPSConnection("spoonacular-recipe-food-nutrition-v1.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com"
    }

    api_request_url = f"/recipes/complexSearch?query={quote(user_input)}&number=19"
    
    conn.request("GET", api_request_url, headers=headers)

    res = conn.getresponse()
    data = res.read()

    response_data = data.decode("utf-8")
    recipes = []  # Initialize an empty list to store recipe details
    error_message = None  # Initialize error_message as None
    
    try:
        response_json = json.loads(response_data)
        if 'results' in response_json:
            recipes = response_json['results']
        else:
            error_message = "No recipe recommendations found."
    except Exception as e:
        error_message = f"Error parsing API response: {e}"
        return render_template('index.html', error_message=error_message)
    
    if error_message:
        return render_template('index.html', error_message=error_message)
    else:
        return render_template('recipes.html', recipes=recipes)

@app.route('/recipe_details/<int:recipe_id>')
def recipe_details(recipe_id):
    conn = http.client.HTTPSConnection("spoonacular-recipe-food-nutrition-v1.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com"
    }

    # Fetch recipe details
    api_request_url_details = f"/recipes/{recipe_id}/information"
    conn.request("GET", api_request_url_details, headers=headers)
    res_details = conn.getresponse()
    data_details = res_details.read()
    response_data_details = data_details.decode("utf-8")

    recipe_details = {}
    error_message = None

    try:
        response_json_details = json.loads(response_data_details)
        recipe_details = response_json_details
    except Exception as e:
        error_message = f"Error parsing recipe details API response: {e}"
        return render_template('error.html', error_message=error_message)

    # Fetch instructions
    api_request_url_instructions = f"/recipes/{recipe_id}/analyzedInstructions"
    conn.request("GET", api_request_url_instructions, headers=headers)
    res_instructions = conn.getresponse()
    data_instructions = res_instructions.read()
    response_data_instructions = data_instructions.decode("utf-8")

    instructions = []
    try:
        response_json_instructions = json.loads(response_data_instructions)
        if response_json_instructions and 'steps' in response_json_instructions[0]:
            instructions = response_json_instructions[0]['steps']
    except Exception as e:
        error_message = f"Error parsing instructions API response: {e}"
        return render_template('error.html', error_message=error_message)

    # Extract ingredients with quantities from the extendedIngredients field
    ingredients_with_quantities = []
    if 'extendedIngredients' in recipe_details:
        for ingredient in recipe_details['extendedIngredients']:
            name = ingredient.get('original', ingredient.get('name'))
            if name:
                ingredients_with_quantities.append(name)

    total_likes = get_total_likes_for_recipe(recipe_id)
    return render_template('recipe_details.html', recipe_details=recipe_details, instructions=instructions, ingredients_with_quantities=ingredients_with_quantities, total_likes=total_likes)



@app.route('/random_recipe', methods=['GET'])
def random_recipe():
    conn = http.client.HTTPSConnection("spoonacular-recipe-food-nutrition-v1.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com"
    }

    api_request_url = "/recipes/random"

    conn.request("GET", api_request_url, headers=headers)

    res = conn.getresponse()
    data = res.read()

    # Parse the response data (JSON)
    response_data = data.decode("utf-8")
    recipe = {}  # Initialize an empty dictionary to store the random recipe details
    error_message = None  # Initialize error_message as None
    
    try:
        # Attempt to parse JSON data
        response_json = json.loads(response_data)
        recipe = response_json['recipes'][0] if 'recipes' in response_json else {}
    except Exception as e:
        error_message = f"Error parsing API response: {e}"
        return render_template('error.html', error_message=error_message)
    
    if not recipe:
        error_message = "No random recipe found."
        return render_template('error.html', error_message=error_message)

    # Get detailed information about the random recipe
    recipe_id = recipe.get('id', 0)
    api_request_url_details = f"/recipes/{recipe_id}/information"
    conn.request("GET", api_request_url_details, headers=headers)
    res_details = conn.getresponse()
    data_details = res_details.read()
    response_data_details = data_details.decode("utf-8")


    recipe_details = {}
    try:
        response_json_details = json.loads(response_data_details)
        recipe_details = response_json_details
    except Exception as e:
        error_message = f"Error parsing recipe details API response: {e}"
        return render_template('error.html', error_message=error_message)

    # Get instructions for the random recipe
    api_request_url_instructions = f"/recipes/{recipe_id}/analyzedInstructions"
    conn.request("GET", api_request_url_instructions, headers=headers)
    res_instructions = conn.getresponse()
    data_instructions = res_instructions.read()
    response_data_instructions = data_instructions.decode("utf-8")

    instructions = []
    try:
        response_json_instructions = json.loads(response_data_instructions)
        if response_json_instructions:
            instructions = response_json_instructions[0].get('steps', [])
    except Exception as e:
        error_message = f"Error parsing instructions API response: {e}"
        return render_template('error.html', error_message=error_message)
    
    ingredients_with_quantities = []
    if 'extendedIngredients' in recipe_details:
        for ingredient in recipe_details['extendedIngredients']:
            name = ingredient.get('original', ingredient.get('name'))
            if name:
                ingredients_with_quantities.append(name)

    return render_template('recipe_details.html', recipe_details=recipe_details, instructions=instructions, ingredients_with_quantities=ingredients_with_quantities)


import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

# Initialize SQLite database
conn = sqlite3.connect('user_profiles.db')
c = conn.cursor()

# Create users table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS users (
             id INTEGER PRIMARY KEY,
             username TEXT NOT NULL,
             password TEXT NOT NULL,
             email TEXT NOT NULL,
             allergens TEXT
             )''')
conn.commit()

conn = sqlite3.connect('saved_recipes.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS saved_recipes (
             id INTEGER PRIMARY KEY,
             user_id INTEGER NOT NULL,
             recipe_title TEXT NOT NULL,
             recipe_id INTEGER NOT NULL,
             FOREIGN KEY (user_id) REFERENCES users (id)
             )''')
conn.commit()

# Fetch all rows from the saved_recipes table
c.execute("SELECT * FROM saved_recipes")
rows = c.fetchall()

# Print the column names
print("ID\tUser ID\tRecipe title\tRecipe_ID")
print("---------------------------------")

# Print the content of the table
for row in rows:
    id, user_id, recipe_title, recipe_id = row
    print(f"{id}\t{user_id}\t{recipe_title}\t{recipe_id}")

# Close the connection
conn.close()
# Close the connection
conn.close()


# Routes for login, registration, profile, and recipe management
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Authenticate user
        if authenticate_user(username, password):
            session['username'] = username
            return redirect(url_for('profile'))
        else:
            return render_template('login.html', message='Invalid username or password')
    return render_template('login.html', message='')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        allergens = request.form['allergens']
        # Register new user
        if register_user(username, password, email, allergens):
            session['username'] = username
            return redirect(url_for('profile'))
        else:
            return render_template('register.html', message='Username or email already exists')
    return render_template('register.html', message='')

from flask import render_template

@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        user_id = get_user_id(username)  # Assuming you have implemented this function
        if user_id is not None:
            saved_recipes = get_saved_recipes(user_id)
            liked_recipes = get_liked_recipes(user_id)  # Fetch liked recipes
            return render_template('profile.html', username=username, saved_recipes=saved_recipes, liked_recipes=liked_recipes)
        else:
            return render_template('profile.html', username=username, saved_recipes=[], liked_recipes=[])  # No recipes found for the user
    return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

# Function to authenticate user
def authenticate_user(username, password):
    conn = sqlite3.connect('user_profiles.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return True if user else False

# Function to register new user
def register_user(username, password, email, allergens):
    conn = sqlite3.connect('user_profiles.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    user = c.fetchone()
    if user:
        conn.close()
        return False
    else:
        c.execute("INSERT INTO users (username, password, email, allergens) VALUES (?, ?, ?, ?)",
                  (username, password, email, allergens))
        conn.commit()
        conn.close()
        return True

def get_user_id(username):
    try:
        conn = sqlite3.connect('user_profiles.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()
        if user_id:
            return user_id[0]  # Return the user ID
        else:
            return None  # Return None if the user is not found
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
        return None
    finally:
        conn.close()


# Function to save user recipe to the database
def save_user_recipe_to_database(user_id, recipe_title, recipe_id):
    conn = sqlite3.connect('saved_recipes.db')
    c = conn.cursor()
    
    # Check if the user has already saved the recipe
    c.execute("SELECT * FROM saved_recipes WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
    existing_recipe = c.fetchone()
    if existing_recipe:
        # User has already saved the recipe, return without saving again
        conn.close()
        return False
    
    # Insert new recipe record
    c.execute("INSERT INTO saved_recipes (user_id, recipe_title, recipe_id) VALUES (?, ?, ?)", (user_id, recipe_title, recipe_id))
    conn.commit()
    conn.close()
    return True


def get_saved_recipes(user_id):
    try:
        conn = sqlite3.connect('saved_recipes.db')
        c = conn.cursor()
        c.execute("SELECT recipe_title, recipe_id FROM saved_recipes WHERE user_id = ?", (user_id,))
        rows = c.fetchall()

        # Convert rows to a list of dictionaries
        saved_recipes = [{'recipe_id': row[1], 'title': row[0]} for row in rows]
        
        return saved_recipes
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
        return []
    finally:
        conn.close()



import logging

@app.route('/save_user_recipe', methods=['POST'])
def save_recipe():
    if 'username' in session:
        username = session['username']
        recipe_title = request.form.get('recipe_title')
        recipe_id = request.form.get('recipe_id')

        if not recipe_title or not recipe_id:
            return render_template('error.html', error_message="Invalid recipe data.")

        try:
            # Get user ID from the database using the username
            user_id = get_user_id(username)
            if user_id is None:
                return render_template('error.html', error_message="User not found.")

            # Save recipe to the database
            save_user_recipe_to_database(user_id, recipe_title, recipe_id)

            # Redirect to the profile page after saving
            return redirect(url_for('profile'))
        except sqlite3.IntegrityError as e:
            logging.error(f"IntegrityError occurred: {str(e)}")
            return render_template('error.html', error_message="Error saving recipe. Please try again.")
        except Exception as e:
            logging.error(f"Database error occurred: {str(e)}")
            return render_template('error.html', error_message="An error occurred while saving the recipe.")
    else:
        return redirect(url_for('login'))
    

def like_recipe_for_user(user_id, recipe_title, recipe_id):
    conn = sqlite3.connect('liked_recipes.db')
    c = conn.cursor()

    # Check if the user has already liked the recipe
    c.execute("SELECT * FROM liked_recipes WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
    existing_like = c.fetchone()
    if existing_like:
        # User has already liked the recipe, return without adding a new like
        conn.close()
        return
    
    # Insert new like record
    c.execute("INSERT INTO liked_recipes (user_id, recipe_title, recipe_id) VALUES (?, ?, ?)", (user_id, recipe_title, recipe_id))
    conn.commit()
    conn.close()

@app.route('/like_recipe', methods=['POST'])
def like_recipe():
    if 'username' in session:
        username = session['username']
        recipe_title = request.form.get('recipe_title')
        recipe_id = request.form.get('recipe_id')


        if not recipe_id:
            return render_template('error.html', error_message="Invalid recipe ID.")

        try:
            # Get user ID from the database using the username
            user_id = get_user_id(username)
            if user_id is None:
                return render_template('error.html', error_message="User not found.")

            # Like recipe and store in the database
            like_recipe_for_user(user_id, recipe_title, recipe_id)

            # Redirect to the profile page after liking the recipe
            return redirect(url_for('profile'))
        except Exception as e:
            logging.error(f"Error occurred while liking recipe: {str(e)}")
            return render_template('error.html', error_message="An error occurred while liking the recipe.")
    else:
        return redirect(url_for('login'))

def get_total_likes_for_recipe(recipe_id):
    conn = sqlite3.connect('liked_recipes.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM liked_recipes WHERE recipe_id = ?", (recipe_id,))
    total_likes = c.fetchone()[0]
    conn.close()
    return total_likes

conn = sqlite3.connect('liked_recipes.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS liked_recipes (
             id INTEGER PRIMARY KEY,
             user_id INTEGER NOT NULL,
             recipe_title TEXT NOT NULL,
             recipe_id INTEGER NOT NULL,
             FOREIGN KEY (user_id) REFERENCES users (id),
             FOREIGN KEY (recipe_id) REFERENCES recipes (id)
             )''')
conn.commit()

# Function to get liked recipes for a user
def get_liked_recipes(user_id):
    try:
        conn = sqlite3.connect('liked_recipes.db')
        c = conn.cursor()
        c.execute("SELECT recipe_title, recipe_id FROM liked_recipes WHERE user_id = ?", (user_id,))
        rows = c.fetchall()

        # Convert rows to a list of dictionaries
        liked_recipes = [{'recipe_id': row[1], 'title': row[0]} for row in rows]
        
        return liked_recipes
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
        return []
    finally:
        conn.close()

def fetch_similar_recipes(recipe_title):
    conn = http.client.HTTPSConnection("spoonacular-recipe-food-nutrition-v1.p.rapidapi.com")
    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com"
    }
    api_request_url = f"/recipes/complexSearch?query={quote(recipe_title)}&number=5"
    conn.request("GET", api_request_url, headers=headers)
    res = conn.getresponse()
    data = res.read()
    response_data = data.decode("utf-8")
    try:
        response_json = json.loads(response_data)
        if 'results' in response_json:
            # Extract recipe details from the response
            similar_recipes = [{'title': recipe['title'], 'recipe_id': recipe['id']} for recipe in response_json['results']]
            return similar_recipes
    except Exception as e:
        print(f"Error fetching similar recipes: {e}")
        return []

@app.route('/AIrecommendation', methods=['GET'])
def ai_recommendation():
    if 'username' in session:
        username = session['username']
        user_id = get_user_id(username)  # Get the user ID
        
        # Fetch saved recipes for the user from the database
        saved_recipes = get_saved_recipes(user_id)
        
        # If no saved recipes, return empty recommendations
        if not saved_recipes:
            return render_template('AIrecommendation.html', username=username, recommended_recipes=[])

        # Prepare a list to store recommended recipes
        recommended_recipes = []

        # Loop through each saved recipe to fetch similar recipes
        for recipe in saved_recipes:
            recipe_title = recipe['title']  # Change 'recipe_title' to 'title'
            recipe_id = recipe['recipe_id']
            # Query the Spoonacular API for similar recipes
            similar_recipes = fetch_similar_recipes(recipe_title)
            # Filter out saved recipes from the similar recipes
            filtered_recipes = [similar_recipe for similar_recipe in similar_recipes if similar_recipe['title'] != recipe_title]
            # Add the filtered similar recipes to the recommended_recipes list
            recommended_recipes.extend(filtered_recipes)
        
        return render_template('AIrecommendation.html', username=username, recommended_recipes=recommended_recipes)
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True) 


