import os
import cv2
import numpy as np
import shutil

UNKNOWN_DIR = "unknown_detected"
KNOWN_DIR = "known_faces"
SIMILARITY_THRESHOLD = 0.30

def cosine_sim(a, b):
    a = a / (np.linalg.norm(a) + 1e-6)
    b = b / (np.linalg.norm(b) + 1e-6)
    return np.dot(a, b)

def calculate_blur_score(img_path):
    img = cv2.imread(img_path)
    if img is None or img.size == 0: 
        return 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def reorder_ids():
    """Mengurutkan ulang ID U1, U2, dst agar tidak ada nomor yang bolong."""
    if not os.path.exists(UNKNOWN_DIR): return False
    
    # Ambil semua folder berawalan U dan angka
    existing = [d for d in os.listdir(UNKNOWN_DIR) if d.startswith("U") and d[1:].isdigit()]
    # Urutkan berdasarkan angka ID lama
    existing.sort(key=lambda x: int(x[1:]))
    
    changed = False
    for i, old_name in enumerate(existing):
        new_name = f"U{i + 1}"
        if old_name != new_name:
            old_path = os.path.join(UNKNOWN_DIR, old_name)
            new_path = os.path.join(UNKNOWN_DIR, new_name)
            # Jika new_path sudah ada (harusnya tidak terjadi karena sudah diurutkan), hindari crash
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                print(f"[*] Reorder: {old_name} -> {new_name}")
                changed = True
    return changed

def run_cleanup():
    """Menjalankan pembersihan duplikat lalu mengurutkan ulang ID."""
    if not os.path.exists(UNKNOWN_DIR):
        return False

    unknowns = {}
    for folder in os.listdir(UNKNOWN_DIR):
        folder_path = os.path.join(UNKNOWN_DIR, folder)
        if not os.path.isdir(folder_path): continue
            
        emb_path = os.path.join(folder_path, "embedding.npy")
        img_path = os.path.join(folder_path, "face.jpg")
        
        if os.path.exists(emb_path) and os.path.exists(img_path):
            unknowns[folder] = {
                "path": folder_path,
                "emb": np.load(emb_path),
                "blur": calculate_blur_score(img_path)
            }

    if len(unknowns) < 1:
        return reorder_ids()

    to_delete = set()
    keys = list(unknowns.keys())
    changed = False

    # 1. Bandingkan unknown dengan known_faces (hapus jika sudah terdaftar)
    if os.path.exists(KNOWN_DIR):
        known_embs = []
        for person in os.listdir(KNOWN_DIR):
            person_dir = os.path.join(KNOWN_DIR, person)
            if not os.path.isdir(person_dir): continue
            for f in os.listdir(person_dir):
                if f.endswith(".npy"):
                    known_embs.append(np.load(os.path.join(person_dir, f)))
        
        for u_id, u_data in unknowns.items():
            for k_emb in known_embs:
                if cosine_sim(u_data["emb"], k_emb) > SIMILARITY_THRESHOLD:
                    to_delete.add(u_id)
                    print(f"[KNOWN] Menghapus {u_id} karena wajah ini sudah terdaftar.")
                    break

    # 2. Bandingkan antar unknown untuk menghapus duplikat

    for i in range(len(keys)):
        id_a = keys[i]
        if id_a in to_delete: continue
            
        for j in range(i + 1, len(keys)):
            id_b = keys[j]
            if id_b in to_delete: continue
                
            sim = cosine_sim(unknowns[id_a]["emb"], unknowns[id_b]["emb"])
            if sim > SIMILARITY_THRESHOLD:
                if unknowns[id_a]["blur"] > unknowns[id_b]["blur"]:
                    to_delete.add(id_b)
                else:
                    to_delete.add(id_a)
                    break

    if to_delete:
        print(f"Menghapus {len(to_delete)} folder duplikat...")
        for del_id in to_delete:
            try:
                shutil.rmtree(unknowns[del_id]["path"])
                changed = True
            except: pass

    # Setelah dihapus, urutkan ulang ID
    reordered = reorder_ids()
    return changed or reordered

if __name__ == "__main__":
    print("Menjalankan cleanup manual...")
    run_cleanup()
    print("Selesai.")
