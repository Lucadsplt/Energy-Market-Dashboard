import numpy as np


def log_returns(prix):
    """Rendements logarithmiques : r_t = ln(P_t / P_{t-1}).

    Ils s'additionnent dans le temps (r sur 2 jours = r1 + r2),
    ce qui est indispensable pour simuler plusieurs jours d'affilee.
    """
    return np.log(prix).diff().dropna()


if __name__ == "__main__":
    import pandas as pd
    print(log_returns(pd.Series([100.0, 110.0, 99.0])))   # attendu : 0.0953 puis -0.1054