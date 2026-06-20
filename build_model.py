import tensorflow as tf
from tensorflow.keras import layers, models

def build_pothole_model():
    # Load pre-trained MobileNetV2 base
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # Freeze pre-trained weights
    
    # Global average pooling to reduce features to 1D
    x = layers.GlobalAveragePooling2D()(base_model.output)
    
    # Dense Layers (The "Decision" part)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(0.2)(x) # Prevents the model from "memorizing"
    
    # Bounding Box Output (4 numbers)
    bbox_output = layers.Dense(4, activation='sigmoid', name='bbox')(x)
    # Classification Output (1 number: 0 = background/diagram/solid, 1 = pothole)
    class_output = layers.Dense(1, activation='sigmoid', name='class')(x)
    
    model = models.Model(inputs=base_model.input, outputs=[bbox_output, class_output])
    
    # Compile with joint loss
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss={'bbox': 'mse', 'class': 'binary_crossentropy'},
        metrics={'bbox': 'mae', 'class': 'accuracy'}
    )
    
    return model

# Create and show the structure
model = build_pothole_model()
model.summary()