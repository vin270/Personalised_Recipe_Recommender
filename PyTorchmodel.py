import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Load the saved recipes dataset from the database
conn = sqlite3.connect('saved_recipes.db')
query = "SELECT user_id, recipe_id FROM saved_recipes"
df = pd.read_sql_query(query, conn)

# Encode user_id and recipe_id using LabelEncoder
encoder = LabelEncoder()
df['user_id'] = encoder.fit_transform(df['user_id'])
df['recipe_id'] = encoder.fit_transform(df['recipe_id'])

# Split the dataset into train and test sets
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

# Define the PyTorch model
class RecommendationModel(nn.Module):
    def __init__(self, num_users, num_recipes, embedding_dim=50):
        super(RecommendationModel, self).__init__()
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.recipe_embedding = nn.Embedding(num_recipes, embedding_dim)
        self.fc = nn.Linear(embedding_dim * 2, 1)
        
    def forward(self, user, recipe):
        user_embedded = self.user_embedding(user)
        recipe_embedded = self.recipe_embedding(recipe)
        concatenated = torch.cat((user_embedded, recipe_embedded), dim=1)
        output = torch.sigmoid(self.fc(concatenated))
        return output

# Initialize the model
model = RecommendationModel(num_users=len(df['user_id'].unique()), num_recipes=len(df['recipe_id'].unique()))

# Define loss function and optimizer
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Convert dataframe to PyTorch tensors
train_user_ids = torch.LongTensor(train_df['user_id'].values)
train_recipe_ids = torch.LongTensor(train_df['recipe_id'].values)
train_labels = torch.FloatTensor([1] * len(train_df))

# Train the model
num_epochs = 10
for epoch in range(num_epochs):
    optimizer.zero_grad()
    outputs = model(train_user_ids, train_recipe_ids)
    loss = criterion(outputs.squeeze(), train_labels)
    loss.backward()
    optimizer.step()
    print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item()}')

# Save the trained model
torch.save(model.state_dict(), 'recommendation_model.pth')
