import os
import cv2
import numpy as np
import xml.etree.ElementTree as ET
import random

IMG_FOLDER = 'annotated-images'
IMG_SIZE = 224 

def generate_negative_image(img, xmin_norm, ymin_norm, xmax_norm, ymax_norm):
    h_orig, w_orig, _ = img.shape
    x1 = int(xmin_norm * w_orig)
    y1 = int(ymin_norm * h_orig)
    x2 = int(xmax_norm * w_orig)
    y2 = int(ymax_norm * h_orig)
    
    # Ensure coordinates are within bounds
    x1, x2 = max(0, min(x1, w_orig - 1)), max(0, min(x2, w_orig - 1))
    y1, y2 = max(0, min(y1, h_orig - 1)), max(0, min(y2, h_orig - 1))
    
    if x1 >= x2 or y1 >= y2:
        return cv2.blur(img, (25, 25))
        
    bw = x2 - x1
    bh = y2 - y1
    
    # Try to find a non-overlapping patch
    for _ in range(20):
        bx = random.randint(0, max(0, w_orig - bw - 1))
        by = random.randint(0, max(0, h_orig - bh - 1))
        
        # Check overlap
        overlap = not (bx + bw <= x1 or bx >= x2 or by + bh <= y1 or by >= y2)
        if not overlap:
            patch = img[by:by+bh, bx:bx+bw]
            neg_img = img.copy()
            neg_img[y1:y2, x1:x2] = patch
            return neg_img
            
    # Fallback: heavily blur the pothole region to erase its signature
    neg_img = img.copy()
    pothole_region = neg_img[y1:y2, x1:x2]
    if pothole_region.size > 0:
        blurred = cv2.blur(pothole_region, (35, 35))
        neg_img[y1:y2, x1:x2] = blurred
    return neg_img

def generate_synthetic_diagram():
    # White canvas
    img = np.ones((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8) * 255
    
    # Draw flowchart shapes (boxes, circles)
    for _ in range(random.randint(2, 5)):
        x1 = random.randint(10, 140)
        y1 = random.randint(10, 140)
        x2 = x1 + random.randint(35, 70)
        y2 = y1 + random.randint(25, 55)
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, random.randint(1, 2))
        
    # Draw connections (lines)
    for _ in range(random.randint(3, 7)):
        pt1 = (random.randint(10, 210), random.randint(10, 210))
        pt2 = (random.randint(10, 210), random.randint(10, 210))
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
        cv2.line(img, pt1, pt2, color, random.randint(1, 2))
        
    # Add random text labels (mimicking diagrams)
    for _ in range(random.randint(2, 5)):
        text = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=random.randint(3, 7)))
        org = (random.randint(10, 150), random.randint(15, 200))
        cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
    return img / 255.0

def generate_synthetic_texture():
    mode = random.choice(['solid', 'noise', 'gradient'])
    if mode == 'solid':
        color = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
        img = np.ones((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8) * color
    elif mode == 'noise':
        img = np.random.randint(0, 256, (IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
    else: # gradient
        img = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
        color1 = np.array([random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)])
        color2 = np.array([random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)])
        for y in range(IMG_SIZE):
            alpha = y / float(IMG_SIZE)
            img[y, :] = (1 - alpha) * color1 + alpha * color2
            
    return img / 255.0

def load_pothole_data():
    images = []
    bboxes = []  
    classes = []
    
    # Get all XML files
    xml_files = [f for f in os.listdir(IMG_FOLDER) if f.endswith('.xml')]
    print(f"🔄 Processing {len(xml_files)} potholes and generating clean road negative samples...")

    for xml_file in xml_files:
        try:
            # Parse XML
            tree = ET.parse(os.path.join(IMG_FOLDER, xml_file))
            root = tree.getroot()
            
            # Get dimensions
            width = int(root.find('size/width').text)
            height = int(root.find('size/height').text)
            
            # Get Bounding Box
            bbox = root.find('object/bndbox')
            xmin = int(bbox.find('xmin').text) / width
            ymin = int(bbox.find('ymin').text) / height
            xmax = int(bbox.find('xmax').text) / width
            ymax = int(bbox.find('ymax').text) / height
            
            # Load Image
            img_path = os.path.join(IMG_FOLDER, xml_file.replace('.xml', '.jpg'))
            img = cv2.imread(img_path)
            
            if img is not None:
                # 1. Positive Sample (Contains Pothole)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pos_img = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE))
                images.append(pos_img / 255.0)
                bboxes.append([xmin, ymin, xmax, ymax])
                classes.append(1.0) # 1.0 = Pothole
                
                # 2. Negative Sample (Pothole Erased)
                neg_img_raw = generate_negative_image(img, xmin, ymin, xmax, ymax)
                neg_img_rgb = cv2.cvtColor(neg_img_raw, cv2.COLOR_BGR2RGB)
                neg_img = cv2.resize(neg_img_rgb, (IMG_SIZE, IMG_SIZE))
                images.append(neg_img / 255.0)
                bboxes.append([0.0, 0.0, 0.0, 0.0]) # No bounding box
                classes.append(0.0) # 0.0 = Clean Road / No Pothole
                
        except Exception as e:
            print(f"⚠️ Skipping {xml_file}: {e}")

    # 3. Generate and append synthetic diagrams to prevent diagram false positives
    print(f"📈 Generating 150 synthetic negative diagrams...")
    for _ in range(150):
        images.append(generate_synthetic_diagram())
        bboxes.append([0.0, 0.0, 0.0, 0.0])
        classes.append(0.0)

    # 4. Generate and append solid color/noise textures to prevent solid screen false positives
    print(f"🎨 Generating 100 synthetic negative textures...")
    for _ in range(100):
        images.append(generate_synthetic_texture())
        bboxes.append([0.0, 0.0, 0.0, 0.0])
        classes.append(0.0)

    return np.array(images), np.array(bboxes), np.array(classes)

if __name__ == "__main__":
    X, y_bbox, y_class = load_pothole_data()
    print(f"✅ Preprocessing Test: Loaded {len(X)} samples ({len(y_class[y_class == 1.0])} positive, {len(y_class[y_class == 0.0])} negative).")