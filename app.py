from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import math
import sqlite3
import cv2  # Added to draw bounding boxes on images
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image as tf_image
from geopy.geocoders import Nominatim
from datetime import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

geolocator = Nominatim(user_agent="safepath_monitoring_v3", timeout=3)
DATABASE_NAME = 'safepath.db'
DUPLICATE_THRESHOLD_METERS = 5.0 

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # FORCE RESET: Clears table definition to fix structural mismatches cleanly
    cursor.execute("DROP TABLE IF EXISTS potholes")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS potholes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            severity TEXT NOT NULL,
            area TEXT NOT NULL,
            reporter_name TEXT NOT NULL,
            reporter_phone TEXT NOT NULL,
            image_url TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            xmin REAL, ymin REAL, xmax REAL, ymax REAL
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ SQLite Database Rebuilt Cleanly With Uniform Columns")

init_db()

MODEL_PATH = 'pothole_detector_model.h5'
try:
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print("✅ CNN Bounding Box Model Loaded Successfully")
except Exception as e:
    print(f"❌ Error Loading Model: {e}")

UPLOAD_FOLDER = os.path.join('static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

@app.route('/api/reports/citizen', methods=['GET'])
def get_citizen_reports():
    phone = request.args.get('phone')
    if not phone:
        return jsonify({'status': 'error', 'message': 'Missing phone parameter'})
    
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM potholes WHERE reporter_phone = ? ORDER BY id DESC", (phone,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({'status': 'success', 'data': [dict(row) for row in rows]})

@app.route('/api/reports/all', methods=['GET'])
def get_all_reports():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM potholes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify({'status': 'success', 'data': [dict(row) for row in rows]})

# --- ROUTE: UPDATE STATUS ENDPOINT ---
@app.route('/api/reports/update-status', methods=['POST'])
def update_status():
    report_id = request.json.get('id')
    new_status = request.json.get('status') 

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT reporter_phone, reporter_name, area FROM potholes WHERE id = ?", (report_id,))
    record = cursor.fetchone()

    if not record:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Report record not found'}), 404

    phone, name, area = record
    cursor.execute("UPDATE potholes SET status = ? WHERE id = ?", (new_status, report_id))
    conn.commit()
    conn.close()

    print(f"\n📱 [SMS GATEWAY NOTIFICATION SENT]")
    print(f"To: {phone} ({name})")
    print(f"Message: Hello {name}, the pothole hazard you reported at {area} has been successfully updated to {new_status}. Thank you for your support!\n")

    return jsonify({'status': 'success', 'message': f'Status successfully updated to {new_status}.'})

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image uploaded'})

    img_file = request.files['image']
    lat_raw = request.form.get('latitude')
    lng_raw = request.form.get('longitude')
    name = request.form.get('name', 'Anonymous Citizen')
    phone = request.form.get('phone', 'Unknown Phone')

    if not lat_raw or not lng_raw:
        return jsonify({'status': 'error', 'message': 'Location data missing'})

    current_lat, current_lng = float(lat_raw), float(lng_raw)
    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(img_file.filename)
    if not safe_filename:
        import uuid
        ext = os.path.splitext(img_file.filename)[1] or '.jpg'
        safe_filename = f"upload_{uuid.uuid4().hex[:8]}{ext}"
    final_filename = "processed_" + safe_filename

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude, severity, area, image_url FROM potholes")
    for row in cursor.fetchall():
        is_same_file = final_filename in row[4]
        is_close_by = calculate_distance(current_lat, current_lng, row[0], row[1]) <= DUPLICATE_THRESHOLD_METERS
        
        if is_same_file or is_close_by:
            conn.close()
            return jsonify({
                'status': 'duplicate',
                'message': 'This pothole has already been registered nearby.',
                'severity': row[2], 'area': row[3]
            }), 200

    temp_path = os.path.join(UPLOAD_FOLDER, "temp_" + safe_filename)
    img_file.save(temp_path)

    try:
        img = tf_image.load_img(temp_path, target_size=(224, 224))
        img_array = tf_image.img_to_array(img)
        img_input = np.expand_dims(img_array, axis=0) / 255.0

        bbox_pred, class_pred = model.predict(img_input)
        xmin, ymin, xmax, ymax = map(float, bbox_pred[0])
        confidence = float(class_pred[0][0])
        area_size = abs(xmax - xmin) * abs(ymax - ymin)

        print(f"Prediction Confidence: {confidence:.4f}, Area Size: {area_size:.4f}")

        # REJECTION CRITERIA: Confidence under 20%
        if confidence < 0.20: 
            os.remove(temp_path) 
            conn.close() 
            return jsonify({
                'status': 'rejected', 
                'message': 'Our AI model did not detect any pothole signatures in this image.'
            }), 200

        if area_size > 0.15:
            severity, color_box = "High", (0, 0, 255) 
        elif area_size > 0.05:
            severity, color_box = "Medium", (0, 165, 255) 
        else:
            severity, color_box = "Low", (0, 255, 0) 

        source_img = cv2.imread(temp_path)
        h_orig, w_orig, _ = source_img.shape
        start_point = (int(xmin * w_orig), int(ymin * h_orig))
        end_point = (int(xmax * w_orig), int(ymax * h_orig))
        
        cv2.rectangle(source_img, start_point, end_point, color_box, 4)
        final_path = os.path.join(UPLOAD_FOLDER, final_filename)
        cv2.imwrite(final_path, source_img)
        os.remove(temp_path) 

        area_name = "Unknown Region"
        try:
            location = geolocator.reverse(f"{current_lat}, {current_lng}", timeout=5)
            if location:
                addr = location.raw.get('address', {})
                area_name = addr.get('suburb') or addr.get('neighbourhood') or addr.get('road') or "PCMC Region"
        except Exception:
            area_name = "Location Service Busy"

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        relative_url = f'/static/uploads/{final_filename}'

        cursor.execute('''
            INSERT INTO potholes (latitude, longitude, severity, area, reporter_name, reporter_phone, image_url, timestamp, status, xmin, ymin, xmax, ymax)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (current_lat, current_lng, severity, area_name, name, phone, relative_url, current_time, 'Pending', xmin, ymin, xmax, ymax))
        
        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success', 'severity': severity, 'area': area_name,
            'image_url': relative_url, 'timestamp': current_time, 'status_repair': 'Pending'
        }), 200
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/reports/reset-database', methods=['POST'])
def reset_database():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM potholes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='potholes'")
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Database completely flushed.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)