import cv2
import numpy as np
import os
import time
import threading
import base64
from datetime import datetime
from insightface.app import FaceAnalysis
import requests

# Flask untuk koneksi ke UI
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sys
import signal

# Telegram Bot
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# KONFIGURASI TELEGRAM BOT
# =========================
# Isi token dari @BotFather
BOT_TOKEN = "8793475313:AAFJDA5zi4WP8P2hCIBHxVLxo9LWu0XXjng"

# Kosongkan [] = semua orang bisa akses
# Isi dengan chat_id tertentu untuk batasi akses
# Cara cari chat_id: kirim pesan ke bot lalu buka
# https://api.telegram.org/bot<TOKEN>/getUpdates
ALLOWED_CHAT_IDS = []

# =========================
# FLASK APP SETUP
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# UPLOAD CONFIG
# =========================
ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'bmp', 'webp', 'tiff'}
ALLOWED_VIDEO_EXT = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT
UPLOAD_TEMP_FOLDER = "upload_temp"
os.makedirs(UPLOAD_TEMP_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def is_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXT

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

# =========================
# PTZ CONTROL ENGINE
# =========================
# Hardware PTZ via UVC (DirectShow / V4L2) — Logitech Rally & compatible
# Falls back to software digital pan/tilt/zoom if hardware not supported

ptz_state = {
    "pan":  0,      # -100 .. +100  (hardware) or pixel offset
    "tilt": 0,      # -100 .. +100
    "zoom": 1.0,    # 1.0 = no zoom, up to 4.0x
    "hw_pan_range":  None,   # filled after probe
    "hw_tilt_range": None,
    "hw_zoom_range": None,
    "hw_supported":  False,
    "mode": "software",      # "hardware" | "software"
}
ptz_lock = threading.Lock()

# Software PTZ state (pixel-level crop/zoom applied in frame render)
soft_ptz = {
    "zoom":   1.0,   # 1.0 – 4.0
    "pan_x":  0.0,   # normalised -1..+1
    "pan_y":  0.0,   # normalised -1..+1
}

def probe_hardware_ptz(camera_cap):
    """Try to read UVC pan/tilt/zoom ranges from the camera."""
    try:
        # OpenCV CAP_PROP codes for UVC PTZ (only available on some builds/platforms)
        PAN_ABS  = cv2.CAP_PROP_PAN   if hasattr(cv2, 'CAP_PROP_PAN')  else None
        TILT_ABS = cv2.CAP_PROP_TILT  if hasattr(cv2, 'CAP_PROP_TILT') else None
        ZOOM_ABS = cv2.CAP_PROP_ZOOM  if hasattr(cv2, 'CAP_PROP_ZOOM') else None

        if PAN_ABS is None:
            return False

        pan_val  = camera_cap.get(PAN_ABS)
        tilt_val = camera_cap.get(TILT_ABS)
        zoom_val = camera_cap.get(ZOOM_ABS)

        # Values of -1 or 0 when property unsupported
        if pan_val == -1 and tilt_val == -1:
            return False

        with ptz_lock:
            ptz_state["hw_supported"] = True
            ptz_state["mode"] = "hardware"
            ptz_state["pan"]  = int(pan_val)
            ptz_state["tilt"] = int(tilt_val)
            ptz_state["zoom"] = max(1.0, zoom_val / 100.0) if zoom_val > 0 else 1.0
        return True
    except Exception:
        return False

def apply_hardware_ptz(camera_cap, pan_delta=0, tilt_delta=0, zoom_delta=0):
    """Send hardware PTZ commands via OpenCV UVC properties."""
    try:
        PAN_ABS  = cv2.CAP_PROP_PAN  if hasattr(cv2, 'CAP_PROP_PAN')  else None
        TILT_ABS = cv2.CAP_PROP_TILT if hasattr(cv2, 'CAP_PROP_TILT') else None
        ZOOM_ABS = cv2.CAP_PROP_ZOOM if hasattr(cv2, 'CAP_PROP_ZOOM') else None

        with ptz_lock:
            # Pan step (Logitech Rally: range ~-360000 to +360000, step 3600)
            if PAN_ABS and pan_delta != 0:
                step = 3600
                new_pan = int(ptz_state["pan"]) + pan_delta * step
                new_pan = max(-360000, min(360000, new_pan))
                camera_cap.set(PAN_ABS, new_pan)
                ptz_state["pan"] = new_pan

            # Tilt step (Logitech Rally: range ~-90000 to +90000)
            if TILT_ABS and tilt_delta != 0:
                step = 3600
                new_tilt = int(ptz_state["tilt"]) + tilt_delta * step
                new_tilt = max(-90000, min(90000, new_tilt))
                camera_cap.set(TILT_ABS, new_tilt)
                ptz_state["tilt"] = new_tilt

            # Zoom (Logitech Rally: 100 = 1x, 400 = 4x)
            if ZOOM_ABS and zoom_delta != 0:
                current_zoom_hw = int(ptz_state["zoom"] * 100)
                new_zoom_hw = current_zoom_hw + zoom_delta * 10
                new_zoom_hw = max(100, min(400, new_zoom_hw))
                camera_cap.set(ZOOM_ABS, new_zoom_hw)
                ptz_state["zoom"] = new_zoom_hw / 100.0
        return True
    except Exception as e:
        print(f"[PTZ HW ERROR] {e}")
        return False

def apply_software_ptz(frame, zoom, pan_x, pan_y):
    """
    Digital zoom + pan applied to a frame.
    zoom  : 1.0 – 4.0
    pan_x : -1.0 (left) .. +1.0 (right)  — normalised
    pan_y : -1.0 (up)   .. +1.0 (down)   — normalised
    """
    if zoom <= 1.0 and pan_x == 0.0 and pan_y == 0.0:
        return frame

    h, w = frame.shape[:2]
    zoom = max(1.0, min(4.0, zoom))

    crop_w = int(w / zoom)
    crop_h = int(h / zoom)

    # Centre of crop window, shifted by pan
    max_offset_x = (w - crop_w) // 2
    max_offset_y = (h - crop_h) // 2

    cx = w // 2 + int(pan_x * max_offset_x)
    cy = h // 2 + int(pan_y * max_offset_y)

    x1 = max(0, cx - crop_w // 2)
    y1 = max(0, cy - crop_h // 2)
    x2 = min(w, x1 + crop_w)
    y2 = min(h, y1 + crop_h)

    # Clamp if near edges
    if x2 - x1 < crop_w:
        x1 = max(0, x2 - crop_w)
    if y2 - y1 < crop_h:
        y1 = max(0, y2 - crop_h)

    cropped = frame[y1:y2, x1:x2]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

def reset_ptz():
    """Reset both hardware and software PTZ to default."""
    with ptz_lock:
        soft_ptz["zoom"]  = 1.0
        soft_ptz["pan_x"] = 0.0
        soft_ptz["pan_y"] = 0.0
        ptz_state["zoom"] = 1.0
        ptz_state["pan"]  = 0
        ptz_state["tilt"] = 0

    if ptz_state["hw_supported"]:
        with cap_lock:
            apply_hardware_ptz(cap, 0, 0, 0)
        try:
            if hasattr(cv2, 'CAP_PROP_PAN'):
                cap.set(cv2.CAP_PROP_PAN,  0)
                cap.set(cv2.CAP_PROP_TILT, 0)
                cap.set(cv2.CAP_PROP_ZOOM, 100)
        except Exception:
            pass

# Probe on startup (non-blocking)
threading.Thread(target=lambda: probe_hardware_ptz(cap), daemon=True).start()

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

@app.route("/ptz", methods=["POST"])
def ptz_control():
    """
    PTZ control endpoint.
    Body: { "action": "left"|"right"|"up"|"down"|"zoom_in"|"zoom_out"|"reset",
            "speed": 1 }
    """
    global cap, soft_ptz

    data   = request.json or {}
    action = data.get("action", "")
    speed  = float(data.get("speed", 1))  # multiplier 1-3

    PAN_STEP  = 0.08 * speed   # software pan step (normalised)
    TILT_STEP = 0.08 * speed
    ZOOM_STEP = 0.25 * speed

    with ptz_lock:
        hw = ptz_state["hw_supported"]

    if action == "reset":
        reset_ptz()
        return jsonify({"ok": True, "state": _ptz_api_state()})

    if hw:
        # Hardware PTZ (Logitech Rally and UVC-compatible cameras)
        with cap_lock:
            if action == "left":
                apply_hardware_ptz(cap, pan_delta=-1)
            elif action == "right":
                apply_hardware_ptz(cap, pan_delta=+1)
            elif action == "up":
                apply_hardware_ptz(cap, tilt_delta=+1)
            elif action == "down":
                apply_hardware_ptz(cap, tilt_delta=-1)
            elif action == "zoom_in":
                apply_hardware_ptz(cap, zoom_delta=+1)
            elif action == "zoom_out":
                apply_hardware_ptz(cap, zoom_delta=-1)
    else:
        # Software digital PTZ (works on ALL cameras)
        with ptz_lock:
            if action == "left":
                soft_ptz["pan_x"] = max(-1.0, soft_ptz["pan_x"] - PAN_STEP)
            elif action == "right":
                soft_ptz["pan_x"] = min(+1.0, soft_ptz["pan_x"] + PAN_STEP)
            elif action == "up":
                soft_ptz["pan_y"] = max(-1.0, soft_ptz["pan_y"] - TILT_STEP)
            elif action == "down":
                soft_ptz["pan_y"] = min(+1.0, soft_ptz["pan_y"] + TILT_STEP)
            elif action == "zoom_in":
                soft_ptz["zoom"] = min(4.0, soft_ptz["zoom"] + ZOOM_STEP)
            elif action == "zoom_out":
                soft_ptz["zoom"] = max(1.0, soft_ptz["zoom"] - ZOOM_STEP)
                # Reset pan when zoomed all the way out
                if soft_ptz["zoom"] <= 1.0:
                    soft_ptz["pan_x"] = 0.0
                    soft_ptz["pan_y"] = 0.0

    return jsonify({"ok": True, "state": _ptz_api_state()})


@app.route("/ptz_state")
def ptz_state_route():
    return jsonify(_ptz_api_state())


def _ptz_api_state():
    with ptz_lock:
        return {
            "hw_supported": ptz_state["hw_supported"],
            "mode":         ptz_state["mode"],
            "zoom":         round(soft_ptz["zoom"] if not ptz_state["hw_supported"] else ptz_state["zoom"], 2),
            "pan_x":        round(soft_ptz["pan_x"], 3),
            "pan_y":        round(soft_ptz["pan_y"], 3),
            "hw_pan":       ptz_state["pan"],
            "hw_tilt":      ptz_state["tilt"],
        }

@app.route("/register_upload", methods=["POST"])
def register_upload():
    """Pendaftaran wajah via upload gambar atau video."""
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "Tidak ada file yang dikirim"}), 400

    file = request.files['file']
    name = request.form.get('name', '').strip()

    if not name:
        return jsonify({"ok": False, "error": "Nama tidak boleh kosong"}), 400

    if file.filename == '':
        return jsonify({"ok": False, "error": "Nama file kosong"}), 400

    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'tidak diketahui'
        return jsonify({
            "ok": False,
            "error": f"Format '.{ext}' tidak didukung. Hanya gambar (jpg, png, bmp, webp) atau video (mp4, avi, mov, mkv) yang diperbolehkan."
        }), 400

    filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOAD_TEMP_FOLDER, filename)
    file.save(temp_path)

    save_dir = os.path.join(base_path, name)
    os.makedirs(save_dir, exist_ok=True)

    captured_dirs = []

    try:
        if is_image_file(filename):
            # Proses file gambar
            img = cv2.imread(temp_path)
            if img is None:
                os.remove(temp_path)
                return jsonify({"ok": False, "error": "Gagal membaca file gambar. Pastikan file tidak rusak."}), 400

            faces = face_app.get(img)
            if len(faces) == 0:
                os.remove(temp_path)
                return jsonify({"ok": False, "error": "Tidak ada wajah terdeteksi dalam gambar."}), 400

            # Ambil wajah terbesar
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            face_img = get_face_crop(img, face.bbox)
            direction = get_direction(face)

            cv2.imwrite(os.path.join(save_dir, f"{direction}.jpg"), face_img)
            np.save(os.path.join(save_dir, f"{direction}.npy"), face.embedding)
            # Simpan juga sebagai CENTER jika bukan CENTER agar minimal ada referensi
            if direction != "CENTER":
                cv2.imwrite(os.path.join(save_dir, "CENTER.jpg"), face_img)
                np.save(os.path.join(save_dir, "CENTER.npy"), face.embedding)
                captured_dirs = [direction, "CENTER"]
            else:
                captured_dirs = [direction]

        elif is_video_file(filename):
            # Proses file video — ambil frame dari berbagai posisi
            vcap = cv2.VideoCapture(temp_path)
            total_frames = int(vcap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = vcap.get(cv2.CAP_PROP_FPS) or 25
            max_duration_frames = int(fps * 60)  # Maksimal 60 detik pertama
            total_frames = min(total_frames, max_duration_frames)

            if total_frames <= 0:
                vcap.release()
                os.remove(temp_path)
                return jsonify({"ok": False, "error": "Video tidak bisa dibaca atau terlalu pendek."}), 400

            directions_needed = ["LEFT", "RIGHT", "UP", "DOWN", "CENTER"]
            best_embeddings = {}   # direction -> (embedding, face_img, blur_score)

            # Sampel frame secara merata
            sample_count = min(120, total_frames)
            frame_indices = [int(i * total_frames / sample_count) for i in range(sample_count)]

            for fi in frame_indices:
                vcap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                ret_v, vframe = vcap.read()
                if not ret_v or vframe is None:
                    continue

                v_faces = face_app.get(vframe)
                if len(v_faces) == 0:
                    continue

                face_v = max(v_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                fdir = get_direction(face_v)
                face_img_v = get_face_crop(vframe, face_v.bbox)
                blur, _ = calculate_blur_score(face_img_v)

                if fdir not in best_embeddings or blur > best_embeddings[fdir][2]:
                    best_embeddings[fdir] = (face_v.embedding, face_img_v, blur)

            vcap.release()

            if len(best_embeddings) == 0:
                os.remove(temp_path)
                return jsonify({"ok": False, "error": "Tidak ada wajah terdeteksi dalam video."}), 400

            for fdir, (emb, fimg, _) in best_embeddings.items():
                cv2.imwrite(os.path.join(save_dir, f"{fdir}.jpg"), fimg)
                np.save(os.path.join(save_dir, f"{fdir}.npy"), emb)
                captured_dirs.append(fdir)

        os.remove(temp_path)

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"ok": False, "error": f"Error saat memproses file: {str(e)}"}), 500

    load_all_db()
    write_daily_log(name, "SYSTEM", f"DAFTAR VIA UPLOAD ({len(captured_dirs)} arah)")

    return jsonify({
        "ok": True,
        "message": f"Berhasil mendaftarkan '{name}' dengan {len(captured_dirs)} arah: {', '.join(captured_dirs)}"
    })


@app.route("/shutdown", methods=["POST"])
def shutdown_system():
    """Matikan seluruh sistem (Flask + main loop)."""
    def do_shutdown():
        time.sleep(0.5)
        write_daily_log("SYSTEM", "SYSTEM", "SHUTDOWN OLEH USER")
        os.kill(os.getpid(), signal.SIGTERM)

    t = threading.Thread(target=do_shutdown, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Sistem akan dimatikan..."})

@app.route("/send_report", methods=["POST"])
def send_report():
    # Fungsi ini mengambil log harian berdasarkan tanggal saat ini
    now = datetime.now()
    main_log_folder = "logs"
    month_dir = os.path.join(main_log_folder, f"Log_{now.strftime('%Y-%m')}")
    file_name = f"{now.strftime('%Y-%m-%d')}.txt"
    file_path = os.path.join(month_dir, file_name)

    if os.path.exists(file_path):
        # URL Webhook n8n yang berbeda untuk menerima file (bukan trigger telegram)
        n8n_receiver_url = "https://n8n.nayr.online/webhook-test/4aa9452a-d5b7-4b06-81e6-05497bf06950"
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'text/plain')}
                requests.post(n8n_receiver_url, files=files)
            return jsonify({"ok": True, "message": "Log terkirim"}), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": False, "message": "File tidak ditemukan"}), 404

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# =========================
# TELEGRAM BOT
# =========================

def tg_get_log_path():
    """Kembalikan path log hari ini, None jika tidak ada."""
    now = datetime.now()
    month_dir = os.path.join("logs", f"Log_{now.strftime('%Y-%m')}")
    file_name  = f"{now.strftime('%Y-%m-%d')}.txt"
    file_path  = os.path.join(month_dir, file_name)
    return file_path if os.path.exists(file_path) else None

def tg_is_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS

async def tg_cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tg_is_allowed(update.effective_chat.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    await update.message.reply_text(
        "👁 *Face Recognition System — Bot Aktif*\n\n"
        "Perintah yang tersedia:\n"
        "/laporan  — Kirim file log deteksi hari ini\n"
        "/penyusup — Lihat foto wajah yang tidak dikenali\n"
        "/status   — Cek status sistem\n"
        "/help     — Tampilkan bantuan ini",
        parse_mode="Markdown"
    )

async def tg_cmd_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tg_is_allowed(update.effective_chat.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    log_path = tg_get_log_path()
    if log_path is None:
        await update.message.reply_text(
            "📭 Belum ada log untuk hari ini.\n"
            "Sistem mencatat aktivitas saat mode *RUN* aktif.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Mengambil laporan, harap tunggu...")
    try:
        now     = datetime.now()
        caption = (
            f"📋 *Log Harian Face Recognition*\n"
            f"🗓 {now.strftime('%d %B %Y')}\n"
            f"🕐 Dikirim pukul {now.strftime('%H:%M:%S')}"
        )
        with open(log_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(log_path),
                caption=caption,
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal mengirim log: {e}")

async def tg_cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tg_is_allowed(update.effective_chat.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    now            = datetime.now()
    jumlah_dikenal = len(known_db)
    jumlah_unknown = len(unknown_db)
    sesi_aktif     = len(active_sessions)
    log_path       = tg_get_log_path()

    jumlah_log = 0
    if log_path:
        with open(log_path, "r") as f:
            jumlah_log = sum(1 for _ in f)

    await update.message.reply_text(
        f"🖥 *Status Sistem Face Recognition*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Mode saat ini   : `{mode}`\n"
        f"📷 Kamera aktif    : `{current_cam_id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Wajah terdaftar : `{jumlah_dikenal}` orang\n"
        f"❓ Wajah unknown   : `{jumlah_unknown}` orang\n"
        f"🟢 Sesi aktif      : `{sesi_aktif}` orang\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Log hari ini    : `{jumlah_log}` baris\n"
        f"🕐 Waktu server    : `{now.strftime('%H:%M:%S')}`",
        parse_mode="Markdown"
    )

async def tg_cmd_penyusup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tg_is_allowed(update.effective_chat.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    if not os.path.exists(unknown_path) or not os.listdir(unknown_path):
        await update.message.reply_text("✅ Aman! Belum ada penyusup yang terdeteksi.")
        return

    await update.message.reply_text("⏳ Memuat maksimal 10 foto penyusup terbaru...")

    unknown_dirs = [d for d in os.listdir(unknown_path) if os.path.isdir(os.path.join(unknown_path, d))]
    
    unknown_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(unknown_path, x)), reverse=True)
    unknown_dirs = unknown_dirs[:10]
    
    count = 0
    for uid in unknown_dirs:
        img_path = os.path.join(unknown_path, uid, "face.jpg")
        if os.path.exists(img_path):
            try:
                with open(img_path, "rb") as f:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=f,
                        caption=f"🚨 *Penyusup Terbaru: {uid}*",
                        parse_mode="Markdown"
                    )
                count += 1
            except Exception as e:
                print(f"Gagal mengirim foto {uid}: {e}")

    if count == 0:
        await update.message.reply_text("⚠️ Folder ada, tetapi data foto tidak ditemukan.")
    else:
        await update.message.reply_text(f"✅ Selesai menampilkan {count} foto penyusup terbaru.")


async def tg_cmd_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Daftar Perintah*\n\n"
        "/start    — Salam pembuka\n"
        "/laporan  — Kirim file log hari ini (.txt)\n"
        "/penyusup — Lihat 10 foto wajah penyusup terbaru\n"
        "/status   — Info sistem (mode, wajah, sesi aktif)\n"
        "/help     — Tampilkan pesan ini",
        parse_mode="Markdown"
    )

async def tg_handler_pesan_biasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tg_is_allowed(update.effective_chat.id):
        return
    await update.message.reply_text(
        "❓ Perintah tidak dikenali. Ketik /help untuk melihat daftar perintah."
    )

def run_telegram_bot():
    """Jalankan Telegram bot di event loop tersendiri (non-blocking terhadap main loop)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start",   tg_cmd_start))
    application.add_handler(CommandHandler("laporan", tg_cmd_laporan))
    application.add_handler(CommandHandler("status",  tg_cmd_status))
    application.add_handler(CommandHandler("penyusup", tg_cmd_penyusup))
    application.add_handler(CommandHandler("help", tg_cmd_bantuan))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, tg_handler_pesan_biasa)
    )

    print("TELEGRAM BOT AKTIF | Kirim /laporan di Telegram untuk mendapat log")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


# =========================
# MAIN LOOP
# =========================
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
telegram_thread.start()

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
            reset_ptz()
            time.sleep(0.5)
            threading.Thread(target=lambda: probe_hardware_ptz(cap), daemon=True).start()

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

    # Apply software digital PTZ (zoom + pan) if hardware not available
    if not ptz_state["hw_supported"]:
        with ptz_lock:
            s_zoom = soft_ptz["zoom"]
            s_px   = soft_ptz["pan_x"]
            s_py   = soft_ptz["pan_y"]
        display = apply_software_ptz(display, s_zoom, s_px, s_py)

    ret_enc, jpg_buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if ret_enc:
        with frame_lock:
            latest_frame_jpg = jpg_buf.tobytes()
    

cap.release()