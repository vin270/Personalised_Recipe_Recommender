import sqlite3
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Step 1: Fetch saved recipes data from the database
def fetch_saved_recipes():
    conn = sqlite3.connect('saved_recipes.db')
    c = conn.cursor()
    c.execute("SELECT user_id, recipe_title, recipe_id FROM saved_recipes")
    rows = c.fetchall()
    conn.close()
    return rows

# Step 2: Preprocess saved recipes data
def preprocess_data(saved_recipes):
    # Convert fetched data into a DataFrame
    df = pd.DataFrame(saved_recipes, columns=['user_id', 'recipe_title', 'recipe_id'])
    
    # Encode recipe_title and recipe_id using LabelEncoder
    label_encoder = LabelEncoder()
    df['recipe_title'] = label_encoder.fit_transform(df['recipe_title'])
    df['recipe_id'] = label_encoder.fit_transform(df['recipe_id'])
    
    # Split data into features and labels
    X = df[['user_id', 'recipe_title']]
    y = df['recipe_id']
    
    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    return X_train, X_test, y_train, y_test

# Step 3: Define and train TensorFlow model
def train_model(X_train, y_train):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(2,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    model.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.2)
    
    return model

# Fetch saved recipes data
saved_recipes_data = fetch_saved_recipes()

# Preprocess data
X_train, X_test, y_train, y_test = preprocess_data(saved_recipes_data)

# Train the TensorFlow model
trained_model = train_model(X_train, y_train)
