import tensorflow as tf
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 1. Load the trained Brain
model = tf.keras.models.load_model('pothole_detector_model.h5', compile=False)
IMG_SIZE = 224

def predict_pothole(img_path):
    # Load and prep the image
    original_img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE)) / 255.0
    img_input = np.expand_dims(img_resized, axis=0)

    # 2. Get Prediction (xmin, ymin, xmax, ymax) and Class (0 or 1)
    bbox_pred, class_pred = model.predict(img_input)
    xmin, ymin, xmax, ymax = bbox_pred[0]
    confidence = class_pred[0][0]

    print(f"Pothole Confidence: {confidence:.4f}")
    if confidence < 0.2:
        print("❌ Rejection: No pothole signature detected in this image.")
        return

    # 3. Calculate Severity Logic
    width_box = xmax - xmin
    height_box = ymax - ymin
    area = width_box * height_box

    if area > 0.15:
        severity = "HIGH (Dangerous)"
        box_color = 'red'
    elif area > 0.05:
        severity = "MEDIUM (Needs Repair)"
        box_color = 'orange'
    else:
        severity = "LOW (Minor Crack)"
        box_color = 'lime'

    # 4. Show the Result with the BOX
    fig, ax = plt.subplots()
    ax.imshow(img_resized)
    
    # Create a Rectangle patch
    # Coordinates need to be multiplied by IMG_SIZE to scale from 0-1 to 224
    rect = patches.Rectangle(
        (xmin * IMG_SIZE, ymin * IMG_SIZE), 
        (xmax - xmin) * IMG_SIZE, 
        (ymax - ymin) * IMG_SIZE, 
        linewidth=2, edgecolor=box_color, facecolor='none'
    )
    
    # Add the patch to the Axes
    ax.add_patch(rect)
    plt.title(f"Severity: {severity}\nArea: {area:.4f}")
    plt.axis('off') # Hide the numbers on the side
    plt.savefig('prediction_result.png')
    print("✅ Result saved as prediction_result.png")

# Test it! (Ensure this filename exists in your folder)
predict_pothole('annotated-images/img-1.jpg')