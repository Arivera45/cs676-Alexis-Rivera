# Project 1: URL Credibility Scoring System

## Overview

This project evaluates the credibility of online sources by analyzing URL characteristics and webpage metadata.

The original baseline system relied primarily on URL-level signals such as:

- Domain reputation
- Top-level domains (TLDs)
- HTTPS usage
- DOI detection
- Path-based penalties

This project extends the baseline by introducing page-level metadata extraction and a regression-based metadata scoring model.

---

## Literature and Background

This project was influenced by previous research in web credibility assessment, trust evaluation, and misinformation detection.

### TrustRank

TrustRank proposed a method for estimating website trustworthiness by propagating trust from a set of manually verified websites through hyperlink relationships. This demonstrated that source reputation can serve as an effective credibility signal.

**Citation**

Gyöngyi, Z., Garcia-Molina, H., & Pedersen, J. (2004). *Combating web spam with TrustRank*. Proceedings of the Thirtieth International Conference on Very Large Data Bases (VLDB), 576–587.

---

### Web Credibility Research

Fogg et al. conducted a large study examining factors that influence user trust in websites. Their findings showed that transparency, authorship, accountability, and source reputation significantly impact perceived credibility.

**Citation**

Fogg, B. J., Marshall, J., Laraki, O., Osipovich, A., Varma, C., Fang, N., Paul, J., Rangnekar, A., Shon, J., Swani, P., & Treinen, M. (2001). *What makes web sites credible? A report on a large quantitative study*. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems, 61–68.

---

### Misinformation Detection

Modern misinformation detection systems frequently combine multiple credibility indicators and machine learning techniques. This motivated the regression-based metadata model used in this project.

**Citation**

Shu, K., Sliva, A., Wang, S., Tang, J., & Liu, H. (2017). *Fake news detection on social media: A data mining perspective*. ACM SIGKDD Explorations Newsletter, 19(1), 22–36.

---

## Features

### URL-Based Credibility Signals

The system evaluates:

- Domain reputation
- HTTPS availability
- DOI indicators
- Path keywords
- Source categories

Examples:

```text
nature.com
nejm.org
reuters.com
```

receive positive credibility signals.

Examples:

```text
/blog/
/forum/
/comments/
```

receive negative credibility signals.

---

### Metadata Extraction

The scorer retrieves page HTML and extracts:

- Author metadata
- Author count
- Publication date
- References and citations
- Preprint indicators
- Cloudflare detection

Example output:

```python
{
    "author": True,
    "author_count": 20,
    "date": True,
    "references": True,
    "preprint": False,
    "cloudflare": False
}
```

---

### Linear Regression Metadata Model

To move beyond fixed rule-based metadata bonuses, a Linear Regression model was trained using synthetic metadata examples.

Input features:

```text
author_count
date_present
references_present
preprint
```

Output:

```text
Metadata credibility contribution
```

The predicted contribution is added to the overall credibility score while remaining bounded to avoid excessive influence.

Example explanation:

```text
Metadata model contribution 0.046
(authors=20, date=True, references=True, preprint=False)
```

---

## Project Structure

```text
project_1/
│
├── credibility.py
├── author_model.py
├── author_metadata_training.csv
├── evaluate.py
├── main.py
├── test_credibility.py
├── testrequest.py
└── README.md
```

### Important Files

#### credibility.py

Main credibility scoring logic.

#### author_model.py

Linear Regression metadata model.

#### author_metadata_training.csv

Synthetic training dataset used by the regression model.

#### evaluate.py

Benchmark evaluation script.

#### test_credibility.py

Provided automated tests.

#### testrequest.py

Additional custom tests created during development.

---

## Running Tests

```powershell
python test_credibility.py
```

Custom tests:

```powershell
python testrequest.py
```

---

## Running Evaluation

```powershell
python evaluate.py
```

---

## Running the Application

```powershell
streamlit run main.py
```

---

## Machine Learning Component

The project includes a Linear Regression model trained on synthetic metadata samples.

The model uses:

- Author count
- Publication metadata
- References
- Preprint status

to estimate a metadata-based credibility contribution.

Multiple iterations of dataset refinement improved model performance:

| Version | MAE |
|----------|----------|
| Initial Regression | 0.140 |
| Author Count Cap | 0.138 |
| Expanded Dataset | 0.137 |
| Tuned Dataset | 0.135 |

This approach was implemented to move beyond fixed metadata bonuses and introduce a data-driven scoring component.

---

## Evaluation Results

Final regression-based system:

```text
URLs evaluated     : 24
Mean absolute error: 0.135
Band accuracy      : 66.7%
Worst single error : 0.430
```

### Test Results

```text
21 passed, 0 failed
```

---

## Known Limitations

- Some publishers block automated requests.
- Cloudflare protection may prevent metadata extraction.
- Some benchmark URLs are unavailable or represent placeholder examples.
- The regression model uses synthetic training data rather than real citation databases.