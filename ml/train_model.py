import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
from pathlib import Path

np.random.seed(42)

# Generate synthetic manufacturing sensor data
n_samples = 5000
temperature = np.random.normal(75, 15, n_samples)
humidity = np.random.normal(60, 20, n_samples)
pressure = np.random.normal(101, 10, n_samples)
vibration = np.random.normal(0.5, 0.3, n_samples)
rpm = np.random.normal(1500, 300, n_samples)

# Defect probability depends on out-of-range sensor values
defect_prob = (
    (temperature > 85).astype(float) * 0.35 +
    (humidity > 80).astype(float) * 0.25 +
    (pressure > 110).astype(float) * 0.20 +
    (vibration > 0.8).astype(float) * 0.30 +
    (rpm > 1800).astype(float) * 0.15 +
    np.random.normal(0, 0.1, n_samples)
)
defect = (defect_prob > 0.35).astype(int)

X = np.column_stack([temperature, humidity, pressure, vibration, rpm])
y = defect

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=8)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

feature_names = ["temperature", "humidity", "pressure", "vibration", "rpm"]
importances = model.feature_importances_.tolist()

meta = {
    "accuracy": round(accuracy, 4),
    "feature_names": feature_names,
    "feature_importances": dict(zip(feature_names, [round(x, 4) for x in importances])),
    "train_samples": len(X_train),
    "test_samples": len(X_test)
}

output_path = Path(__file__).parent / "model.joblib"
joblib.dump({"model": model, "meta": meta}, output_path)

print(f"Model trained and saved to {output_path}")
print(f"Test Accuracy: {accuracy:.4f}")
print(f"Feature Importances: {meta['feature_importances']}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))
