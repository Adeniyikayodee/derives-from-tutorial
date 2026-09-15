"""leak_demo.py: predict a published index from the columns it was built from."""
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score

# CDC marks missing values as -999, so turn those into proper blanks.
df = pd.read_csv("California.csv", low_memory=False).replace(-999, float("nan"))


def score(inputs, target):
    data = df[inputs + [target]].dropna()
    model = HistGradientBoostingRegressor(random_state=0)
    folds = KFold(n_splits=5, shuffle=True, random_state=0)
    r2 = cross_val_score(model, data[inputs], data[target],
                         cv=folds, scoring="r2").mean()
    print(f"{target:<11} from {len(inputs)} column(s)  "
          f"tracts={len(data)}  R2 = {r2:.3f}")


# Theme 1 is built from exactly these five columns.
score(["EP_POV150", "EP_UNEMP", "EP_HBURD", "EP_NOHSDP", "EP_UNINSUR"],
      "RPL_THEME1")

# EP_NOINT ships in the same file, and CDC leaves it out of the index.
score(["EP_NOINT"], "RPL_THEMES")
