import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
import joblib


def train():
    df = pd.read_csv("data/tasks_dataset.csv")

    assert df["priority"].between(0, 1).all(), "Priority must be in [0, 1] range"

    df["full_text"] = df["task_title"].fillna('') + ". " + df["task_description"].fillna('')

    model = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('regressor', GradientBoostingRegressor(
            n_estimators=100,
            loss='huber'
        ))
    ])

    model.fit(df["full_text"], df["priority"])
    joblib.dump(model, "models/task_priority_model.pkl")


if __name__ == "__main__":
    train()
