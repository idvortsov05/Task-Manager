import os

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
import joblib
from sentence_embedder import SentenceEmbeddingTransformer
from sklearn.metrics import mean_absolute_error


def train():
    df = pd.read_csv("server/ml/data/processed_tasks_dataset.csv")
    assert df["priority"].between(0, 1).all(), "Priority must be in [0, 1]"

    df["full_text"] = df["task_title"].fillna('') + ". " + df["task_description"].fillna('')

    model = Pipeline([
        ('embedding', SentenceEmbeddingTransformer(model_name="all-MiniLM-L6-v2")),
        ('regressor', GradientBoostingRegressor(
            n_estimators=150,
            loss='huber',
            random_state=42
        ))
    ])

    model.fit(df["full_text"], df["priority"])

    preds = model.predict(df["full_text"])
    mae = mean_absolute_error(df["priority"], preds)
    print(f"MAE (Mean Absolute Error): {mae:.4f}")

    os.makedirs("server/ml/models", exist_ok=True)
    joblib.dump(model, "server/ml/models/task_priority_model.pkl")


if __name__ == "__main__":
    train()

