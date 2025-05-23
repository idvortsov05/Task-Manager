import pandas as pd


def load_and_clean_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    return df.dropna(subset=["task_title", "task_description", "priority"])


if __name__ == "__main__":
    df = load_and_clean_data("server/ml/data/tasks_dataset.csv")
    assert df["priority"].between(0, 1).all(), "Priority must be in [0, 1]"
    df.to_csv("server/ml/data/processed_tasks_dataset.csv", index=False)
