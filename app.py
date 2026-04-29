import cv2
import numpy as np
import os
import time
import threading
import base64
from datetime import datetime
from insightface.app import FaceAnalysis

# Flask untuk koneksi ke UI
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

# =========================
# FLASK APP SETUP
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# INIT MODEL
# =========================
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))

# Default ke kamera 0 (kamera PC/Laptop)
current_cam_id = 0

def setup_camera(cam_id):
    # Menggunakan kamera PC lokal (CAP_DSHOW mempercepat load kamera di Windows)
    new_cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return new_cap

cap = setup_camera(current_cam_id)
cap_lock = threading.Lock()

base_path = "known_faces"
unknown_path = "unknown_detected"
os.makedirs(base_path, exist_ok=True)
os.makedirs(unknown_path, exist_ok=True)

# =========================
# UTILS
# =========================
def cosine(a, b):
    a = a / (np.linalg.norm(a) + 1e-6)
    b = b / (np.linalg.norm(b) + 1e-6)
    return np.dot(a, b)

def calculate_blur_score(face_img):
    if face_img is None or face_img.size == 0: return 0, 0
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return score, score

def get_face_crop(frame, bbox):
    x1, y1, x2, y2 = map(int, bbox)
    h, w = frame.shape[:2]
    margin_w = int((x2 - x1) * 0.2)
    margin_h = int((y2 - y1) * 0.2)
    nx1, ny1 = max(0, x1 - margin_w), max(0, y1 - margin_h)
    nx2, ny2 = min(w, x2 + margin_w), min(h, y2 + margin_h)
    return frame[ny1:ny2, nx1:nx2]

def get_direction(face):
    kps = face.kps
    dist_l = np.linalg.norm(kps[2] - kps[0])
    dist_r = np.linalg.norm(kps[2] - kps[1])
    ratio_h = dist_l / (dist_r + 1e-6)
    eye_y = (kps[0][1] + kps[1][1]) / 2
    mouth_y = (kps[3][1] + kps[4][1]) / 2
    nose_y = kps[2][1]
    ratio_v = abs(nose_y - eye_y) / (abs(nose_y - mouth_y) + 1e-6)
    if ratio_h > 1.6: return "RIGHT"
    if ratio_h < 0.6: return "LEFT"
    if ratio_v < 0.4: return "UP"
    if ratio_v > 1.2: return "DOWN"
    return "CENTER"

def write_daily_log(name, status, action):
    now = datetime.now()
    main_log_folder = "logs"
    month_dir = os.path.join(main_log_folder, f"Log_{now.strftime('%Y-%m')}")
    file_name = f"{now.strftime('%Y-%m-%d')}.txt"
    if not os.path.exists(month_dir):
        os.makedirs(month_dir)
    file_path = os.path.join(month_dir, file_name)
    timestamp = now.strftime("%H:%M:%S")
    with open(file_path, "a") as f:
        f.write(f"[{timestamp}] {name} - {status} - {action}\n")
    log_buffer.append({
        "time": timestamp,
        "name": name,
        "status": status,
        "action": action
    })
    if len(log_buffer) > 200:
        log_buffer.pop(0)

# =========================
# DATABASE MANAGER
# =========================
known_db = {}
unknown_db = {}
unknown_best_blur_scores = {}

def load_all_db():
    global known_db, unknown_db, unknown_best_blur_scores
    known_db = {}
    if os.path.exists(base_path):
        for person in os.listdir(base_path):
            folder = os.path.join(base_path, person)
            if not os.path.isdir(folder): continue
            embs = [np.load(os.path.join(folder, f)) for f in os.listdir(folder) if f.endswith(".npy")]
            if embs: known_db[person] = np.array(embs)

    unknown_db = {}
    unknown_best_blur_scores = {}
    if os.path.exists(unknown_path):
        for person in os.listdir(unknown_path):
            folder = os.path.join(unknown_path, person)
            if not os.path.isdir(folder): continue
            embs = [np.load(os.path.join(folder, f)) for f in os.listdir(folder) if f.endswith(".npy")]
            if embs: unknown_db[person] = np.array(embs)
            img_path = os.path.join(folder, "face.jpg")
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                score, _ = calculate_blur_score(img)
                unknown_best_blur_scores[person] = score

load_all_db()

# =========================
# STATE & CONFIG
# =========================
mode = "IDLE"
frame_skip = 2
frame_id = 0
last_faces = []
last_unknown_check = 0
capture_delay = 5
MIN_FACE_SIZE = 25
recognition_buffer = {}
active_sessions = {}
COOLDOWN_KELUAR = 3

scan_name = ""
save_dir = ""
captured = set()
buffer_dir = []
counter = {}

log_buffer = []           
latest_frame_jpg = None   
frame_lock = threading.Lock()
ui_command = None         
ui_command_lock = threading.Lock()

state_for_ui = {
    "mode": "IDLE",
    "cam_id": current_cam_id,
    "faces": [],
    "active_sessions": {},
    "known_db": [],
    "unknown_db": [],
    "scan_progress": {
        "name": "",
        "captured": [],
        "current_dir": "",
        "counter": 0
    }
}

def update_state_for_ui():
    state_for_ui["mode"] = mode
    state_for_ui["cam_id"] = current_cam_id
    state_for_ui["active_sessions"] = {k: v for k, v in active_sessions.items()}
    state_for_ui["known_db"] = list(known_db.keys())
    state_for_ui["unknown_db"] = list(unknown_db.keys())
    state_for_ui["scan_progress"] = {
        "name": scan_name,
        "captured": list(captured),
        "current_dir": "",
        "counter": 0
    }

# =========================
# FLASK ROUTES
# =========================

@app.route("/")
def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "index.html")
    
    if not os.path.exists(html_path):
        return f"""
        <h1>Error: File HTML Tidak Ditemukan</h1>
        <p>Sistem mencari file bernama <b>index.html</b> di dalam folder:</p>
        <p><code>{base_dir}</code></p>
        <p><b>Solusi:</b> Pastikan file HTML Anda bernama <code>index.html</code> dan diletakkan di folder tersebut.</p>
        """, 404
        
    return send_file(html_path)

@app.route("/stream")
def stream():
    def generate():
        while True:
            with frame_lock:
                jpg = latest_frame_jpg
            if jpg is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(0.03)  
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/state")
def get_state():
    update_state_for_ui()
    return jsonify(state_for_ui)

@app.route("/logs")
def get_logs():
    return jsonify({"logs": log_buffer})

@app.route("/command", methods=["POST"])
def post_command():
    global ui_command
    body = request.json
    with ui_command_lock:
        ui_command = body
    return jsonify({"ok": True})

# --- PERBAIKAN PENGIRIMAN GAMBAR (RAW JPEG) ---
@app.route("/unknown_image/<uid>")
def unknown_image(uid):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, unknown_path, uid, "face.jpg")
    if not os.path.exists(img_path):
        return "", 404
    return send_file(img_path, mimetype='image/jpeg')

@app.route("/known_image/<name>/<direction>")
def known_image(name, direction):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, base_path, name, f"{direction}.jpg")
    if not os.path.exists(img_path):
        return "", 404
    return send_file(img_path, mimetype='image/jpeg')
# ----------------------------------------------

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# =========================
# MAIN LOOP
# =========================
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print("SISTEM AKTIF | UI SERVER -> Buka http://localhost:5000 di Browser Anda")

while True:
    with cap_lock:
        ret, frame = cap.read()
    if not ret:
        break

    frame_id += 1
    display = frame.copy()
    current_time = time.time()

    with ui_command_lock:
        cmd = ui_command
        ui_command = None

    if cmd:
        c = cmd.get("cmd", "")
        d = cmd.get("data", {})

        if c == "switch_cam":
            new_cam = int(d.get("cam_id", 0))
            with cap_lock:
                cap.release()
                current_cam_id = new_cam
                cap = setup_camera(current_cam_id)
            time.sleep(0.5)

        elif c == "scan_start":
            name_val = d.get("name", "").strip()
            if name_val and mode not in ["SCAN", "WAIT_CONFIRM"]:
                scan_name = name_val
                save_dir = os.path.join(base_path, scan_name)
                os.makedirs(save_dir, exist_ok=True)
                mode = "WAIT_CONFIRM"

        elif c == "scan_begin":
            if mode == "WAIT_CONFIRM":
                captured, buffer_dir = set(), []
                counter = {d_: 0 for d_ in ["LEFT", "RIGHT", "UP", "DOWN", "CENTER"]}
                mode = "SCAN"

        elif c == "reload_db" or c == "set_mode" and d.get("mode") == "RUN":
            load_all_db()
            mode = "RUN"

        elif c == "stop":
            mode = "IDLE"

    if frame_id % frame_skip == 0:
        last_faces = face_app.get(frame)
    faces = last_faces

    cv2.putText(display, f"CAM: {current_cam_id} | MODE: {mode}", (10, 470), 1, 1, (255, 255, 255), 1)

    faces_for_ui = []

    if mode == "WAIT_CONFIRM":
        overlay = display.copy()
        cv2.rectangle(overlay, (50, 150), (590, 330), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
        cv2.putText(display, f"READY: {scan_name}", (180, 210), 1, 2, (0, 255, 255), 2)
        cv2.putText(display, "TEKAN MULAI SCAN DI UI", (140, 280), 1, 1.5, (255, 255, 255), 2)

    elif mode == "SCAN" and len(faces) > 0:
        cv2.putText(display, "HADAP SESUAI INSTRUKSI", (10, 25), 1, 1, (0, 255, 255), 2)
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        x1, y1, x2, y2 = map(int, face.bbox)
        direction = get_direction(face)
        buffer_dir.append(direction)
        if len(buffer_dir) > 5: buffer_dir.pop(0)
        stable_dir = max(set(buffer_dir), key=buffer_dir.count)

        cv2.rectangle(display, (x1, y1), (x2, y2), (255, 255, 0), 2)
        cv2.putText(display, f"POSISI: {stable_dir}", (x1, y1 - 10), 1, 1.2, (0, 255, 255), 2)

        if stable_dir not in captured:
            counter[stable_dir] += 1
            if counter[stable_dir] > 15:
                face_img = get_face_crop(frame, face.bbox)
                cv2.imwrite(os.path.join(save_dir, f"{stable_dir}.jpg"), face_img)
                np.save(os.path.join(save_dir, f"{stable_dir}.npy"), face.embedding)
                captured.add(stable_dir)

        if len(captured) == 5:
            load_all_db()
            mode = "IDLE"

        state_for_ui["scan_progress"] = {
            "name": scan_name,
            "captured": list(captured),
            "current_dir": stable_dir,
            "counter": counter.get(stable_dir, 0)
        }

    elif mode == "RUN":
        present_this_frame = set()
        if len(faces) > 0:
            for face in faces:
                x1, y1, x2, y2 = map(int, face.bbox)
                f_w = x2 - x1
                emb = face.embedding
                best_name, best_score = "Unknown", -1
                for person, db_embs in known_db.items():
                    scores = [cosine(emb, ref) for ref in db_embs]
                    score = max(scores)
                    if score > best_score: best_score, best_name = score, person

                display_name, display_score = best_name, best_score

                if best_score < 0.35:
                    u_id_found, u_max_s = None, -1
                    for u_id, u_embs in unknown_db.items():
                        u_s = max([cosine(emb, ref) for ref in u_embs])
                        if u_s > u_max_s: u_max_s, u_id_found = u_s, u_id

                    if u_id_found and u_max_s > 0.40:
                        display_name, display_score = u_id_found, u_max_s
                        face_img = get_face_crop(frame, face.bbox)
                        new_blur, _ = calculate_blur_score(face_img)
                        stored_blur = unknown_best_blur_scores.get(u_id_found, 0)
                        if new_blur > (stored_blur + 5) and f_w > MIN_FACE_SIZE:
                            u_dir = os.path.join(unknown_path, u_id_found)
                            cv2.imwrite(os.path.join(u_dir, "face.jpg"), face_img)
                            np.save(os.path.join(u_dir, "embedding.npy"), emb)
                            unknown_best_blur_scores[u_id_found] = new_blur
                            write_daily_log(u_id_found, "SYSTEM", "UPDATE FOTO")
                    else:
                        display_name = "Unknown"
                        track_id = f"{round(x1, -1)}_{round(y1, -1)}"
                        recognition_buffer[track_id] = recognition_buffer.get(track_id, 0) + 1
                        if recognition_buffer[track_id] > 6:
                            face_img = get_face_crop(frame, face.bbox)
                            b_score, _ = calculate_blur_score(face_img)
                            if b_score > (25 if f_w < 50 else 60) and f_w > MIN_FACE_SIZE:
                                if time.time() - last_unknown_check > capture_delay:
                                    existing = [d for d in os.listdir(unknown_path) if d.startswith("U")]
                                    ids = [int(d[1:]) for d in existing if d[1:].isdigit()]
                                    n_id = max(ids) + 1 if ids else 1
                                    u_name = f"U{n_id}"
                                    u_d = os.path.join(unknown_path, u_name)
                                    os.makedirs(u_d, exist_ok=True)
                                    cv2.imwrite(os.path.join(u_d, "face.jpg"), face_img)
                                    np.save(os.path.join(u_d, "embedding.npy"), emb)
                                    write_daily_log(u_name, "SYSTEM", "NEW UNKNOWN")
                                    last_unknown_check = time.time()
                                    load_all_db()
                                    display_name = u_name

                present_this_frame.add(display_name)
                if display_name != "Unknown" and display_name not in active_sessions:
                    status_txt = "TERDAFTAR" if display_name in known_db else "PENYUSUP"
                    write_daily_log(display_name, status_txt, "MASUK")

                if display_name != "Unknown":
                    active_sessions[display_name] = current_time

                face_type = "known" if display_name in known_db else ("unknown" if display_name != "Unknown" else "intruder")
                faces_for_ui.append({
                    "name": display_name,
                    "score": float(display_score),
                    "type": face_type,
                    "bbox": [x1, y1, x2, y2]
                })

                color = (0, 255, 0) if display_name in known_db else (0, 165, 255)
                if display_name == "Unknown": color = (0, 0, 255)
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f"{display_name} {display_score:.2f}", (x1, y1 - 10), 1, 0.8, color, 2)

        for name in list(active_sessions.keys()):
            if name not in present_this_frame:
                if current_time - active_sessions[name] > COOLDOWN_KELUAR:
                    status_txt = "TERDAFTAR" if name in known_db else "PENYUSUP"
                    write_daily_log(name, status_txt, "KELUAR")
                    del active_sessions[name]

    state_for_ui["faces"] = faces_for_ui

    ret_enc, jpg_buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if ret_enc:
        with frame_lock:
            latest_frame_jpg = jpg_buf.tobytes()

cap.release()