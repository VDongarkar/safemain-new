import tensorflow as tf
from preprocess import load_pothole_data  # Uses your previous code
from build_model import build_pothole_model

# 1. Load the Data
print("📦 Loading and preparing data...")
X, y_bbox, y_class = load_pothole_data()

# 2. Split into Training (80%) and Testing (20%)
from sklearn.model_selection import train_test_split
X_train, X_test, y_bbox_train, y_bbox_test, y_class_train, y_class_test = train_test_split(
    X, y_bbox, y_class, test_size=0.2, random_state=42
)

# 3. Get the Model
model = build_pothole_model()

# 4. START TRAINING
print("🚀 Training started. This may take a few minutes...")
history = model.fit(
    X_train,
    {'bbox': y_bbox_train, 'class': y_class_train},
    validation_data=(X_test, {'bbox': y_bbox_test, 'class': y_class_test}),
    epochs=10,          # Trained longer for realistic box predictions (approx 3 minutes on CPU)
    batch_size=16       # How many images it looks at before updating itself
)

# 5. Save the "Brain"
model.save('pothole_detector_model.h5')
print("✅ Training complete! Model saved as 'pothole_detector_model.h5'")