import pandas as pd
from sklearn.linear_model import LinearRegression

# ------------------------------------------------------------
# Load synthetic training data
# ------------------------------------------------------------
df = pd.read_csv("author_metadata_training.csv")

# ------------------------------------------------------------
# Features
# ------------------------------------------------------------
X = df[
    [
        "author_count",
        "date_present",
        "references_present",
        "preprint",
    ]
]

# ------------------------------------------------------------
# Target credibility value
# ------------------------------------------------------------
y = df["credibility"]

# ------------------------------------------------------------
# Train model
# ------------------------------------------------------------
model = LinearRegression()
model.fit(X, y)

# ------------------------------------------------------------
# Predict metadata credibility contribution
# ------------------------------------------------------------
def predict_author_signal(
    author_count,
    date_present,
    references_present,
    preprint,
):
    prediction_df = pd.DataFrame(
        [[
            author_count,
            int(date_present),
            int(references_present),
            int(preprint),
        ]],
        columns=[
            "author_count",
            "date_present",
            "references_present",
            "preprint",
        ],
    )

    prediction = model.predict(prediction_df)[0]

    # Convert predicted credibility into a score adjustment
    contribution = (prediction - 0.5) * 0.08

    # Prevent excessive influence
    contribution = max(min(contribution, 0.05), -0.05)

    return contribution