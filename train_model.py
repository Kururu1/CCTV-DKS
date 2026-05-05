import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

BASE_PATH = "known_faces"

# ========================
# LOAD EMBEDDINGS
# ========================
X, y = [], []
for person in os.listdir(BASE_PATH):
    folder = os.path.join(BASE_PATH, person)
    if not os.path.isdir(folder):
        continue
    for f in os.listdir(folder):
        if f.endswith(".npy"):
            emb = np.load(os.path.join(folder, f))
            X.append(emb)
            y.append(person)

if len(X) == 0:
    print("ERROR: Tidak ada data embedding di folder known_faces!")
    exit(1)

if len(set(y)) < 2:
    print("ERROR: Minimal 2 orang terdaftar untuk training!")
    exit(1)

X = np.array(X, dtype=np.float32)
y = np.array(y)

# Normalize embeddings
X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-6)

# Label encode
classes = sorted(set(y))
class_to_idx = {c: i for i, c in enumerate(classes)}
y_enc = np.array([class_to_idx[lbl] for lbl in y], dtype=np.int32)
num_classes = len(classes)
emb_dim = X.shape[1]

print(f"\n{'='*40}")
print(f"Data Training:")
print(f"  Embedding dim : {emb_dim}")
print(f"  Jumlah orang  : {num_classes}")
print(f"  Total sampel  : {len(X)}")
for cls in classes:
    print(f"    {cls}: {np.sum(y == cls)} sampel")
print(f"{'='*40}\n")

# ========================
# AUGMENTASI DATA
# ========================
X_aug, y_aug = [X], [y_enc]
for _ in range(4):
    noise = np.random.normal(0, 0.01, X.shape).astype(np.float32)
    Xn = X + noise
    Xn = Xn / (np.linalg.norm(Xn, axis=1, keepdims=True) + 1e-6)
    X_aug.append(Xn)
    y_aug.append(y_enc)

X_train = np.concatenate(X_aug)
y_train = np.concatenate(y_aug)

idx = np.random.permutation(len(X_train))
X_train, y_train = X_train[idx], y_train[idx]

print(f"Total setelah augmentasi: {len(X_train)} sampel")

# ========================
# BUILD MODEL
# ========================

model = models.Sequential([
    layers.Input(shape=(emb_dim,)),
    layers.Dense(256, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    layers.Dense(128, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.2),
    layers.Dense(num_classes, activation='softmax')
], name="face_classifier")

model.compile(
    optimizer=tf.keras.optimizers.Adam(0.001),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

cb = [
    callbacks.EarlyStopping(monitor='accuracy', patience=30, restore_best_weights=True, verbose=1),
    callbacks.ReduceLROnPlateau(monitor='accuracy', patience=15, factor=0.5, min_lr=1e-5, verbose=1)
]

# ========================
# TRAINING
# ========================
print("\nMulai training...\n")
model.fit(
    X_train, y_train,
    epochs=300,
    batch_size=min(32, len(X_train)),
    callbacks=cb,
    verbose=1
)

# ========================
# SIMPAN MODEL
# ========================
model.save("face_classifier.h5")
np.save("face_labels.npy", np.array(classes))

print(f"\n{'='*40}")
print(f"Model tersimpan : face_classifier.h5")
print(f"Label tersimpan : face_labels.npy")
print(f"Kelas           : {classes}")

# Test akurasi pada data asli
preds = np.argmax(model.predict(X, verbose=0), axis=1)
acc = np.mean(preds == y_enc) * 100
print(f"Akurasi training: {acc:.1f}%")
print(f"{'='*40}")
print("\nSelesai! Restart app.py untuk menggunakan model baru.")
